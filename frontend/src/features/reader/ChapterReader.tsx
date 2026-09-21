import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import type { ChapterSummary } from "../../api/types";

type ChapterReaderProps = {
  chapter: ChapterSummary | null;
  content: string;
  onSelectChoice: (choiceId: string) => void;
  fontFamily?: string;
  fontSize?: string;
  choicesDisabled?: boolean;
  historical?: boolean;
  headerActions?: ReactNode;
  footer?: ReactNode;
  emptyTitle?: string;
};

const fontFamilies: Record<string, string> = {
  Georgia: 'Georgia, "Times New Roman", serif',
  serif: 'Georgia, "Times New Roman", serif',
  "sans-serif":
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  monospace: '"Courier New", Courier, monospace',
};
const fontSizes: Record<string, string> = {
  small: "clamp(1rem, 1rem + 0.5vw, 1.125rem)",
  medium: "clamp(1.125rem, 1rem + 0.5vw, 1.375rem)",
  large: "clamp(1.25rem, 1.5rem + 0.5vw, 1.625rem)",
  xl: "clamp(1.5rem, 1.75rem + 0.5vw, 2rem)",
};

function storyBody(content: string, title: string) {
  const text = content.replace(/^<!--[\s\S]*?-->\s*/m, "");
  const heading = text.match(/^# ([^\n]+)\n*/);
  const headingTitle = heading?.[1]
    .replace(/^Chapter\s+\d+\s*[:—-]\s*/i, "")
    .trim();
  return headingTitle?.toLowerCase() === title.trim().toLowerCase()
    ? text.slice(heading![0].length)
    : text;
}

export function ChapterReader({
  chapter,
  content,
  onSelectChoice,
  fontFamily = "Georgia",
  fontSize = "medium",
  choicesDisabled = false,
  historical = false,
  headerActions,
  footer,
  emptyTitle,
}: ChapterReaderProps) {
  const body = chapter ? storyBody(content, chapter.title) : "";
  const minutes = Math.max(1, Math.ceil(body.split(/\s+/).length / 220));
  return (
    <article className="reader">
      <header className="reader__header">
        {chapter && (
          <div className="reader__topline">
            <span className="eyebrow">
              {`Chapter ${String(chapter.number).padStart(2, "0")}`}
            </span>
            <div className="reader__tools">
              {chapter && content && (
                <span className="reading-time">{minutes} min read</span>
              )}
              {headerActions}
            </div>
          </div>
        )}
        <h1>{chapter?.title ?? emptyTitle ?? "Create a world"}</h1>
      </header>
      {chapter?.scene && (
        <img
          className="reader__scene"
          src={chapter.scene}
          alt={`Illustration for ${chapter.title}`}
        />
      )}
      {chapter && (
        <div
          className="reader__body"
          style={{
            fontFamily: fontFamilies[fontFamily] ?? fontFamilies.Georgia,
            fontSize: fontSizes[fontSize] ?? fontSizes.medium,
          }}
        >
          {content ? (
            <ReactMarkdown>{body}</ReactMarkdown>
          ) : (
            <p role="status" className="muted">
              Opening chapter...
            </p>
          )}
        </div>
      )}
      {!!chapter?.choices.length && (
        <fieldset
          className="story-choices"
          disabled={choicesDisabled || historical}
        >
          <legend className="eyebrow">
            {historical ? "Selected choice" : "What happens next?"}
          </legend>
          {chapter.choices.map((choice) => (
            <label className="story-choice" key={choice.id}>
              <input
                type="radio"
                name={`chapter-${chapter.number}-choice`}
                checked={chapter.selected_choice_id === choice.id}
                onChange={() => onSelectChoice(choice.id)}
              />
              <span>
                <strong>{choice.text}</strong>
                {choice.description && (
                  <span className="story-choice__description">
                    {choice.description}
                  </span>
                )}
              </span>
            </label>
          ))}
          {historical && (
            <p className="muted">
              Choices in earlier chapters cannot be changed.
            </p>
          )}
        </fieldset>
      )}
      {footer}
    </article>
  );
}
