import { startTransition, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api/client";
import type {
  ChapterSummary,
  GenerationRequest,
  RandomWorldResponse,
  SettingsResponse,
  SettingsUpdateRequest,
  WorldDetail,
  WorldInput,
  WorldSummary,
} from "./api/types";
import { ProgressCard } from "./components/ProgressCard";
import { ToastShelf } from "./components/ToastShelf";
import { ChapterTimeline } from "./features/chapters/ChapterTimeline";
import { ChapterReader } from "./features/reader/ChapterReader";
import { SettingsPanel } from "./features/settings/SettingsPanel";
import { WorldEditor } from "./features/worlds/WorldEditor";
import { WorldList } from "./features/worlds/WorldList";
import { useEventStream } from "./hooks/useEventStream";
import { useToastQueue } from "./hooks/useToastQueue";

type JobState = {
  slug: string;
  jobId: string;
  label: string;
};

type EditorState = "create" | "edit" | null;

function savedJob(): JobState | null {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem("activeChapterJob") ?? "null");
    if (value && typeof value === "object" && "slug" in value && "jobId" in value &&
        typeof value.slug === "string" && /^[a-z0-9-]+$/i.test(value.slug) &&
        typeof value.jobId === "string" && /^[a-z0-9-]+$/i.test(value.jobId)) {
      return { slug: value.slug, jobId: value.jobId, label: "Chapter generation" };
    }
  } catch { /* Storage may be unavailable in private browsing. */ }
  return null;
}

const defaultGenerationRequest: GenerationRequest = {
  no_images: false,
  chapter_length: "medium",
};

export function App() {
  const [worlds, setWorlds] = useState<WorldSummary[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [worldDetail, setWorldDetail] = useState<WorldDetail | null>(null);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [chapterContent, setChapterContent] = useState<Record<string, string>>({});
  const selectedSlugRef = useRef(selectedSlug);
  selectedSlugRef.current = selectedSlug;
  const [selectedChapterNumber, setSelectedChapterNumber] = useState<number | null>(null);
  const [generationRequest, setGenerationRequest] = useState<GenerationRequest>(
    defaultGenerationRequest,
  );
  const [activeJob, setActiveJob] = useState<JobState | null>(savedJob);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [editorState, setEditorState] = useState<EditorState>(null);
  const [randomWorld, setRandomWorld] = useState<RandomWorldResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const { toasts, pushToast, dismissToast } = useToastQueue();

  const selectedChapter = useMemo<ChapterSummary | null>(() => {
    if (!worldDetail || selectedChapterNumber === null) {
      return null;
    }
    return (
      worldDetail.chapters.find((chapter) => chapter.number === selectedChapterNumber) ??
      null
    );
  }, [selectedChapterNumber, worldDetail]);

  const streamState = useEventStream(
    activeJob ? `/api/worlds/${activeJob.slug}/chapters/stream/${activeJob.jobId}` : null,
    {
      onComplete: async (chapter) => {
        pushToast(`${activeJob?.label ?? "Chapter job"} finished.`, "success");
        if (activeJob?.slug === selectedSlugRef.current) setSelectedChapterNumber(chapter.number);
        setChapterContent((current) => {
          const next = { ...current };
          delete next[`${activeJob?.slug}:${chapter.number}`];
          return next;
        });
        setActiveJob(null);
        try {
          await refreshSelectedWorld(activeJob?.slug ?? null, chapter.number);
        } catch (error) {
          pushToast((error as Error).message, "error");
        }
      },
      onError: (message) => {
        pushToast(message, "error");
        setActiveJob(null);
      },
    },
  );

  useEffect(() => {
    try {
      if (activeJob) sessionStorage.setItem("activeChapterJob", JSON.stringify(activeJob));
      else sessionStorage.removeItem("activeChapterJob");
    } catch { /* Job discovery still works when storage is unavailable. */ }
  }, [activeJob]);

  useEffect(() => {
    void loadWorlds().catch((error: Error) => pushToast(error.message, "error"));
    void loadSettings().catch((error: Error) => pushToast(error.message, "error"));
  }, []);

  useEffect(() => {
    if (!selectedSlug) {
      setWorldDetail(null);
      return;
    }
    setWorldDetail(null);
    setSelectedChapterNumber(null);
    void refreshSelectedWorld(selectedSlug).catch((error: Error) => pushToast(error.message, "error"));
    void api.getCurrentChapterJob(selectedSlug).then((job) => {
      if (job && selectedSlugRef.current === selectedSlug) {
        setActiveJob((current) => current ?? { slug: selectedSlug, jobId: job.job_id, label: "Chapter generation" });
      }
    }).catch((error: Error) => pushToast(error.message, "error"));
  }, [selectedSlug]);

  useEffect(() => {
    const key = `${selectedSlug}:${selectedChapterNumber}`;
    if (!selectedSlug || selectedChapterNumber === null || chapterContent[key]) {
      return;
    }
    void api
      .getChapterContent(selectedSlug, selectedChapterNumber)
      .then((response) => {
        setChapterContent((current) => ({ ...current, [key]: response.content }));
      })
      .catch((error: Error) => pushToast(error.message, "error"));
  }, [chapterContent, pushToast, selectedChapterNumber, selectedSlug]);

  async function loadWorlds() {
    const list = await api.listWorlds();
    setWorlds(list);
    const currentWorld = list.find((world) => world.is_current) ?? list[0] ?? null;
    setSelectedSlug((previous) => previous ?? currentWorld?.slug ?? null);
  }

  async function loadSettings() {
    const response = await api.getSettings();
    setSettings(response);
  }

  async function refreshSelectedWorld(slug: string | null, preferredChapter?: number) {
    if (!slug) {
      return;
    }
    const detail = await api.getWorld(slug);
    if (selectedSlugRef.current !== slug) return;
    startTransition(() => {
      setWorldDetail(detail);
      setSelectedChapterNumber(
        preferredChapter ??
          detail.chapters[detail.chapters.length - 1]?.number ??
          detail.chapters[0]?.number ??
          null,
      );
    });
    void loadWorlds().catch((error: Error) => pushToast(error.message, "error"));
  }

  async function handleWorldSubmit(input: WorldInput) {
    setBusy(true);
    try {
      if (editorState === "edit" && selectedSlug) {
        await api.updateWorld(selectedSlug, input);
        pushToast("World updated.", "success");
        await refreshSelectedWorld(selectedSlug);
      } else {
        const created = await api.createWorld(input);
        setSelectedSlug(created.slug);
        pushToast(`Created ${created.title}.`, "success");
      }
      setEditorState(null);
      setRandomWorld(null);
      await loadWorlds();
    } catch (error) {
      pushToast((error as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleRandomWorld() {
    setBusy(true);
    try {
      const generated = await api.getRandomWorld();
      setRandomWorld(generated);
      setEditorState("create");
    } catch (error) {
      pushToast((error as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveSettings(input: SettingsUpdateRequest) {
    setBusy(true);
    try {
      await api.updateSettings(input);
      pushToast("Settings saved.", "success");
      await loadSettings();
    } catch (error) {
      pushToast((error as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleClearKeys() {
    setBusy(true);
    try {
      await api.clearKeys();
      pushToast("API keys cleared.", "success");
      await loadSettings();
    } catch (error) {
      pushToast((error as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleSelectWorld(slug: string) {
    if (slug === selectedSlug) {
      return;
    }
    try {
      await api.setCurrentWorld(slug);
      setSelectedSlug(slug);
    } catch (error) {
      pushToast((error as Error).message, "error");
    }
  }

  async function handleDeleteWorld() {
    if (!selectedSlug || !worldDetail) {
      return;
    }
    setBusy(true);
    try {
      await api.deleteWorld(selectedSlug);
      pushToast(`Deleted ${worldDetail.config.title}.`, "success");
      setSelectedSlug(null);
      setWorldDetail(null);
      setChapterContent({});
      await loadWorlds();
    } catch (error) {
      pushToast((error as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function launchJob(label: string, run: () => Promise<{ job_id: string }>) {
    if (!selectedSlug) {
      return;
    }
    setBusy(true);
    try {
      const response = await run();
      setActiveJob({ slug: selectedSlug, jobId: response.job_id, label });
    } catch (error) {
      pushToast((error as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleSelectChoice(choiceId: string) {
    if (!selectedSlug || !selectedChapter) {
      return;
    }
    setBusy(true);
    try {
      await api.selectChoice(selectedSlug, selectedChapter.number, choiceId);
      pushToast("Choice locked in.", "success");
      await refreshSelectedWorld(selectedSlug, selectedChapter.number);
    } catch (error) {
      pushToast((error as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleRegenerateImage(chapterNumber: number) {
    if (!selectedSlug) {
      return;
    }
    setBusy(true);
    try {
      await api.regenerateImage(selectedSlug, chapterNumber);
      pushToast("Scene image regenerated.", "success");
      await refreshSelectedWorld(selectedSlug, chapterNumber);
    } catch (error) {
      pushToast((error as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteChapter(chapterNumber: number) {
    if (!selectedSlug) {
      return;
    }
    setBusy(true);
    try {
      await api.deleteChapter(selectedSlug, chapterNumber);
      pushToast(`Chapter ${chapterNumber} deleted.`, "success");
      setChapterContent((current) => {
        const next = { ...current };
        delete next[`${selectedSlug}:${chapterNumber}`];
        return next;
      });
      await refreshSelectedWorld(selectedSlug);
    } catch (error) {
      pushToast((error as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <span className="hero__kicker">Persistent narrative engine</span>
          <h1>Living Storyworld</h1>
          <p>
            Create a world, meet its characters, and choose where the story goes next.
          </p>
        </div>
        <div className="hero__actions">
          <button type="button" className="button button--ghost" onClick={() => setSettingsOpen(true)}>
            Settings
          </button>
          <button type="button" className="button button--ghost" onClick={handleDeleteWorld} disabled={!selectedSlug || busy}>
            Delete World
          </button>
          <button type="button" className="button" onClick={() => setEditorState("edit")} disabled={!worldDetail}>
            Edit World
          </button>
        </div>
      </header>

      <div className="layout">
        <WorldList
          worlds={worlds}
          selectedSlug={selectedSlug}
          onSelect={(slug) => void handleSelectWorld(slug)}
          onCreate={() => {
            setRandomWorld(null);
            setEditorState("create");
          }}
          onRandom={() => void handleRandomWorld()}
        />

        <main className="content">
          {editorState && settings ? (
            <WorldEditor
              mode={editorState}
              world={worldDetail}
              randomWorld={randomWorld}
              settings={settings}
              busy={busy}
              onCancel={() => {
                setEditorState(null);
                setRandomWorld(null);
              }}
              onSubmit={(value) => void handleWorldSubmit(value)}
            />
          ) : null}

          {settingsOpen ? (
            <SettingsPanel
              settings={settings}
              busy={busy}
              onClose={() => setSettingsOpen(false)}
              onSave={(value) => void handleSaveSettings(value)}
              onClearKeys={() => void handleClearKeys()}
            />
          ) : null}

          <section className="panel world-summary">
            <div className="panel__eyebrow">Active World</div>
            <div className="world-summary__header">
              <div>
                <h2>{worldDetail?.config.title ?? "Pick a world"}</h2>
                <p>{worldDetail?.config.theme ?? "Create or select a world to get started."}</p>
              </div>
              <div className="world-summary__controls">
                <label>
                  Length
                  <select
                    value={generationRequest.chapter_length}
                    onChange={(event) =>
                      setGenerationRequest((current) => ({
                        ...current,
                        chapter_length: event.target.value as GenerationRequest["chapter_length"],
                      }))
                    }
                  >
                    <option value="short">Short</option>
                    <option value="medium">Medium</option>
                    <option value="long">Long</option>
                  </select>
                </label>
                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={generationRequest.no_images}
                    onChange={(event) =>
                      setGenerationRequest((current) => ({
                        ...current,
                        no_images: event.target.checked,
                      }))
                    }
                  />
                  Skip image generation
                </label>
                <button
                  type="button"
                  className="button"
                  disabled={!selectedSlug || busy || !!activeJob}
                  onClick={() =>
                    void launchJob("Chapter generation", () =>
                      api.startChapterGeneration(selectedSlug!, generationRequest),
                    )
                  }
                >
                  Generate Chapter
                </button>
              </div>
            </div>
            {worldDetail ? (
              <div className="world-summary__meta">
                <span>{worldDetail.chapters.length} chapters</span>
                <span>{worldDetail.config.preset}</span>
                <span>{worldDetail.config.style_pack}</span>
                <span>{worldDetail.config.image_model}</span>
              </div>
            ) : null}
          </section>

          <ProgressCard
            title={activeJob?.label ?? "No active job"}
            busy={!!activeJob}
            progress={streamState.progress}
            error={streamState.error}
          />

          <div className="content-grid">
            <ChapterTimeline
              chapters={worldDetail?.chapters ?? []}
              selectedChapterNumber={selectedChapterNumber}
              onSelect={setSelectedChapterNumber}
              onReroll={(chapterNumber) =>
                void launchJob("Chapter reroll", () =>
                  api.rerollChapter(selectedSlug!, chapterNumber, generationRequest),
                )
              }
              onRegenerateImage={(chapterNumber) => void handleRegenerateImage(chapterNumber)}
              onDelete={(chapterNumber) => void handleDeleteChapter(chapterNumber)}
            />

            <ChapterReader
              chapter={selectedChapter}
              fontFamily={settings?.reader_font_family}
              fontSize={settings?.reader_font_size}
              content={
                selectedChapterNumber !== null ? chapterContent[`${selectedSlug}:${selectedChapterNumber}`] ?? "" : ""
              }
              onSelectChoice={(choiceId) => void handleSelectChoice(choiceId)}
            />
          </div>
        </main>
      </div>

      <ToastShelf toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
