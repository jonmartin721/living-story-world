# Living Storyworld

A persistent narrative universe you can explore via a simple CLI. It generates chapters (Markdown) and scene illustrations using the OpenAI API, and builds a lightweight HTML index for viewing.

## Quickstart

- Install deps:
  - `python3 -m pip install -r requirements.txt`
- Set environment:
  - `export OPENAI_API_KEY=...`

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

- `storybook-ink`: Storybook ink and wash; muted palette, cozy, illustrative.
- `pixel-rpg`: 16-bit SNES pixel art; crisp sprites; nostalgic.
- `lowpoly-iso`: Low-poly isometric diorama; clean and stylized.

## Notes

- Text model: `gpt-4o-mini` (configurable in `worlds/<slug>/config.json`).
- Image model: `gpt-image-1` (landscape size by default).
- The CLI caches image prompts by hash to avoid duplicate generations.

## Layout

- `worlds/<slug>/chapters/` — Markdown chapters
- `worlds/<slug>/media/scenes/` — Generated scene art
- `worlds/<slug>/media/index.json` — Media index
- `worlds/<slug>/web/index.html` — Simple viewer
