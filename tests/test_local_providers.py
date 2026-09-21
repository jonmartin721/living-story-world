import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from living_storyworld.providers.local import LocalProvider, validate_local_url
from living_storyworld.settings import UserSettings, get_available_text_providers
from living_storyworld.webapp import app


@pytest.fixture
def model_server():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, body):
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            requests.append((self.path, None))
            self.send(
                {
                    "object": "list",
                    "data": [
                        {"id": "installed-model", "object": "model"},
                        {"id": "remote:cloud", "object": "model"},
                    ],
                }
            )

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((self.path, body))
            self.send(
                {
                    "id": "local",
                    "object": "chat.completion",
                    "created": 0,
                    "model": body["model"],
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "<think>Private reasoning</think>\n# The Lantern\nA story.",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                }
            )

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/v1", requests
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.mark.parametrize("provider", ["local", "ollama"])
def test_local_generation_uses_compatible_wire_protocol(model_server, provider):
    url, requests = model_server
    model = LocalProvider(provider=provider, base_url=url)
    result = model.generate([{"role": "user", "content": "Tell a story"}])
    assert result.model == "installed-model"
    assert result.content == "# The Lantern\nA story."
    assert result.estimated_cost == 0
    assert requests[0] == ("/v1/models", None)
    assert requests[1][0] == "/v1/chat/completions"
    assert requests[1][1]["messages"] == [{"role": "user", "content": "Tell a story"}]
    assert requests[1][1]["reasoning_effort"] == "none"
    if provider == "ollama":
        assert model.list_models() == ["installed-model"]


def test_local_selection_cannot_fall_back_to_a_paid_provider(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    for provider in ("local", "ollama"):
        assert get_available_text_providers(UserSettings(text_provider=provider)) == [
            provider
        ]


def test_free_hosted_selection_cannot_fall_back_to_paid_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "paid-test-key")
    settings = UserSettings(
        text_provider="openrouter",
        openrouter_api_key="free-route-key",
        default_text_model="openrouter/free",
    )
    assert get_available_text_providers(settings) == ["openrouter"]


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/v1",
        "http://169.254.169.254/v1",
        "file:///etc/passwd",
        "http://user:secret@localhost/v1",
        "http://localhost/v1?key=secret",
    ],
)
def test_local_connection_rejects_nonlocal_or_embedded_credentials(url):
    with pytest.raises(ValueError):
        validate_local_url(url)


def test_ollama_does_not_generate_with_a_cloud_model():
    with pytest.raises(ValueError, match="installed local model"):
        LocalProvider(provider="ollama").generate([], model="remote:cloud")


def test_local_metadata_missing_only_the_outer_brace_is_recovered():
    from living_storyworld.generator import _parse_meta

    raw = '<!-- {"choices": [{"id": "a", "text": "Open the gate"}], "story_health": {"notes": "A beginning"} -->\n# The Gate'
    assert _parse_meta(raw)["choices"][0]["text"] == "Open the gate"
    assert _parse_meta('<!-- {"choices": [{"id": "unfinished} -->') == {}
    assert _parse_meta('<!-- {"choices": [invalid]} -->') == {}


def test_settings_catalog_and_local_discovery_do_not_return_secrets(model_server):
    url, _ = model_server
    client = TestClient(app)
    catalog = client.get("/api/settings/providers").json()
    assert "ollama" in catalog["text"] and "local" in catalog["text"]
    assert "none" in catalog["image"]
    response = client.post(
        "/api/settings/local-models", json={"provider": "ollama", "base_url": url}
    )
    assert response.json() == {"models": ["installed-model"]}


def test_existing_provider_and_model_settings_survive_new_defaults(
    tmp_path, monkeypatch
):
    from living_storyworld.settings import load_user_settings

    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "text_provider": "openai",
                "default_text_model": "custom-model",
                "image_provider": "pollinations",
                "default_image_model": "flux",
            }
        )
    )
    monkeypatch.setattr("living_storyworld.settings.CONFIG_PATH", config)
    settings = load_user_settings()
    assert (settings.text_provider, settings.default_text_model) == (
        "openai",
        "custom-model",
    )
    assert (settings.image_provider, settings.default_image_model) == (
        "pollinations",
        "flux",
    )


def test_pollinations_auth_is_only_in_the_header(tmp_path):
    import io
    from PIL import Image
    from living_storyworld.providers.image import PollinationsProvider

    data = io.BytesIO()
    Image.new("RGB", (4, 4)).save(data, format="PNG")
    response = SimpleNamespace(
        headers={"Content-Type": "image/png"},
        raise_for_status=lambda: None,
        iter_content=lambda chunk_size: [data.getvalue()],
    )
    with patch("requests.get", return_value=response) as get:
        result = PollinationsProvider(api_key="private-key").generate(
            "A sunset / sea", tmp_path / "scene.png", model="flux"
        )
    args = get.call_args
    assert args.args[0].startswith("https://gen.pollinations.ai/image/")
    assert "private-key" not in args.args[0]
    assert args.kwargs["headers"] == {"Authorization": "Bearer private-key"}
    assert result.model == "black-forest-labs/flux.1-schnell"
