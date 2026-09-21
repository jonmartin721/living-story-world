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


it("applies changed reader preferences to the chapter body", () => {
  const chapter = { number: 1, title: "Harbor", filename: "1.md", characters_in_scene: [], choices: [] };
  const { container, rerender } = render(<ChapterReader chapter={chapter} onSelectChoice={vi.fn()} content="Story" fontFamily="Georgia" fontSize="medium" />);
  const body = container.querySelector<HTMLElement>(".reader__body")!;
  expect(body.style.fontFamily).toContain("Georgia");
  const medium = body.style.fontSize;
  rerender(<ChapterReader chapter={chapter} onSelectChoice={vi.fn()} content="Story" fontFamily="monospace" fontSize="large" />);
  expect(body.style.fontFamily).toContain("Courier");
  expect(body.style.fontSize).not.toBe(medium);
});
