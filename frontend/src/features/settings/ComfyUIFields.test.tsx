import { fireEvent, render, screen } from "@testing-library/react";
import { ComfyUIFields } from "./ComfyUIFields";
import { api } from "../../api/client";

vi.mock("../../api/client", () => ({ api: { checkComfyUI: vi.fn() } }));

it("preserves the existing workflow when an import is invalid", async () => {
  const onChange = vi.fn();
  render(
    <ComfyUIFields
      address="http://127.0.0.1:8188"
      workflow='{"1":{"class_type":"CLIPTextEncode","inputs":{"text":"old"}}}'
      promptNode="1"
      onChange={onChange}
    />,
  );
  const file = new File(["invalid"], "broken.json", {
    type: "application/json",
  });
  Object.defineProperty(file, "text", { value: async () => "invalid" });
  fireEvent.change(screen.getByLabelText(/Import image workflow/), {
    target: { files: [file] },
  });
  expect(await screen.findByRole("alert")).toHaveTextContent("API");
  expect(onChange).not.toHaveBeenCalled();
  expect(screen.getByRole("combobox")).toHaveValue("1");
});

it("shows a connection failure beside the local setup controls", async () => {
  vi.mocked(api.checkComfyUI).mockRejectedValueOnce(new Error("Start ComfyUI"));
  render(
    <ComfyUIFields
      address="http://127.0.0.1:8188"
      workflow=""
      promptNode=""
      onChange={vi.fn()}
    />,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Check ComfyUI connection" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent("Start ComfyUI");
  expect(api.checkComfyUI).toHaveBeenCalledWith("http://127.0.0.1:8188");
});
