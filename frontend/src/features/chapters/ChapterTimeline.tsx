import type { ChapterSummary } from "../../api/types";

type Props = {
  chapters: ChapterSummary[];
  selectedChapterNumber: number | null;
  onSelect: (chapterNumber: number) => void;
};

export function ChapterTimeline({
  chapters,
  selectedChapterNumber,
  onSelect,
}: Props) {
  return (
    <nav className="chapter-timeline" aria-label="Chapters">
      <div className="eyebrow">
        Chapters <span>{chapters.length.toString().padStart(2, "0")}</span>
      </div>
      <ol className="chapter-list">
        {chapters.map((chapter) => (
          <li key={chapter.number}>
            <button
              type="button"
              aria-current={
                chapter.number === selectedChapterNumber ? "page" : undefined
              }
              className="chapter-link"
              onClick={() => onSelect(chapter.number)}
            >
              <span className="chapter-link__number">
                {chapter.number.toString().padStart(2, "0")}
              </span>
              <span>{chapter.title}</span>
            </button>
          </li>
        ))}
      </ol>
      {!chapters.length && <p className="empty-state">No chapters yet.</p>}
    </nav>
  );
}
