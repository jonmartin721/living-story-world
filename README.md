# Living Storyworld

A persistent narrative universe you can explore via a simple CLI. It generates chapters (Markdown) and scene illustrations using the OpenAI API, and builds a lightweight HTML index for viewing.

## Prerequisites

- **Python 3.8+** (developed with 3.10+)
- **OpenAI API key** ([get one here](https://platform.openai.com/api-keys))
- **Note**: This tool makes API calls to OpenAI. Each chapter generation uses `gpt-4o-mini` (text) and `dall-e-3` (images), which incur costs. Typical cost per chapter with image: ~$0.10-0.15 USD.

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
     --style storybook-ink
   ```

4. Generate a chapter:
   ```bash
   python3 -m living_storyworld.cli chapter \
     --world the-flooded-stacks \
     --preset cozy-adventure
   ```

5. View your story:
   ```bash
   python3 -m living_storyworld.cli build --world the-flooded-stacks
   # Open worlds/the-flooded-stacks/web/index.html in your browser
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

- Setup wizard (saves API key locally with 600 perms):
  - `python3 -m living_storyworld.cli setup --style storybook-ink --preset cozy-adventure`
- Interactive UI (Textual):
  - `python3 -m living_storyworld.cli play`
  - Colorful TUI with buttons to generate chapters and build the viewer.

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

## Notes

- **Text model**: `gpt-4o-mini` (configurable in `worlds/<slug>/config.json`)
- **Image model**: `dall-e-3` (landscape 1536x1024 by default)
- **Image caching**: The CLI caches image prompts by hash to avoid duplicate API calls
- **Error handling**: If an API call fails, the tool will exit with an error message. Check your API key and OpenAI account status.

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
