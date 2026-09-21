import ReactMarkdown from "react-markdown";
import type { ChapterSummary } from "../../api/types";

type ChapterReaderProps = {
  chapter: ChapterSummary | null;
  content: string;
  onSelectChoice: (choiceId: string) => void;
  fontFamily?: string;
  fontSize?: string;
};

const fontFamilies: Record<string, string> = {
  Georgia: 'Georgia, "Times New Roman", serif',
  serif: 'Georgia, "Times New Roman", serif',
  "sans-serif": '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  monospace: '"Courier New", Courier, monospace',
};
const fontSizes: Record<string, string> = {
  small: "clamp(1rem, 1rem + 0.5vw, 1.125rem)",
  medium: "clamp(1.125rem, 1.25rem + 0.5vw, 1.375rem)",
  large: "clamp(1.25rem, 1.5rem + 0.5vw, 1.625rem)",
  xl: "clamp(1.5rem, 1.75rem + 0.5vw, 2rem)",
};

function stripMetadata(content: string) {
  return content.replace(/^<!--[\s\S]*?-->\s*/m, "");
}

export function ChapterReader({ chapter, content, onSelectChoice, fontFamily = "Georgia", fontSize = "medium" }: ChapterReaderProps) {
  if (!chapter) {
    return (
      <section className="panel reader">
        <div className="panel__eyebrow">Reader</div>
        <h2>Select a chapter</h2>
        <p className="empty-state">The story text shows up here once you pick a chapter.</p>
      </section>
    );
  }

  return (
    <section className="panel reader">
      <div className="reader__header">
        <div>
          <div className="panel__eyebrow">Reader</div>
          <h2>{chapter.title}</h2>
        </div>
        <div className="reader__meta">
          <span>{chapter.text_model_used ?? "unknown model"}</span>
          {chapter.image_model_used ? <span>{chapter.image_model_used}</span> : null}
        </div>
      </div>

      {chapter.scene ? (
        <img className="reader__scene" src={chapter.scene} alt={chapter.title} />
      ) : null}

      <div className="reader__body" style={{ fontFamily: fontFamilies[fontFamily] ?? fontFamilies.Georgia, fontSize: fontSizes[fontSize] ?? fontSizes.medium }}>
        <ReactMarkdown>{stripMetadata(content)}</ReactMarkdown>
      </div>

      {chapter.choices.length > 0 ? (
        <div className="choice-grid">
          {chapter.choices.map((choice) => (
            <button
              key={choice.id}
              type="button"
              className={`choice-card ${
                chapter.selected_choice_id === choice.id ? "choice-card--selected" : ""
              }`}
              onClick={() => onSelectChoice(choice.id)}
            >
              <strong>{choice.text}</strong>
              <span>{choice.description}</span>
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
