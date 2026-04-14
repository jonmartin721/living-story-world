import ReactMarkdown from "react-markdown";
import type { ChapterSummary } from "../../api/types";

type ChapterReaderProps = {
  chapter: ChapterSummary | null;
  content: string;
  onSelectChoice: (choiceId: string) => void;
};

function stripMetadata(content: string) {
  return content.replace(/^<!--[\s\S]*?-->\s*/m, "");
}

export function ChapterReader({ chapter, content, onSelectChoice }: ChapterReaderProps) {
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

      <div className="reader__body">
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
