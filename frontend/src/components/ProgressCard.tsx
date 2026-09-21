import type { JobProgress } from "../api/types";

type Props = {
  title: string;
  progress: JobProgress | null;
  busy: boolean;
  error?: string | null;
};

export function ProgressCard({ title, progress, busy, error }: Props) {
  if (!busy && !error) return null;
  return (
    <section className="progress-card" aria-label={title}>
      <div className="progress-card__heading">
        <span>{title}</span>
        <span>{progress?.percent ?? 0}%</span>
      </div>
      <progress max={100} value={progress?.percent ?? 0} aria-label={title} />
      <p role="status">
        {error ?? progress?.message ?? "Starting generation…"}
      </p>
    </section>
  );
}
