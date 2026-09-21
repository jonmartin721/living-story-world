import { useState } from "react";
import type { WorldSummary } from "../../api/types";
import { displayName } from "./options";

type Props = {
  worlds: WorldSummary[];
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
  onCreate: () => void;
  onRandom: () => void;
  busy?: boolean;
};

export function WorldList({
  worlds,
  selectedSlug,
  onSelect,
  onCreate,
  onRandom,
  busy = false,
}: Props) {
  const [query, setQuery] = useState("");
  const shown = worlds.filter((world) =>
    `${world.title} ${world.theme}`
      .toLowerCase()
      .includes(query.toLowerCase().trim()),
  );
  return (
    <section className="world-library">
      <div className="library-toolbar">
        <div className="sidebar__actions">
          <button type="button" className="button" onClick={onCreate}>
            New world
          </button>
          <button
            type="button"
            className="button button--ghost"
            disabled={busy}
            aria-busy={busy}
            onClick={onRandom}
          >
            {busy ? "Generating…" : "Random world"}
          </button>
        </div>
        {!!worlds.length && (
          <label className="library-search">
            <input
              type="search"
              aria-label="Search worlds"
              placeholder="Search worlds"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
        )}
      </div>
      {shown.length ? (
        <div className="world-list">
          {shown.map((world) => (
            <button
              key={world.slug}
              type="button"
              aria-pressed={world.slug === selectedSlug}
              className={`world-card ${world.slug === selectedSlug ? "world-card--active" : ""}`}
              onClick={() => onSelect(world.slug)}
            >
              <span className="world-card__cover" aria-hidden="true">
                <span>{world.title.charAt(0)}</span>
              </span>
              <span className="world-card__body">
                <span className="eyebrow">{displayName(world.preset)}</span>
                <span className="world-card__title">
                  <strong>{world.title}</strong>
                </span>
                <p>{world.theme}</p>
                <span className="world-card__footer">
                  <span>
                    {world.chapter_count}{" "}
                    {world.chapter_count === 1 ? "chapter" : "chapters"}
                  </span>
                  <span>
                    {world.slug === selectedSlug
                      ? "Continue reading"
                      : "Open world"}{" "}
                    →
                  </span>
                </span>
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div className="library-empty">
          <h2>{query ? "No worlds found" : "No worlds yet"}</h2>
          <p className="muted">
            {query
              ? "Try another title or a word from your premise."
              : "Create a world to start a story."}
          </p>
          {query && (
            <button
              className="text-button"
              type="button"
              onClick={() => setQuery("")}
            >
              Clear search
            </button>
          )}
        </div>
      )}
    </section>
  );
}
