import base64
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from living_storyworld.providers.horde import HordeImageProvider
from living_storyworld.providers.local_image import ComfyUIProvider, validate_workflow
from living_storyworld.settings import UserSettings
from living_storyworld.webapp import app


@pytest.fixture
def image_bytes():
    data = io.BytesIO()
    Image.new("RGB", (16, 9), "green").save(data, format="PNG")
    return data.getvalue()


WORKFLOW = {
    "1": {"class_type": "CLIPTextEncode", "inputs": {"text": "positive"}},
    "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "negative"}},
    "3": {"class_type": "KSampler", "inputs": {"seed": 42}},
}


def test_comfyui_submission_history_and_image_download(
    tmp_path, monkeypatch, image_bytes
):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, data, content_type="application/json"):
            data = (
                json.dumps(data).encode()
                if content_type == "application/json"
                else data
            )
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            calls.append(
                (
                    self.path,
                    json.loads(self.rfile.read(int(self.headers["Content-Length"]))),
                )
            )
            self.respond({"prompt_id": "our-job"})

        def do_GET(self):
            calls.append((self.path, None))
            if self.path.startswith("/view?"):
                self.respond(image_bytes, "image/png")
            else:
                self.respond(
                    {
                        "our-job": {
                            "status": {"completed": True},
                            "outputs": {
                                "9": {
                                    "images": [
                                        {
                                            "filename": "scene.png",
                                            "subfolder": "",
                                            "type": "output",
                                        }
                                    ]
                                }
                            },
                        }
                    }
                )

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    settings = UserSettings(
        comfyui_base_url=f"http://127.0.0.1:{server.server_port}",
        comfyui_workflow=json.dumps(WORKFLOW),
        comfyui_prompt_node="1",
    )
    monkeypatch.setattr(
        "living_storyworld.settings.load_user_settings", lambda: settings
    )
    try:
        result = ComfyUIProvider().generate("A lantern garden", tmp_path / "scene.png")
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    assert result.image_path.exists()
    assert Image.open(result.image_path).size == (16, 9)
    sent = calls[0][1]["prompt"]
    assert sent["1"]["inputs"]["text"] == "A lantern garden"
    assert sent["2"]["inputs"]["text"] == "negative"
    assert WORKFLOW["1"]["inputs"]["text"] == "positive"
    assert calls[1][0] == "/history/our-job"
    assert calls[2][0].startswith("/view?")


@pytest.mark.parametrize(
    "workflow,node",
    [("invalid", "1"), ('{"nodes": []}', "1"), (json.dumps(WORKFLOW), "3")],
)
def test_comfyui_workflow_requires_api_format_and_text_node(workflow, node):
    with pytest.raises(ValueError):
        validate_workflow(workflow, node)


def test_invalid_workflow_does_not_save_settings(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr("living_storyworld.settings.CONFIG_PATH", path)
    response = TestClient(app).put(
        "/api/settings",
        json={"comfyui_workflow": '{"nodes": []}', "comfyui_prompt_node": "1"},
    )
    assert response.status_code == 400
    assert not path.exists()


def test_horde_uses_account_key_and_disables_image_sharing(tmp_path, image_bytes):
    session = MagicMock()
    session.post.return_value.json.return_value = {"id": "job-1"}
    check, status = MagicMock(), MagicMock()
    check.json.return_value = {"done": True}
    status.json.return_value = {
        "generations": [
            {"model": "community-model", "img": base64.b64encode(image_bytes).decode()}
        ]
    }
    session.get.side_effect = [check, status]
    with patch("requests.Session") as factory:
        factory.return_value.__enter__.return_value = session
        result = HordeImageProvider(api_key="account-test-key").generate(
            "A lantern", tmp_path / "horde.png"
        )
    payload = session.post.call_args.kwargs["json"]
    assert payload["shared"] is False and payload["r2"] is False
    assert "account-test-key" not in json.dumps(payload)
    assert session.headers.update.call_args.args[0]["apikey"] == "account-test-key"
    assert result.model == "community-model" and result.estimated_cost == 0
    assert result.image_path.exists()
    session.delete.assert_not_called()


def test_horde_failed_job_is_cancelled_without_saving_image(tmp_path):
    session = MagicMock()
    session.post.return_value.json.return_value = {"id": "job-1"}
    session.get.return_value.json.return_value = {"faulted": True}
    with patch("requests.Session") as factory:
        factory.return_value.__enter__.return_value = session
        with pytest.raises(RuntimeError, match="could not generate"):
            HordeImageProvider(api_key="test-key").generate(
                "A lantern", tmp_path / "failed.png"
            )
    session.delete.assert_called_once()
    assert not (tmp_path / "failed.png").exists()


def test_horde_anonymous_sharing_is_not_implicitly_enabled():
    with pytest.raises(ValueError, match="Anonymous"):
        HordeImageProvider(api_key="0000000000")
