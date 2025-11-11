# Living Storyworld

A storybook created from your imagination, with infinite possibilities. Make decisions and steer the story, or sit back and enjoy a relaxing tale! Create evolving fictional worlds where each chapter builds on the last. Living Storyworld combines multiple LLM providers with AI image generation to produce coherent, ongoing narratives with custom scene illustrations. 

This fun little project was inspired by text adventures, with a modern twist of simplified decision-making and creativity. I wanted to make something that could be both less and more than traditional text adventures, without the (powerful) burden that a service like NovelAI puts on you to be creative. 

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

Pre-built executables are available on the [Releases](https://github.com/jonmartin721/living-storyworld/releases) page. Alternatively, run from source:

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

1. **Setup Wizard** — On first launch, a guided setup wizard helps you configure API keys and select providers (free options available)
2. **Create a World** — Use "New World" to design your own, or try "Random World" for instant generation with pre-filled lore
3. **Generate Chapters** — Click "Generate Next Chapter" to continue the story with real-time progress indicators
4. **Make Choices** — When presented with story choices, select one and lock it in to influence the narrative direction

The web interface provides full world management, chapter generation with live progress, and comprehensive settings. Access the setup wizard anytime via Console → "Start Setup Wizard".

---

## Visual Styles

- **storybook-ink** — Ink and wash illustration
- **pixel-rpg** — 16-bit SNES-style pixel art
- **lowpoly-iso** — Low-poly isometric diorama
- **watercolor-dream** — Soft watercolor painting
- **noir-sketch** — High-contrast ink sketch
- **art-nouveau** — Art Nouveau poster illustration
- **comic-book** — Classic American comic book style
- **oil-painting** — Classical oil painting (Old Masters)

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

- **Gemini** — 2.5 Flash model with generous free tier ([get key](https://aistudio.google.com/apikey))
- **Pollinations** — Free image generation (no key required)

Using Gemini 2.5 Flash and Pollinations, everything is completely free. The setup wizard automatically recommends this configuration.

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
- World art shown for each world behind chapters.
- Better visual transitions between chapters.
- Themed reading mode for different worlds, or in Settings.
- How can we end stories naturally or let readers do it in a way that isn't limiting or too abrupt?

I'd love to see new improvements, feel free to suggest and open a PR! Contributions are very welcome.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

Built with FastAPI, multiple AI provider integrations, and modern web technologies.
