import { useEffect, useRef, useState } from "react";
import type { ChapterSummary, JobProgress } from "../api/types";

type StreamState = {
  status: "idle" | "streaming" | "complete" | "error";
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

    source.addEventListener("complete", (event) => {
      settled = true;
      const chapter = JSON.parse((event as MessageEvent<string>).data) as ChapterSummary;
      void onCompleteRef.current?.(chapter);
      setState((previous) => ({
        status: "complete",
        progress: previous.progress,
        error: null,
      }));
      source.close();
    });

    source.addEventListener("error", (event) => {
      const data = readEventData(event);
      if (!data) {
        closeWithError("Connection lost while streaming progress.");
        return;
      }

      try {
        const payload = JSON.parse(data) as { error?: string };
        closeWithError(payload.error ?? "Connection lost while streaming progress.");
      } catch {
        closeWithError("Connection lost while streaming progress.");
      }
    });

    source.onerror = () => {
      closeWithError("Connection lost while streaming progress.");
    };

    return () => source.close();
  }, [path]);

  return state;
}
