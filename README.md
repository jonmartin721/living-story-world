# Living Storyworld

> A storybook created from your imagination, with infinite possibilities. Make decisions and steer the story, or sit back and enjoy a relaxing tale.

Create evolving fictional worlds where each chapter builds on the last. Living Storyworld combines multiple LLM providers with AI image generation to produce coherent, ongoing narratives with custom scene illustrations. 

---

## Features

- **Persistent World State** — Characters, locations, and narrative continuity maintained across chapters
- **Multi-Provider Support** — Choose from OpenAI, Groq, Together AI, HuggingFace, OpenRouter for text; Replicate, Fal.ai, Pollinations for images. Free options available (rate-limited or requiring free API keys)
- **Visual Styles** — Multiple art direction presets (storybook-ink, pixel-rpg, lowpoly-iso, watercolor-dream, and more)
- **Narrative Presets** — 12+ genre/tone templates from cozy-adventure to cyberpunk-noir
- **Modern Web Interface** — Full-featured GUI with real-time progress and chapter management
- **Smart Caching** — Avoids duplicate API calls by hashing image prompts
- **Random World Creation** — Fully randomized world with lore and direction prefilled
---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/jonmartin721/living-storyworld.git
cd living-storyworld

# Set up virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Launch the Web Interface

```bash
python3 -m living_storyworld.cli web
```

The web app will open automatically at `http://localhost:8001`.

### Get Started

1. **Configure API Keys** — Click Settings to add your API keys. The app will guide you through provider options including free tiers
2. **Create a World** — Use the "New World" button or try "Random World" for instant generation
3. **Generate Chapters** — Select your world and click "Generate Chapter" to continue the story with real-time progress
4. **Customize Settings** — Adjust narrative presets, visual styles, and memory fields for each world

The web interface provides:
- Multi-world management and navigation
- Real-time chapter generation with progress streaming
- Illustrated chapter viewer in card layout
- Image regeneration on demand
- World configuration and API settings

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
