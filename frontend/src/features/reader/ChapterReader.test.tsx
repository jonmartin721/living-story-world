import { fireEvent, render, screen } from "@testing-library/react";
import { ChapterReader } from "./ChapterReader";

describe("ChapterReader", () => {
  it("renders chapter content and routes choice clicks", () => {
    const onSelectChoice = vi.fn();

    render(
      <ChapterReader
        chapter={{
          number: 1,
          title: "Harbor",
          filename: "chapter-0001.md",
          characters_in_scene: [],
          choices: [{ id: "stay", text: "Stay", description: "Hold position" }],
          scene: null,
        }}
        content={"<!-- {\"scene_prompt\":\"x\"} -->\n# Harbor\n\nThe tide came in."}
        onSelectChoice={onSelectChoice}
      />,
    );

    expect(screen.getByText(/the tide came in/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /stay hold position/i }));
    expect(onSelectChoice).toHaveBeenCalledWith("stay");
  });
});
