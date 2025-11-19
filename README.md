# Living Storyworld

[![Release](https://img.shields.io/github/v/release/jonmartin721/living-story-world?style=flat-square)](https://github.com/jonmartin721/living-story-world/releases)
[![Tests](https://img.shields.io/github/actions/workflow/status/jonmartin721/living-story-world/test.yml?branch=main&label=tests&style=flat-square)](https://github.com/jonmartin721/living-story-world/actions)
[![codecov](https://codecov.io/gh/jonmartin721/living-story-world/branch/main/graph/badge.svg)](https://codecov.io/gh/jonmartin721/living-story-world)
[![Python](https://img.shields.io/badge/dynamic/toml?url=https://raw.githubusercontent.com/jonmartin721/living-story-world/main/pyproject.toml&query=project.requires-python&label=python&style=flat-square&color=blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/jonmartin721/living-story-world?style=flat-square)](LICENSE)
[![Code style](https://img.shields.io/badge/code%20style-ruff-black?style=flat-square)](https://github.com/astral-sh/ruff)

>NovelAI but chill

An AI storytelling engine that writes illustrated chapters while maintaining memory. Characters remember past events, locations build history, and your choices actually matter going forward.

I built this to explore whether AI could handle long-form narrative without turning into word salad by Chapter 3. The interesting engineering problems: keeping a knowledge graph consistent across generations, orchestrating multiple AI providers (text + image) with clean abstractions, and streaming progress in real-time without blocking the UI.

**Built with:** Python, FastAPI, Server-Sent Events, NovelAI-style memory system

---

## Why I Built This

Most AI story generators are goldfish—write one scene, forget everything, write another. I wanted to see if we could maintain a persistent narrative universe where entities (characters, locations, plot threads) survive across generations instead of getting amnesia every chapter.

The project started as an experiment in combining modern AI models with classic text adventure mechanics. Could we have the narrative depth of a novel without requiring the creative effort that services like NovelAI demand from users?

Also, I wanted to play with provider-agnostic patterns to avoid vendor lock-in. Being able to A/B test OpenAI vs Groq vs Together AI side-by-side is useful when everyone's releasing new models every week.

---

## Quick Start

I highly recommend downloading pre-built executables from the [Releases](https://github.com/jonmartin721/living-storyworld/releases).

If you'd rather build from source or contribute:

```bash
git clone https://github.com/jonmartin721/living-storyworld.git
cd living-storyworld
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the web interface
python3 -m living_storyworld.cli web
```

The web app will open at `http://localhost:8001`. First-time setup will walk you through configuring API keys—I recommend using Gemini 2.5 Flash (free tier) plus Pollinations for images to get started without costs.

![Setup wizard for initial configuration](screenshots/setup-wizard.png)

Once you're in, create a new world by clicking "New" (or use the random generator) and start generating chapters. You'll get choices at key points to steer the story direction.

---

## Interface & Workflow

### 1. First-Time Setup

When you first launch Living Storyworld, you'll see a setup wizard that guides you through configuring your API keys. You'll need at least one text provider (Gemini's free tier is solid) and optionally an image provider (Pollinations is free and requires no key).

![Setup wizard for initial configuration](screenshots/setup-wizard.png)

You can always return to settings later to add more providers or change your defaults:

![API keys configuration](screenshots/api-keys-settings.png)

### 2. World Management

The main interface shows all your story worlds in one place. Each world card displays recent chapters with their illustrations, making it easy to jump back into any story.

![Main interface showing world management](screenshots/main-page.png)

### 3. Creating a New World

Click "New World" to start a fresh story. You can manually set the title, theme, genre, and art style, or use the random generator to create unique combinations instantly.

![New world creation dialog](screenshots/new-world-dialog.png)

### 4. Reading & Making Choices

When reading chapters, you'll get a clean view optimized for enjoying your generated story. The interface shows the chapter illustration, narrative text, and your choices.

![Clean reading interface](screenshots/reading-mode.png)

At key moments in the story, you'll be presented with choices that influence how the narrative unfolds. Select an option to guide the direction of the next chapter.

These are PERMANENT! Choose carefully.

![Interactive choice moments](screenshots/make-choices.png)

---

## Features

- **Persistent Memory** - Stories remember characters and locations across chapters (entity graph tracks continuity)
- **Multi-Provider Support** - Swap between OpenAI, Groq, Together AI, HuggingFace, OpenRouter, Gemini without touching code
- **Visual Styles** - 8 illustration styles from storybook ink to pixel art to oil paintings
- **Genre Presets** - 12 narrative presets tuned for different story types (fantasy, mystery, sci-fi, horror, etc.)
- **Real-Time Streaming** - Progress updates via Server-Sent Events (no polling, feels snappy)
- **Choice System** - Make decisions that affect future chapters (permanent branching)
- **Image Caching** - Avoids redundant API calls by hashing prompts
- **Random Worlds** - Generator creates unique world combinations with pre-built lore
- **Web + TUI + CLI** - Three interfaces (browser, terminal UI, command-line)

---

## How It Works

### Provider Swapping

One design goal: don't get locked into a single AI provider. OpenAI might be expensive, Groq might be fast, Together AI might have a better model next month.

The solution is abstract base classes that let you swap providers without touching generation logic:

```python
class TextProvider(ABC):
    """All text providers implement this interface"""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text. Each provider handles retries differently."""
        ...

    @abstractmethod
    def validate_model(self, model: str) -> bool:
        """Check if a model name is valid for this provider."""
        ...

    @abstractmethod
    def estimate_cost(self, tokens: int) -> float:
        """Ballpark cost estimate—useful for comparing providers."""
        ...
```

Now I can A/B test providers side-by-side or switch when one goes down. Currently supports: OpenAI, Groq, Together AI, HuggingFace, OpenRouter, Gemini.

Same pattern for image providers (Replicate, HuggingFace, Pollinations, Fal.ai).

### State Management & Entity Graph

World state is stored as JSON files with dataclass serialization. Each world tracks:

```
worlds/<slug>/
├── config.json          # WorldConfig (immutable: title, theme, models, style)
├── world.json           # WorldState (mutable: characters, locations, chapters)
├── chapters/            # Generated markdown content
├── media/
│   ├── scenes/          # Scene illustrations (PNG)
│   └── index.json       # Media metadata registry
└── web/
    └── index.html       # Static HTML export (via build command)
```

Entity extraction happens automatically via structured JSON in chapter metadata:

```html
<!-- {
  "scene_prompt": "...",
  "characters_in_scene": ["char-001"],
  "new_characters": [{"id": "char-002", "name": "...", "description": "..."}],
  "new_locations": [...],
  "summary": "..."
} -->
```

New entities get registered into `WorldState` during generation, building a persistent knowledge graph. This is how the system remembers that "Lyra" is a character and "Thornhaven" is a location across chapters.

### Real-Time Progress Streaming

Chapter generation uses Server-Sent Events for live progress updates without polling:

```javascript
// Frontend code - real-time updates without refreshing
const eventSource = new EventSource('/api/generate/stream');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'progress') {
    updateProgressBar(data.percent);  // Text generation in progress
  } else if (data.type === 'chapter_complete') {
    renderChapter(data.content);      // Chapter ready, now generating image
  } else if (data.type === 'image_complete') {
    displayScene(data.image_url);     // All done!
  }
};
```

Backend emits structured events during the async generation pipeline. Feels responsive compared to long-polling.

### Memory System (NovelAI-Inspired)

Context is built via layered injection:

1. **Memory** (always included) - World lore, background, key facts
2. **Author's Note** (inserted at strategic point) - Style guidance, tone directives
3. **World Instructions** - Custom world-specific rules
4. **Preset System Directive** - Genre-specific generation guidance
5. **Chapter History** - Recent chapter summaries for continuity
6. **Entity Context** - Active characters and locations in scene

This gives you control over different "levels" of context like NovelAI's lorebooks, but simpler.

---

## Design Decisions

### Why Server-Sent Events instead of WebSockets?

Simpler server implementation and automatic reconnect handling. Generation is unidirectional (server → client), so WebSockets would be overkill. SSE gives you real-time updates without the complexity of bidirectional channels.

### Why dataclasses instead of SQLAlchemy?

JSON persistence keeps the project dependency-light and makes the world files human-readable. For a narrative tool, being able to `cat world.json` and see your entity graph is genuinely useful for debugging. Also avoids the overhead of an ORM for what's essentially a document store.

### Why FastAPI + Textual + PyWebView?

I wanted to build three interfaces (CLI, TUI, web) from one backend. FastAPI's async support made SSE easy, Textual handles the terminal UI, and PyWebView wraps the web interface for a "desktop app" feel without Electron bloat.

### Why multiple providers instead of just OpenAI?

Vendor lock-in sucks. Also, different providers have different strengths—Groq is blazingly fast, Together AI has open models, Gemini has a generous free tier. Being able to compare outputs side-by-side is valuable.

---

## Visual Styles

These affect how generated images look to a very high degree.

Available illustration styles:
- `storybook-ink` - Ink and wash illustrations with subtle color accents
- `pixel-rpg` - 16-bit pixel art style (classic JRPG aesthetic)
- `lowpoly-iso` - Isometric low-poly scenes
- `watercolor-dream` - Soft watercolor paintings with bleeding edges
- `noir-sketch` - High contrast ink drawings (black and white)
- `art-nouveau` - Art Nouveau poster style with flowing lines
- `comic-book` - Classic comic book look with halftone dots
- `oil-painting` - Classical oil paintings with visible brushstrokes

Each style pack includes base prompt, negative prompt, and style modifiers for consistent output.

---

## Narrative Presets

These affect pacing, tone, maturity level, and how the story is told. Large effect on narrative output!

Story genres:
- `cozy-adventure` - Character-driven stories with gentle stakes (think Stardew Valley)
- `epic-fantasy` - High fantasy with kingdoms, magic, and large-scale conflicts
- `solarpunk-explorer` - Hopeful eco-futurism and community building
- `whimsical-fairy-tale` - Modern fairy tales with charm and moral elements
- `noir-mystery` - Urban crime stories with cynical detectives
- `gothic-horror` - Atmospheric horror with family secrets and dread
- `cosmic-horror` - Existential stories about incomprehensible forces (Lovecraftian)
- `cyberpunk-noir` - Near-future tech noir with corporate intrigue
- `slice-of-life` - Everyday moments and character relationships
- `historical-intrigue` - Period stories with political maneuvering
- `post-apocalyptic` - Survival and rebuilding after societal collapse
- `space-opera` - Grand interstellar adventures

Each preset specifies temperature, system instructions, pacing, and content maturity level.

---

## CLI Reference

```bash
# World initialization
python3 -m living_storyworld.cli init \
  --title "World Name" \
  --theme "Theme description" \
  --style storybook-ink \
  --preset epic-fantasy

# Chapter generation
python3 -m living_storyworld.cli chapter \
  --world world-slug \
  --preset cozy-adventure

# Scene image generation
python3 -m living_storyworld.cli image scene \
  --world world-slug \
  --chapter 1

# Static HTML build (shareable export)
python3 -m living_storyworld.cli build --world world-slug

# Configuration management
python3 -m living_storyworld.cli setup

# Launch web interface
python3 -m living_storyworld.cli web --no-browser --port 8001

# Interactive TUI (terminal interface)
python3 -m living_storyworld.cli play
```

---

## API Keys & Configuration

I recommend using Gemini 2.5 Flash (free tier) with Pollinations for images to get started without costs. Get a Gemini key here: https://aistudio.google.com/api-keys

The setup wizard will walk you through configuration. You'll need at least one text provider API key—image providers like Pollinations work without keys.

API keys are stored in `~/.config/living-storyworld/settings.json` with 600 permissions (secure, local-only).

### Security Notes

This runs on localhost only by default (`127.0.0.1`). Don't expose it to the internet—there's no authentication, no rate limiting, and I haven't done a real security audit.

Some basic protections in place:
- Slug validation prevents path traversal attacks (`../../../etc/passwd` won't work)
- Image downloads have size limits (10MB) and timeouts (30s)
- HTML output is escaped to prevent XSS
- CORS is locked to localhost origins
- API keys stored with restricted file permissions (600)

Good enough for a local tool, not production-ready.

---

## Known Limitations & Future Ideas

### Current Limitations

- No multi-threaded generation (one chapter at a time per world)
- Entity extraction relies on LLM structured output—can be flaky with smaller models
- Image generation is slow (30-60s per scene with Flux models)
- No built-in story branching visualization (choice tree)
- Choice system doesn't support "go back" (permanent decisions)

### Future Ideas

- WebSocket support for collaborative story editing
- RAG-style long-term memory (vector DB for searching chapter history)
- Character portrait generation with consistent face models (LoRA fine-tuning?)
- Export to EPUB/PDF with embedded images
- Story branching visualization (interactive choice tree)
- Multi-user worlds (shared narrative universe)

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines, code style requirements, and pull request process.

**Found a bug?** Please [open an issue](https://github.com/jonmartin721/living-story-world/issues) on GitHub.

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
