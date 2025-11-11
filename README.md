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

- **storybook-ink** — Ink and wash illustration
- **pixel-rpg** — 16-bit SNES-style pixel art
- **lowpoly-iso** — Low-poly isometric diorama
- **watercolor-dream** — Soft watercolor
- **noir-sketch** — High-contrast ink sketch
- **vaporwave-glitch** — Vaporwave with digital artifacts

---

## Narrative Presets

12 genre and tone templates: `cozy-adventure`, `epic-fantasy`, `solarpunk-explorer`, `whimsical-fairy-tale`, `noir-mystery`, `gothic-horror`, `cosmic-horror`, `cyberpunk-noir`, `slice-of-life`, `historical-intrigue`, `post-apocalyptic`, `space-opera`

---

## Architecture

FastAPI backend with pluggable text/image providers. Worlds stored as JSON with generated markdown chapters and PNG scene illustrations. Data models track persistent state across characters, locations, and narrative history.

---

## Advanced Features

Worlds include Memory, Author's Note, and World Instructions fields for narrative control. Chapters automatically extract and track new characters, locations, and scene summaries for continuity.

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

Built with FastAPI, Groq, Replicate, and Flux.
