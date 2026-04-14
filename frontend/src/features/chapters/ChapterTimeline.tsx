import type { ChapterSummary } from "../../api/types";

type ChapterTimelineProps = {
  chapters: ChapterSummary[];
  selectedChapterNumber: number | null;
  onSelect: (chapterNumber: number) => void;
  onReroll: (chapterNumber: number) => void;
  onRegenerateImage: (chapterNumber: number) => void;
  onDelete: (chapterNumber: number) => void;
};

export function ChapterTimeline({
  chapters,
  selectedChapterNumber,
  onSelect,
  onReroll,
  onRegenerateImage,
  onDelete,
}: ChapterTimelineProps) {
  return (
    <section className="panel chapter-timeline">
      <div className="panel__eyebrow">Chapters</div>
      <h2>Story Arc</h2>
      <div className="timeline-list">
        {chapters.map((chapter) => (
          <article
            key={chapter.number}
            className={`chapter-card ${
              chapter.number === selectedChapterNumber ? "chapter-card--active" : ""
            }`}
          >
            <button type="button" className="chapter-card__body" onClick={() => onSelect(chapter.number)}>
              <div className="chapter-card__heading">
                <strong>
                  {chapter.number}. {chapter.title}
                </strong>
                <span>{chapter.generated_at ? new Date(chapter.generated_at).toLocaleString() : "Drafted"}</span>
              </div>
              <p>{chapter.ai_summary ?? chapter.summary ?? "No summary yet."}</p>
              <div className="chapter-card__meta">
                <span>{chapter.text_model_used ?? "model pending"}</span>
                {chapter.image_model_used ? <span>{chapter.image_model_used}</span> : null}
              </div>
            </button>
            <div className="chapter-card__actions">
              <button type="button" className="button button--ghost" onClick={() => onReroll(chapter.number)}>
                Reroll
              </button>
              <button
                type="button"
                className="button button--ghost"
                onClick={() => onRegenerateImage(chapter.number)}
              >
                Image
              </button>
              <button type="button" className="button button--ghost" onClick={() => onDelete(chapter.number)}>
                Delete
              </button>
            </div>
          </article>
        ))}
        {chapters.length === 0 ? <p className="empty-state">Generate the first chapter to start the world.</p> : null}
      </div>
    </section>
  );
}
