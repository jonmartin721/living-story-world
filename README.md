# Living Storyworld

A persistent narrative universe you can explore via a simple CLI. It generates chapters (Markdown) using Groq (Llama 3.3) and scene illustrations using Flux via Replicate, then builds a lightweight HTML index for viewing.

## Prerequisites

- **Python 3.8+** (developed with 3.10+)
- **Groq API key** for text generation ([get one here](https://console.groq.com/keys)) - Free tier available!
- **Replicate API token** for image generation ([get one here](https://replicate.com/account/api-tokens))
- **Note**: This tool makes API calls to Groq (text) and Replicate (images). Each chapter generation uses `llama-3.3-70b-versatile` (text, ~$0.001) and `flux-dev` (images, ~$0.025), typical cost per chapter: ~$0.026 USD.

## Quickstart

1. Install dependencies:
   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. Configure your API key (choose one):
   ```bash
   # Option A: Use the setup wizard (recommended - stores key securely with 600 perms)
   python3 -m living_storyworld.cli setup

   # Option B: Create a .env file (convenient for local development)
   cp .env.example .env
   # Edit .env and add your API key: OPENAI_API_KEY=sk-...

   # Option C: Set environment variable
   export OPENAI_API_KEY=sk-...
   ```

3. Create your first world:
   ```bash
   python3 -m living_storyworld.cli init \
     --title "The Flooded Stacks" \
     --theme "A city of drowned archives" \
     --style storybook-ink \
     --image-model flux-dev
   ```

   **Image model options:**
   - `flux-dev` — Higher quality, ~$0.025 per image (default)
   - `flux-schnell` — Faster/cheaper, ~$0.003 per image

4. Generate a chapter:
   ```bash
   python3 -m living_storyworld.cli chapter \
     --world the-flooded-stacks \
     --preset cozy-adventure
   ```

5. View your story:

   **Option A: Web Interface (Recommended)**
   ```bash
   python3 -m living_storyworld.cli web
   ```
   Opens at `http://localhost:8001` with full GUI for browsing, generating, and viewing chapters.

   > **Security Note:** The web server is designed for single-user, localhost-only use. It binds to `127.0.0.1` and has no authentication. Do not expose it to the internet or local network without implementing proper authentication and access controls.

   **Option B: Static HTML viewer**
   ```bash
   python3 -m living_storyworld.cli build --world the-flooded-stacks
   # Then open worlds/the-flooded-stacks/web/index.html in your browser
   ```

## Usage

- Initialize a world:
  - `python3 -m living_storyworld.cli init --title "The Flooded Stacks" --theme "A city of drowned archives" --style storybook-ink --slug flooded-stacks`
- Generate a chapter (with scene image):
  - `python3 -m living_storyworld.cli chapter --world flooded-stacks --preset cozy-adventure --focus "The Archivist investigates a sealed aisle"`
- Generate or re-generate a scene image explicitly:
  - `python3 -m living_storyworld.cli image scene --world flooded-stacks --chapter 1`
- Build a simple web index:
  - `python3 -m living_storyworld.cli build --world flooded-stacks`
  - Open `worlds/flooded-stacks/web/index.html`

## Guided UX

- **Web Interface** (Recommended):
  ```bash
  python3 -m living_storyworld.cli web
  ```
  Modern web-based GUI with:
  - Browse and manage multiple worlds
  - Generate chapters with real-time progress
  - View chapters with scene images in card layout
  - Regenerate images on demand
  - Runs locally at `http://localhost:8001`

- Setup wizard (saves API key locally with 600 perms):
  - `python3 -m living_storyworld.cli setup --style storybook-ink --preset cozy-adventure`

- Interactive TUI (Terminal UI):
  - `python3 -m living_storyworld.cli play`
  - Colorful terminal interface with buttons to generate chapters and build the viewer.

## Style Packs

Visual art styles for scene illustrations:

- `storybook-ink`: Storybook ink and wash; muted palette, cozy, illustrative.
- `pixel-rpg`: 16-bit SNES pixel art; crisp sprites; nostalgic.
- `lowpoly-iso`: Low-poly isometric diorama; clean and stylized.

## Narrative Presets

Story tone and pacing options (use with `--preset` flag):

- `cozy-adventure`: Wholesome explorations, wonder, gentle stakes, warm tone. (default)
- `noir-mystery`: Moody, wry, metaphor-rich, moral gray zones.
- `epic-fantasy`: Grand vistas, mythic stakes, lyrical cadence.
- `solarpunk-explorer`: Inventive systems, hopepunk tone, practical wonder.
- `gothic-horror`: Atmospheric dread, psychological tension, haunting beauty.
- `space-opera`: Galactic scale, diverse cultures, political intrigue among the stars.
- `slice-of-life`: Quiet moments, everyday magic, character-focused intimacy.
- `cosmic-horror`: Existential dread, incomprehensible forces, sanity fraying.
- `cyberpunk-noir`: High-tech low-life, neon-soaked streets, corporate shadows.
- `whimsical-fairy-tale`: Playful enchantment, talking creatures, moral lessons with heart.
- `post-apocalyptic`: Survival amid ruins, harsh beauty, rebuilding hope.
- `historical-intrigue`: Period authenticity, courtly machinations, personal stakes in grand events.

## Notes

- **Text model**: `llama-3.3-70b-versatile` via Groq (configurable in `worlds/<slug>/config.json` or Settings UI)
- **Image model**: `flux-dev` via Replicate (landscape 16:9 aspect ratio by default)
  - Choose at world creation with `--image-model` flag
  - Alternative: `flux-schnell` for faster/cheaper generation (~$0.003 per image)
  - Change anytime by editing `worlds/<slug>/config.json` → `"image_model": "flux-schnell"`
- **Image caching**: The CLI caches image prompts by hash to avoid duplicate API calls
- **Error handling**: If an API call fails, the tool will exit with an error message. Check your API keys and account status.

## Project Layout

- `worlds/<slug>/chapters/` — Generated Markdown chapters
- `worlds/<slug>/media/scenes/` — Generated scene art (PNG)
- `worlds/<slug>/media/index.json` — Media metadata index
- `worlds/<slug>/config.json` — World configuration
- `worlds/<slug>/state.json` — World state (characters, locations, chapter history)
- `worlds/<slug>/web/index.html` — Simple web viewer

## Contributing

Contributions are welcome! This is an early-stage project with plenty of room for expansion:

- Additional style packs and narrative presets
- Character/location/item image generation
- Export formats (EPUB, PDF)
- Advanced world simulation mechanics
- Test coverage

Feel free to open issues or submit pull requests.

## License

MIT License - see [LICENSE](LICENSE) for details.
