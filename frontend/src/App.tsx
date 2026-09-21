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
import { Workspace } from "./components/Workspace";
import { Inspector } from "./components/Inspector";
import { hasProviderKey } from "./features/settings/connections";
import { Dialog } from "./components/Dialog";
import { AppearancePanel } from "./features/settings/AppearancePanel";
import {
  applyTheme,
  readTheme,
  themeStorageKey,
  type Theme,
} from "./features/settings/themes";
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
    const value: unknown = JSON.parse(
      sessionStorage.getItem("activeChapterJob") ?? "null",
    );
    if (
      value &&
      typeof value === "object" &&
      "slug" in value &&
      "jobId" in value &&
      typeof value.slug === "string" &&
      /^[a-z0-9-]+$/i.test(value.slug) &&
      typeof value.jobId === "string" &&
      /^[a-z0-9-]+$/i.test(value.jobId)
    ) {
      return {
        slug: value.slug,
        jobId: value.jobId,
        label: "Chapter generation",
      };
    }
  } catch {
    /* Storage may be unavailable in private browsing. */
  }
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
  const [chapterContent, setChapterContent] = useState<Record<string, string>>(
    {},
  );
  const selectedSlugRef = useRef(selectedSlug);
  selectedSlugRef.current = selectedSlug;
  const [selectedChapterNumber, setSelectedChapterNumber] = useState<
    number | null
  >(null);
  const [generationRequest, setGenerationRequest] = useState<GenerationRequest>(
    defaultGenerationRequest,
  );
  const [activeJob, setActiveJob] = useState<JobState | null>(savedJob);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [appearanceOpen, setAppearanceOpen] = useState(false);
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [chaptersOpen, setChaptersOpen] = useState(false);
  const [loreOpen, setLoreOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>(readTheme);
  const [confirmation, setConfirmation] = useState<{
    kind: "world" | "chapter";
    chapterNumber?: number;
  } | null>(null);
  const [editorState, setEditorState] = useState<EditorState>(null);
  const [randomWorld, setRandomWorld] = useState<RandomWorldResponse | null>(
    null,
  );
  const [busy, setBusy] = useState(false);
  const [generationError, setGenerationError] = useState("");
  const [initializing, setInitializing] = useState(true);
  const [loadError, setLoadError] = useState("");
  const { toasts, pushToast, dismissToast } = useToastQueue();

  useEffect(() => {
    applyTheme(theme);
    try {
      window.localStorage.setItem(themeStorageKey, theme);
    } catch {
      /* Keep the theme usable without storage. */
    }
  }, [theme]);

  const selectedChapter = useMemo<ChapterSummary | null>(() => {
    if (!worldDetail || selectedChapterNumber === null) {
      return null;
    }
    return (
      worldDetail.chapters.find(
        (chapter) => chapter.number === selectedChapterNumber,
      ) ?? null
    );
  }, [selectedChapterNumber, worldDetail]);

  const streamState = useEventStream(
    activeJob
      ? `/api/worlds/${activeJob.slug}/chapters/stream/${activeJob.jobId}`
      : null,
    {
      onComplete: async (chapter) => {
        pushToast(`${activeJob?.label ?? "Chapter job"} finished.`, "success");
        if (activeJob?.slug === selectedSlugRef.current)
          setSelectedChapterNumber(chapter.number);
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
        setGenerationError(message);
        setActiveJob(null);
      },
    },
  );

  useEffect(() => {
    try {
      if (activeJob)
        sessionStorage.setItem("activeChapterJob", JSON.stringify(activeJob));
      else sessionStorage.removeItem("activeChapterJob");
    } catch {
      /* Job discovery still works when storage is unavailable. */
    }
  }, [activeJob]);

  async function initialize() {
    setInitializing(true);
    setLoadError("");
    try {
      await Promise.all([loadWorlds(), loadSettings()]);
    } catch (error) {
      setLoadError((error as Error).message);
    } finally {
      setInitializing(false);
    }
  }
  useEffect(() => {
    void initialize();
  }, []);

  useEffect(() => {
    if (!selectedSlug) {
      setWorldDetail(null);
      return;
    }
    setWorldDetail(null);
    setGenerationError("");
    setLoadError("");
    setSelectedChapterNumber(null);
    void refreshSelectedWorld(selectedSlug).catch((error: Error) =>
      setLoadError(error.message),
    );
    void api
      .getCurrentChapterJob(selectedSlug)
      .then((job) => {
        if (job && selectedSlugRef.current === selectedSlug) {
          setActiveJob(
            (current) =>
              current ?? {
                slug: selectedSlug,
                jobId: job.job_id,
                label: "Chapter generation",
              },
          );
        }
      })
      .catch((error: Error) => pushToast(error.message, "error"));
  }, [selectedSlug]);

  useEffect(() => {
    const key = `${selectedSlug}:${selectedChapterNumber}`;
    if (
      !selectedSlug ||
      worldDetail?.config.slug !== selectedSlug ||
      !selectedChapter ||
      chapterContent[key]
    ) {
      return;
    }
    void api
      .getChapterContent(selectedSlug, selectedChapter.number)
      .then((response) => {
        setChapterContent((current) => ({
          ...current,
          [key]: response.content,
        }));
      })
      .catch((error: Error) => pushToast(error.message, "error"));
  }, [
    chapterContent,
    pushToast,
    selectedChapter,
    selectedChapterNumber,
    selectedSlug,
    worldDetail?.config.slug,
  ]);

  async function loadWorlds() {
    const list = await api.listWorlds();
    setWorlds(list);
    const currentWorld =
      list.find((world) => world.is_current) ?? list[0] ?? null;
    setSelectedSlug((previous) => previous ?? currentWorld?.slug ?? null);
  }

  async function loadSettings() {
    const response = await api.getSettings();
    setSettings(response);
  }

  async function refreshSelectedWorld(
    slug: string | null,
    preferredChapter?: number,
  ) {
    if (!slug) {
      return;
    }
    const detail = await api.getWorld(slug);
    if (selectedSlugRef.current !== slug) {
      await loadWorlds();
      return;
    }
    startTransition(() => {
      setWorldDetail(detail);
      setSelectedChapterNumber(
        preferredChapter ??
          detail.chapters[detail.chapters.length - 1]?.number ??
          detail.chapters[0]?.number ??
          null,
      );
    });
    void loadWorlds().catch((error: Error) =>
      pushToast(error.message, "error"),
    );
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
      setLibraryOpen(false);
      await loadWorlds();
    } catch (error) {
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function handleRandomWorld() {
    setBusy(true);
    try {
      const generated = await api.getRandomWorld();
      setRandomWorld(generated);
      setLibraryOpen(false);
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
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function handleReadingChange(input: SettingsUpdateRequest) {
    const previous = settings;
    if (!previous) return;
    setSettings({ ...previous, ...input });
    try {
      await api.updateSettings(input);
    } catch (error) {
      setSettings(previous);
      throw error;
    }
  }

  async function handleClearKeys() {
    setBusy(true);
    try {
      await api.clearKeys();
      pushToast("API keys cleared.", "success");
      await loadSettings();
    } catch (error) {
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function handleSelectWorld(slug: string) {
    if (slug === selectedSlug) {
      setLibraryOpen(false);
      return;
    }
    try {
      await api.setCurrentWorld(slug);
      setSelectedSlug(slug);
      setLibraryOpen(false);
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

  async function launchJob(
    label: string,
    run: () => Promise<{ job_id: string }>,
  ) {
    if (!selectedSlug || activeJob || busy) {
      return;
    }
    setBusy(true);
    setGenerationError("");
    try {
      const response = await run();
      setActiveJob({ slug: selectedSlug, jobId: response.job_id, label });
    } catch (error) {
      setGenerationError((error as Error).message);
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

  const latestChapter = worldDetail?.chapters[worldDetail.chapters.length - 1];
  const historical =
    !!selectedChapter && selectedChapter.number !== latestChapter?.number;
  const writing = busy || !!activeJob;
  const writingElsewhere = !!activeJob && activeJob.slug !== selectedSlug;
  const progressTitle = writingElsewhere
    ? `Writing in ${worlds.find((world) => world.slug === activeJob.slug)?.title ?? activeJob.slug}`
    : (activeJob?.label ?? "Writing the next chapter");
  const chooseChapter = (number: number) => {
    setSelectedChapterNumber(number);
    setChaptersOpen(false);
    window.scrollTo({ top: 0, behavior: "instant" });
  };
  const timeline = (
    <ChapterTimeline
      chapters={worldDetail?.chapters ?? []}
      selectedChapterNumber={selectedChapterNumber}
      onSelect={chooseChapter}
    />
  );
  const beginWorld = () => {
    setLibraryOpen(false);
    setRandomWorld(null);
    setEditorState("create");
  };
  const chapterActions = selectedChapter && (
    <details
      className="chapter-menu"
      key={`${selectedSlug}:${selectedChapter.number}`}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.preventDefault();
          event.currentTarget.removeAttribute("open");
          event.currentTarget.querySelector("summary")?.focus();
        }
      }}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget))
          event.currentTarget.removeAttribute("open");
      }}
    >
      <summary aria-label="Chapter actions" title="Chapter actions">
        •••
      </summary>
      <div className="chapter-menu__content">
        <p>
          {selectedChapter.ai_summary ??
            selectedChapter.summary ??
            "Chapter details"}
        </p>
        <button
          type="button"
          disabled={writing || historical}
          onClick={(event) => {
            event.currentTarget.closest("details")?.removeAttribute("open");
            void launchJob("Rewriting chapter", () =>
              api.rerollChapter(
                selectedSlug!,
                selectedChapter.number,
                generationRequest,
              ),
            );
          }}
        >
          Rewrite chapter
        </button>
        <button
          type="button"
          disabled={writing || settings?.image_provider === "none"}
          onClick={(event) => {
            event.currentTarget.closest("details")?.removeAttribute("open");
            void handleRegenerateImage(selectedChapter.number);
          }}
        >
          Regenerate illustration
        </button>
        <button
          type="button"
          className="danger-text"
          disabled={writing || historical}
          onClick={() =>
            setConfirmation({
              kind: "chapter",
              chapterNumber: selectedChapter.number,
            })
          }
        >
          Delete chapter
        </button>
        {historical && (
          <small>Only the latest chapter can be rewritten or deleted.</small>
        )}
        <small>
          {[selectedChapter.text_model_used, selectedChapter.image_model_used]
            .filter(Boolean)
            .join(" · ")}
        </small>
      </div>
    </details>
  );

  const worldDetails = (
    <details className="world-details">
      <summary>
        World details <span aria-hidden="true">⌄</span>
      </summary>
      <p>{worldDetail?.config.theme ?? "Create a world to begin."}</p>
      {worldDetail?.config.memory && <p>{worldDetail.config.memory}</p>}
      <div className="world-details__actions">
        <button
          type="button"
          className="text-button"
          disabled={!worldDetail || writing}
          onClick={() => setEditorState("edit")}
        >
          Edit world
        </button>
        <button
          type="button"
          className="text-button danger-text"
          disabled={!worldDetail || writing}
          onClick={() => setConfirmation({ kind: "world" })}
        >
          Delete world
        </button>
      </div>
    </details>
  );

  if (settingsOpen)
    return (
      <>
        <SettingsPanel
          settings={settings}
          busy={busy}
          onSave={handleSaveSettings}
          onClearKeys={handleClearKeys}
          onClose={() => setSettingsOpen(false)}
          onAppearance={() => {
            setSettingsOpen(false);
            setAppearanceOpen(true);
            setLoreOpen(false);
          }}
        />
        <ToastShelf toasts={toasts} onDismiss={dismissToast} />
      </>
    );
  if (editorState && settings)
    return (
      <>
        <WorldEditor
          mode={editorState}
          world={worldDetail}
          randomWorld={randomWorld}
          settings={settings}
          busy={busy}
          onCancel={() => {
            setEditorState(null);
            setRandomWorld(null);
            setLibraryOpen(true);
          }}
          onSubmit={handleWorldSubmit}
        />
        <ToastShelf toasts={toasts} onDismiss={dismissToast} />
      </>
    );
  if (libraryOpen)
    return (
      <>
        <Workspace wide title="Library" onBack={() => setLibraryOpen(false)}>
          <WorldList
            worlds={worlds}
            selectedSlug={selectedSlug}
            onSelect={(slug) => void handleSelectWorld(slug)}
            onCreate={beginWorld}
            onRandom={() => void handleRandomWorld()}
            busy={busy}
          />
        </Workspace>
        <ToastShelf toasts={toasts} onDismiss={dismissToast} />
      </>
    );
  if (loadError || initializing || (selectedSlug && !worldDetail))
    return (
      <Workspace
        title={loadError ? "Unable to load" : "Loading library…"}
        onBack={() => setLibraryOpen(true)}
        backLabel="Open library"
      >
        {loadError ? (
          <div className="field-stack">
            <p className="inline-error" role="alert">
              {loadError}
            </p>
            <button
              type="button"
              className="button"
              onClick={() => {
                void initialize();
                if (selectedSlug)
                  void refreshSelectedWorld(selectedSlug).catch(
                    (error: Error) => setLoadError(error.message),
                  );
              }}
            >
              Try again
            </button>
          </div>
        ) : (
          <p role="status">Loading your worlds and reading preferences.</p>
        )}
      </Workspace>
    );
  return (
    <div className="app-shell">
      <a className="skip-link" href="#story">
        Skip to story
      </a>
      <header className="topbar">
        <button
          className="icon-button mobile-chapters"
          type="button"
          aria-label="Open chapters"
          onClick={() => setChaptersOpen(true)}
        >
          ☰
        </button>
        <button
          type="button"
          className="brand"
          onClick={() => setLibraryOpen(true)}
          aria-label="Living Storyworld library"
        >
          <svg viewBox="0 0 32 32" aria-hidden="true">
            <path d="M3 4v23h26V4M8 3v18l8 6 8-6V3M16 7v20" />
          </svg>
          <span>Living Storyworld</span>
        </button>
        <div className="topbar__actions">
          <button
            type="button"
            className="topbar__link"
            onClick={() => setLibraryOpen(true)}
          >
            ‹ <span>Library</span>
          </button>
          <button
            type="button"
            className="appearance-trigger"
            aria-label="Reading appearance"
            title="Reading appearance"
            aria-expanded={appearanceOpen}
            onClick={() => {
              setAppearanceOpen(!appearanceOpen);
              setLoreOpen(false);
            }}
          >
            Aa
          </button>
          <button
            type="button"
            className="icon-button settings-trigger"
            aria-label="Settings"
            title="Settings"
            onClick={() => setSettingsOpen(true)}
          >
            ⚙
          </button>
        </div>
      </header>

      <div
        className={`reading-layout ${appearanceOpen || loreOpen ? "reading-layout--inspecting" : ""}`}
      >
        <aside className="book-sidebar">
          <div className="book-sidebar__title">
            <h2>{worldDetail?.config.title ?? "No world selected"}</h2>
            <span className="book-rule" />
          </div>
          {timeline}
          {worldDetails}
        </aside>

        <main id="story" tabIndex={-1}>
          <ChapterReader
            chapter={selectedChapter}
            emptyTitle={worldDetail?.config.title}
            fontFamily={settings?.reader_font_family}
            fontSize={settings?.reader_font_size}
            content={
              selectedChapterNumber !== null
                ? (chapterContent[`${selectedSlug}:${selectedChapterNumber}`] ??
                  "")
                : ""
            }
            choicesDisabled={writing}
            historical={historical}
            headerActions={chapterActions}
            onSelectChoice={(choiceId) => void handleSelectChoice(choiceId)}
            footer={
              <div className="reader__footer">
                {historical ? (
                  <button
                    type="button"
                    className="button"
                    onClick={() => chooseChapter(latestChapter!.number)}
                  >
                    Return to latest chapter →
                  </button>
                ) : selectedSlug ? (
                  <>
                    <div className="continue-row">
                      <button
                        type="button"
                        className="button button--continue"
                        disabled={!worldDetail || writing}
                        onClick={() =>
                          void launchJob("Writing the next chapter", () =>
                            api.startChapterGeneration(
                              selectedSlug,
                              generationRequest,
                            ),
                          )
                        }
                      >
                        {writingElsewhere
                          ? "Writing elsewhere..."
                          : activeJob
                            ? "Writing..."
                            : busy
                              ? "Working..."
                              : selectedChapter
                                ? "Continue story"
                                : "Begin story"}
                        <span aria-hidden="true">→</span>
                      </button>
                      <details className="generation-options">
                        <summary>Story options</summary>
                        <div className="generation-options__fields">
                          <label>
                            Chapter length
                            <select
                              value={generationRequest.chapter_length}
                              disabled={writing}
                              onChange={(event) =>
                                setGenerationRequest((current) => ({
                                  ...current,
                                  chapter_length: event.target
                                    .value as GenerationRequest["chapter_length"],
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
                              checked={
                                settings?.image_provider !== "none" &&
                                !generationRequest.no_images
                              }
                              disabled={
                                writing || settings?.image_provider === "none"
                              }
                              onChange={(event) =>
                                setGenerationRequest((current) => ({
                                  ...current,
                                  no_images: !event.target.checked,
                                }))
                              }
                            />
                            Include an illustration
                          </label>
                        </div>
                      </details>
                    </div>
                    {!generationRequest.no_images &&
                      settings &&
                      !["none", "comfyui"].includes(settings.image_provider) &&
                      !hasProviderKey(settings, settings.image_provider) && (
                        <p className="setup-notice">
                          Illustrations need an API key.{" "}
                          <button
                            type="button"
                            className="text-button"
                            onClick={() => setSettingsOpen(true)}
                          >
                            Set up your provider
                          </button>{" "}
                          or turn illustrations off in Story options.
                        </p>
                      )}
                  </>
                ) : (
                  <button type="button" className="button" onClick={beginWorld}>
                    Create world
                  </button>
                )}
                {generationError && (
                  <div className="inline-error" role="alert">
                    {generationError}
                    <br />
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => setSettingsOpen(true)}
                    >
                      Review generation settings
                    </button>
                  </div>
                )}
                {activeJob && (
                  <ProgressCard
                    title={progressTitle}
                    busy
                    progress={streamState.progress}
                    error={streamState.error}
                  />
                )}
              </div>
            }
          />
        </main>
        <aside className="lore-rail">
          <button
            type="button"
            aria-expanded={loreOpen}
            onClick={() => {
              setLoreOpen(!loreOpen);
              setAppearanceOpen(false);
            }}
            disabled={!worldDetail}
            aria-label="Open lore"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 5C8 2 3 3 3 3v16s5-1 9 2c4-3 9-2 9-2V3s-5-1-9 2Zm0 0v16" />
            </svg>
            <span>Lore</span>
            <span aria-hidden="true">→</span>
          </button>
        </aside>
        {appearanceOpen && (
          <Inspector
            title="Reading appearance"
            onClose={() => setAppearanceOpen(false)}
          >
            <AppearancePanel
              theme={theme}
              onThemeChange={setTheme}
              settings={settings}
              onReaderChange={handleReadingChange}
            />
          </Inspector>
        )}
        {loreOpen && worldDetail && (
          <Inspector title="Lore" onClose={() => setLoreOpen(false)}>
            <div className="lore-content">
              <p className="lore-intro">{worldDetail.config.theme}</p>
              {(
                [
                  ["Characters", worldDetail.state.characters],
                  ["Places", worldDetail.state.locations],
                ] as const
              ).map(([title, entries]) => (
                <section key={title}>
                  <h3 className="eyebrow">{title}</h3>
                  {Object.values(entries).length ? (
                    Object.values(entries).map((entry) => (
                      <article key={entry.id}>
                        <h4>{entry.name}</h4>
                        {entry.description && <p>{entry.description}</p>}
                      </article>
                    ))
                  ) : (
                    <p className="muted">No {title.toLowerCase()} yet.</p>
                  )}
                </section>
              ))}
              {worldDetail.config.memory && (
                <section>
                  <h3 className="eyebrow">World memory</h3>
                  <p>{worldDetail.config.memory}</p>
                </section>
              )}
            </div>
          </Inspector>
        )}
      </div>

      {chaptersOpen && (
        <Dialog
          title={worldDetail?.config.title ?? "Chapters"}
          onClose={() => setChaptersOpen(false)}
        >
          {timeline}
          {worldDetails}
        </Dialog>
      )}
      {confirmation && (
        <Dialog
          title={
            confirmation.kind === "world"
              ? "Delete this world?"
              : "Delete this chapter?"
          }
          onClose={() => setConfirmation(null)}
        >
          <p>
            {confirmation.kind === "world"
              ? `This permanently removes "${worldDetail?.config.title}" and its chapters.`
              : "This removes the latest chapter and restores the previous story context."}
          </p>
          <div className="editor__actions">
            <button
              type="button"
              className="button button--ghost"
              onClick={() => setConfirmation(null)}
            >
              Keep it
            </button>
            <button
              type="button"
              className="button button--danger"
              onClick={() => {
                if (confirmation.kind === "world") void handleDeleteWorld();
                else void handleDeleteChapter(confirmation.chapterNumber!);
                setConfirmation(null);
              }}
            >
              Delete {confirmation.kind}
            </button>
          </div>
        </Dialog>
      )}
      <ToastShelf toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
