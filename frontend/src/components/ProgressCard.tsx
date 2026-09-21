import type { JobProgress } from "../api/types";

type ProgressCardProps = {
  title: string;
  progress: JobProgress | null;
  busy: boolean;
  error?: string | null;
};

export function ProgressCard({ title, progress, busy, error }: ProgressCardProps) {
  return (
    <section className="panel progress-card">
      <div className="panel__eyebrow">Live Job</div>
      <h3>{title}</h3>
      <div className="progress-track" aria-hidden="true">
        <span style={{ width: `${progress?.percent ?? 0}%` }} />
      </div>
      <p className="progress-card__message">
        {error ? error : progress?.message ?? (busy ? "Working..." : "No active job")}
      </p>
      {progress ? (
        <div className="progress-card__meta">
          <span>{progress.stage}</span>
          <span>{progress.percent}%</span>
        </div>
      ) : null}
    </section>
  );
}
