import { useEffect, useRef, useState } from "react";
import type { ChapterJobStatus, ChapterSummary, JobProgress } from "../api/types";

type StreamState = {
  status: "idle" | "streaming" | "reconnecting" | "complete" | "error";
  progress: JobProgress | null;
  error: string | null;
};

type StreamOptions = {
  onComplete?: (chapter: ChapterSummary) => void | Promise<void>;
  onError?: (message: string) => void;
};

function readEventData(event: Event): string | null {
  const maybeMessage = event as Partial<MessageEvent<string>>;
  return typeof maybeMessage.data === "string" ? maybeMessage.data : null;
}

export function useEventStream(path: string | null, options: StreamOptions = {}) {
  const onCompleteRef = useRef(options.onComplete);
  const onErrorRef = useRef(options.onError);
  const [state, setState] = useState<StreamState>({
    status: "idle",
    progress: null,
    error: null,
  });

  useEffect(() => {
    onCompleteRef.current = options.onComplete;
    onErrorRef.current = options.onError;
  }, [options.onComplete, options.onError]);

  useEffect(() => {
    if (!path) {
      setState({ status: "idle", progress: null, error: null });
      return;
    }

    const source = new EventSource(path);
    let settled = false;
    let polling = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const controller = new AbortController();
    setState({ status: "streaming", progress: null, error: null });

    const closeWithError = (message: string) => {
      if (settled) {
        return;
      }
      settled = true;
      onErrorRef.current?.(message);
      setState((previous) => ({
        status: "error",
        progress: previous.progress,
        error: message,
      }));
      source.close();
    };

    source.addEventListener("progress", (event) => {
      const progress = JSON.parse((event as MessageEvent<string>).data) as JobProgress;
      setState({ status: "streaming", progress, error: null });
    });

    const complete = (chapter: ChapterSummary) => {
      if (settled) return;
      settled = true;
      void onCompleteRef.current?.(chapter);
      setState((previous) => ({
        status: "complete",
        progress: previous.progress,
        error: null,
      }));
      source.close();
    };

    const pollStatus = async () => {
      try {
        const response = await fetch(path.replace("/stream/", "/jobs/"), { signal: controller.signal });
        if (settled) return;
        if (response.status === 404) {
          closeWithError("This job is no longer available. Reload the world to check its latest chapter.");
          return;
        }
        if (!response.ok) throw new Error("Status unavailable");
        const job = await response.json() as ChapterJobStatus;
        if (settled) return;
        if (job.status === "complete" && job.chapter) { complete(job.chapter); return; }
        if (job.status === "error") { closeWithError(job.error ?? "Chapter generation failed."); return; }
        setState({ status: "reconnecting", progress: job.progress, error: null });
      } catch {
        if (settled || controller.signal.aborted) return;
        setState((previous) => ({ ...previous, status: "reconnecting", error: "Connection lost. Retrying job status..." }));
      }
      if (!settled) timer = setTimeout(() => void pollStatus(), 2000);
    };

    const recoverConnection = () => {
      if (settled || polling) return;
      polling = true;
      source.close();
      setState((previous) => ({ ...previous, status: "reconnecting", error: "Connection lost. Checking job status..." }));
      void pollStatus();
    };

    source.addEventListener("complete", (event) => {
      const chapter = JSON.parse((event as MessageEvent<string>).data) as ChapterSummary;
      complete(chapter);
    });

    source.addEventListener("error", (event) => {
      const data = readEventData(event);
      if (!data) {
        recoverConnection();
        return;
      }

      try {
        const payload = JSON.parse(data) as { error?: string };
        closeWithError(payload.error ?? "Connection lost while streaming progress.");
      } catch {
        closeWithError("Connection lost while streaming progress.");
      }
    });

    source.onerror = recoverConnection;

    return () => {
      settled = true;
      source.close();
      controller.abort();
      clearTimeout(timer);
    };
  }, [path]);

  return state;
}
