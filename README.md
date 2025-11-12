# Living Storyworld

>NovelAI but chill

Living Storyworld is a story generator that creates illustrated stories chapter by chapter. Each story builds on previous chapters, maintaining character and location continuity while letting you make choices that affect the narrative going forward.

The project started as an experiment in combining modern AI models with classic text adventure mechanics. I wanted to see if we could have the narrative depth of a novel without requiring the creative effort that services like NovelAI demand from users. 

---

## Features

- Stories remember characters and locations across chapters
- Works with multiple AI providers (OpenAI, Groq, Together AI, etc.) for both text and images
- Several visual styles for story illustrations
- Genre presets for different story types (fantasy, mystery, sci-fi, etc.)
- Web interface for managing worlds and generating chapters
- Image caching to avoid redundant API calls
- Random world generation with pre-built lore
---

## Quick Start

You can download pre-built executables from the [Releases](https://github.com/jonmartin721/living-storyworld/releases) page, or run from source:

```bash
git clone https://github.com/jonmartin721/living-storyworld.git
cd living-storyworld
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the web interface
python3 -m living_storyworld.cli web
```

The web app will open at `http://localhost:8001`. First-time setup will walk you through configuring API keys - I recommend using Gemini (free tier) plus Pollinations for images to get started without costs.

![Setup wizard for initial configuration](screenshots/setup-wizard.png)

Once you're in, create a new world by clicking "New" (or use the random generator) and start generating chapters. You can make choices at key points to steer the story direction.

## Interface & Workflow

The web interface provides a clean, distraction-free environment for managing your story worlds:

![Main interface showing world management](screenshots/main-page.png)

Creating a new world is simple - just give it a title and theme, or let the generator randomize one for you:

![New world creation dialog](screenshots/new-world-dialog.png)

First-time setup is straightforward. The settings panel lets you configure API keys for various AI providers:

![API keys configuration](screenshots/api-keys-settings.png)

As you read through chapters, you'll encounter choice points that let you influence how the story unfolds:

![Interactive choice moments](screenshots/make-choices.png)

The reading mode provides a clean, focused view for enjoying your generated chapters:

![Clean reading interface](screenshots/reading-mode.png)

---

## Visual Styles

Available illustration styles:
- `storybook-ink` - Ink and wash illustrations
- `pixel-rpg` - 16-bit pixel art style
- `lowpoly-iso` - Isometric low-poly scenes
- `watercolor-dream` - Soft watercolor paintings
- `noir-sketch` - High contrast ink drawings
- `art-nouveau` - Art Nouveau poster style
- `comic-book` - Classic comic book look
- `oil-painting` - Classical oil paintings

---

## Narrative Presets

Story genres to set the tone:
- `cozy-adventure` - Character-driven stories with gentle stakes
- `epic-fantasy` - High fantasy with kingdoms, magic, and large conflicts
- `solarpunk-explorer` - Hopeful eco-futurism and community building
- `whimsical-fairy-tale` - Modern fairy tales with charm and moral elements
- `noir-mystery` - Urban crime stories with cynical detectives
- `gothic-horror` - Atmospheric horror with family secrets and dread
- `cosmic-horror` - Existential stories about incomprehensible forces
- `cyberpunk-noir` - Near-future tech noir with corporate intrigue
- `slice-of-life` - Everyday moments and character relationships
- `historical-intrigue` - Period stories with political maneuvering
- `post-apocalyptic` - Survival and rebuilding after societal collapse
- `space-opera` - Grand interstellar adventures

---

## Architecture

The project uses FastAPI for the web backend with a plugin system for different AI providers. Each world is stored as JSON files with markdown chapters and PNG illustrations. The system tracks character and location state across chapters to maintain narrative consistency.

---

## API Keys & Setup

I recommend using Gemini 2.5 Flash (free tier available) with Pollinations for images to get started for free!. The setup wizard will walk you through this configuration.

**Security notes:**
- API keys are stored locally with restricted permissions
- The web server runs on localhost only
- No authentication is built-in (don't expose this to the internet)
- Basic security measures are in place for file operations

---

## Contributing

Some areas I'd like to explore:
- More visual styles and story genres
- Character and location portraits
- Better ways to handle story endings
- Improved visual transitions between chapters
- Theming "Read" mode
- Adding background art for each world
- Handling cases where AI models refuse to generate content

Pull requests are welcome for bug fixes or small improvements like the above. For larger features, it's probably best to open an issue first to discuss the approach.

Enjoy!

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---