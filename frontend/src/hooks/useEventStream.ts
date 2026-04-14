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
    setState({ status: "streaming", progress: null, error: null });

    source.addEventListener("progress", (event) => {
      const progress = JSON.parse((event as MessageEvent<string>).data) as JobProgress;
      setState({ status: "streaming", progress, error: null });
    });

    source.addEventListener("complete", (event) => {
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
      const payload = JSON.parse((event as MessageEvent<string>).data) as { error: string };
      onErrorRef.current?.(payload.error);
      setState((previous) => ({
        status: "error",
        progress: previous.progress,
        error: payload.error,
      }));
      source.close();
    });

    source.onerror = () => {
      onErrorRef.current?.("Connection lost while streaming progress.");
      setState((previous) => ({
        status: "error",
        progress: previous.progress,
        error: "Connection lost while streaming progress.",
      }));
      source.close();
    };

    return () => source.close();
  }, [path]);

  return state;
}
