import { act, render, screen, waitFor } from "@testing-library/react";
import { useEventStream } from "./useEventStream";

class MockEventSource {
  listeners = new Map<string, Set<(event: Event) => void>>();
  onerror: (() => void) | null = null;

  constructor(public readonly url: string) {
    MockEventSource.instances.push(this);
  }

  static instances: MockEventSource[] = [];

  addEventListener(type: string, listener: (event: Event) => void) {
    const current = this.listeners.get(type) ?? new Set();
    current.add(listener);
    this.listeners.set(type, current);
  }

  emit(type: string, data: unknown) {
    const message = { data: JSON.stringify(data) } as MessageEvent<string>;
    this.listeners.get(type)?.forEach((listener) => listener(message));
  }

  emitNativeError() {
    this.listeners.get("error")?.forEach((listener) => listener(new Event("error")));
  }

  close() {}
}

function Harness({
  label,
  onComplete,
  onError,
}: {
  label: string;
  onComplete?: (chapter: { title: string }) => void;
  onError?: (message: string) => void;
}) {
  const state = useEventStream("/stream/test", {
    onComplete,
    onError,
  });

  return (
    <div>
      <span>{label}</span>
      <span>{state.progress?.message ?? "idle"}</span>
      <span>{state.status}</span>
    </div>
  );
}

describe("useEventStream", () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("handles chapter generation progress and completion", async () => {
    const onComplete = vi.fn();
    render(<Harness label="generation" onComplete={onComplete} />);

    const source = MockEventSource.instances[0];
    act(() => {
      source.emit("progress", { stage: "text", percent: 45, message: "Writing..." });
      source.emit("complete", { title: "Done" });
    });

    await waitFor(() => expect(screen.getByText("Writing...")).toBeInTheDocument());
    await waitFor(() => expect(onComplete).toHaveBeenCalledWith({ title: "Done" }));
  });

  it("handles reroll progress errors", async () => {
    const onError = vi.fn();
    render(<Harness label="reroll" onError={onError} />);

    const source = MockEventSource.instances[0];
    act(() => {
      source.emit("progress", { stage: "image", percent: 92, message: "Rerolling..." });
      source.emit("error", { error: "Reroll failed" });
    });

    await waitFor(() => expect(screen.getByText("Rerolling...")).toBeInTheDocument());
    await waitFor(() => expect(onError).toHaveBeenCalledWith("Reroll failed"));
  });

  it("recovers completion from job status after a transport failure", async () => {
    const onError = vi.fn();
    const onComplete = vi.fn();
    const fetchStatus = vi.fn().mockResolvedValue({ ok: true, status: 200,
      json: async () => ({ status: "complete", chapter: { title: "Recovered" } }) });
    vi.stubGlobal("fetch", fetchStatus);
    render(<Harness label="transport" onError={onError} onComplete={onComplete} />);
    act(() => {
      MockEventSource.instances[0].emitNativeError();
      MockEventSource.instances[0].onerror?.();
    });
    await waitFor(() => expect(onComplete).toHaveBeenCalledWith({ title: "Recovered" }));
    expect(onError).not.toHaveBeenCalled();
    expect(fetchStatus).toHaveBeenCalledTimes(1);
    expect(fetchStatus).toHaveBeenCalledWith("/jobs/test", expect.objectContaining({ signal: expect.any(AbortSignal) }));
  });

  it("reports expired jobs without starting another generation", async () => {
    const onError = vi.fn();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ status: 404 }));
    render(<Harness label="expired" onError={onError} />);
    act(() => MockEventSource.instances[0].emitNativeError());
    await waitFor(() => expect(onError).toHaveBeenCalledWith(expect.stringContaining("no longer available")));
  });

  it("cancels status recovery when unmounted", async () => {
    const onComplete = vi.fn();
    let resolve!: (value: unknown) => void;
    const fetchStatus = vi.fn().mockReturnValue(new Promise((done) => { resolve = done; }));
    vi.stubGlobal("fetch", fetchStatus);
    const { unmount } = render(<Harness label="pending" onComplete={onComplete} />);
    act(() => MockEventSource.instances[0].emitNativeError());
    const signal = fetchStatus.mock.calls[0][1].signal;
    unmount();
    await act(async () => resolve({ status: 200, ok: true, json: async () => ({ status: "complete", chapter: { title: "Late" } }) }));
    expect(signal.aborted).toBe(true);
    expect(onComplete).not.toHaveBeenCalled();
  });
});
