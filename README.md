# Living Storyworld

> A persistent narrative universe generator that creates illustrated story chapters using AI-powered text and image generation.

Create evolving fictional worlds where each chapter builds on the last. Living Storyworld combines multiple LLM providers with AI image generation to produce coherent, ongoing narratives with custom scene illustrations—all from a simple CLI or modern web interface.

---

## Features

- **Persistent World State** — Characters, locations, and narrative continuity maintained across chapters
- **Multi-Provider Support** — Choose from OpenAI, Groq, Together AI, HuggingFace, OpenRouter for text; Replicate, Fal.ai, Pollinations for images
- **Visual Styles** — Multiple art direction presets (storybook-ink, pixel-rpg, lowpoly-iso, watercolor-dream, and more)
- **Narrative Presets** — 12+ genre/tone templates from cozy-adventure to cyberpunk-noir
- **Web Interface** — Modern GUI with real-time generation progress and chapter management
- **Smart Caching** — Avoids duplicate API calls by hashing image prompts
- **Flexible Output** — Generate static HTML viewers or use the interactive web app

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/living-storyworld.git
cd living-storyworld

# Set up virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Configure your API keys using the setup wizard:

```bash
python3 -m living_storyworld.cli setup
```

The wizard securely stores your keys in `~/.config/living-storyworld/settings.json` with `600` permissions.

<details>
<summary>Alternative: Environment Variables</summary>

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your keys
export GROQ_API_KEY=gsk_...
export REPLICATE_API_TOKEN=r8_...
```
</details>

### Create Your First World

```bash
python3 -m living_storyworld.cli init \
  --title "The Flooded Stacks" \
  --theme "A city of drowned archives where knowledge flows like water" \
  --style storybook-ink \
  --preset cozy-adventure
```

### Generate a Chapter

```bash
python3 -m living_storyworld.cli chapter \
  --world the-flooded-stacks \
  --focus "The Archivist discovers a sealed section"
```

### View Your Story

**Option 1: Web Interface (Recommended)**

```bash
python3 -m living_storyworld.cli web
```

Visit `http://localhost:8001` for a modern GUI with:
- Browse multiple worlds
- Generate chapters with real-time progress
- View illustrated chapters in card layout
- Regenerate images on demand

**Option 2: Static HTML Viewer**

```bash
python3 -m living_storyworld.cli build --world the-flooded-stacks
# Open worlds/the-flooded-stacks/web/index.html in your browser
```

---

## Usage

### World Management

| Command | Description |
|---------|-------------|
| `init` | Create a new narrative world |
| `chapter` | Generate a new chapter with scene illustration |
| `image scene` | Regenerate a specific chapter's scene image |
| `build` | Build static HTML viewer for a world |
| `web` | Launch interactive web interface |
| `play` | Interactive terminal UI |

### Available Interfaces

**Web Interface** (Primary)
```bash
python3 -m living_storyworld.cli web [--port 8001] [--no-browser]
```

**Terminal UI**
```bash
python3 -m living_storyworld.cli play
```

**Command Line**
```bash
# Full chapter generation example
python3 -m living_storyworld.cli chapter \
  --world my-world \
  --preset noir-mystery \
  --focus "Detective follows a lead to the docks" \
  --length 2000
```

---

## Visual Styles

Choose from multiple art direction presets for scene illustrations:

| Style | Description |
|-------|-------------|
| `storybook-ink` | Ink and wash illustration with muted palette |
| `pixel-rpg` | 16-bit SNES-style pixel art |
| `lowpoly-iso` | Low-poly isometric diorama |
| `watercolor-dream` | Soft watercolor with dreamy atmosphere |
| `noir-sketch` | High-contrast ink sketch, noir aesthetic |
| `vaporwave-glitch` | Vaporwave aesthetic with digital artifacts |

Configure in world settings or via `worlds/<slug>/config.json`

---

## Narrative Presets

12 genre and tone templates to shape your story:

<table>
<tr>
<td width="50%">

**Adventure & Wonder**
- `cozy-adventure` — Wholesome exploration, gentle stakes
- `epic-fantasy` — Grand vistas, mythic stakes
- `solarpunk-explorer` — Hopepunk tone, inventive systems
- `whimsical-fairy-tale` — Playful enchantment

</td>
<td width="50%">

**Dark & Mysterious**
- `noir-mystery` — Moody, metaphor-rich
- `gothic-horror` — Atmospheric dread
- `cosmic-horror` — Existential terror
- `cyberpunk-noir` — High-tech low-life

</td>
</tr>
<tr>
<td>

**Drama & Character**
- `slice-of-life` — Quiet moments, intimacy
- `historical-intrigue` — Period authenticity

</td>
<td>

**Survival & Conflict**
- `post-apocalyptic` — Harsh beauty, rebuilding
- `space-opera` — Galactic scale, political intrigue

</td>
</tr>
</table>

---

## Architecture

### Project Structure

```
living-storyworld/
├── living_storyworld/
│   ├── cli.py              # CLI entry point
│   ├── webapp.py           # FastAPI application
│   ├── generator.py        # Chapter generation orchestrator
│   ├── world.py            # World initialization and state
│   ├── storage.py          # Filesystem abstraction
│   ├── models.py           # Core data models
│   ├── providers/          # Pluggable text/image providers
│   ├── api/                # FastAPI routers
│   └── web/                # Frontend assets
└── worlds/
    └── <slug>/
        ├── config.json     # World configuration
        ├── world.json      # Persistent state
        ├── chapters/       # Generated markdown
        └── media/
            └── scenes/     # Scene illustrations
```

### Provider Architecture

**Text Providers**: OpenAI, Groq, Together AI, HuggingFace, OpenRouter
**Image Providers**: Replicate (Flux), Fal.ai, HuggingFace, Pollinations (free)

All providers implement unified interfaces for easy swapping and cost estimation.

### Data Models

Core dataclasses define world structure:
- `WorldConfig` — Title, theme, model settings, memory system
- `WorldState` — Characters, locations, chapter history, tick count
- `Chapter` — Markdown content, metadata, entity references
- `Character`, `Location`, `Item` — Persistent entities

---

## Advanced Features

### Memory System

Inspired by NovelAI, each world includes three memory fields:

- **Memory** — Always in context (lore, key facts)
- **Author's Note** — Style guidance inserted at strategic points
- **World Instructions** — Custom world-specific directives

Configure via web settings or edit `worlds/<slug>/config.json`

### Entity Tracking

Chapters automatically extract and register:
- New characters with descriptions
- New locations and landmarks
- Scene summaries for continuity

All tracked in `world.json` for persistent world state.

### Image Model Options

| Model | Provider | Quality | Cost | Speed |
|-------|----------|---------|------|-------|
| `flux-dev` | Replicate | High | ~$0.025 | Moderate |
| `flux-schnell` | Replicate | Good | ~$0.003 | Fast |
| `fal-flux` | Fal.ai | High | ~$0.025 | Fast |
| `pollinations` | Pollinations | Moderate | Free | Variable |

---

## API Keys & Pricing

### Recommended Setup (Free Tier)

- **Groq** — Free tier includes generous token limits ([get key](https://console.groq.com/keys))
- **Pollinations** — Free image generation ([no key required](https://pollinations.ai/))

Typical cost per chapter with paid tiers: ~$0.026 USD (text + image)

### Security Notes

- API keys stored locally with `600` permissions
- Web server binds to `127.0.0.1` (localhost only)
- No authentication — do not expose to internet
- Slug validation prevents path traversal attacks
- Image downloads enforce size limits and timeouts

---

## Contributing

Contributions welcome! Areas for expansion:

- Additional style packs and narrative presets
- Character/location portrait generation
- Export formats (EPUB, PDF)
- Advanced world simulation mechanics
- Test coverage improvements

Open an issue or submit a pull request.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) — Modern web framework
- [Groq](https://groq.com/) — Fast LLM inference
- [Replicate](https://replicate.com/) — AI model hosting
- [Flux](https://blackforestlabs.ai/) — State-of-the-art image generation
