import type { WorldSummary } from "../../api/types";

type Props = {
  worlds: WorldSummary[];
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
  onCreate: () => void;
  onRandom: () => void;
};

export function WorldList({ worlds, selectedSlug, onSelect, onCreate, onRandom }: Props) {
  return (
    <aside className="panel sidebar">
      <div className="panel__eyebrow">Your worlds</div>
      <div className="sidebar__header"><h2>Library</h2><span className="pill">{worlds.length}</span></div>
      <div className="sidebar__actions">
        <button type="button" className="button" onClick={onCreate}>New world</button>
        <button type="button" className="button button--ghost" onClick={onRandom}>Surprise me</button>
      </div>
      <div className="world-list">
        {worlds.map((world) => (
          <button key={world.slug} type="button" aria-pressed={world.slug === selectedSlug}
            className={`world-card ${world.slug === selectedSlug ? "world-card--active" : ""}`}
            onClick={() => onSelect(world.slug)}>
            <div className="world-card__title"><strong>{world.title}</strong><span className="pill">{world.chapter_count} chapters</span></div>
            <p>{world.theme}</p>
            <span className="pill pill--muted">{world.preset}</span>
          </button>
        ))}
        {!worlds.length && <p className="empty-state">Create a world to begin your story.</p>}
      </div>
    </aside>
  );
}
