# Contributing to Living Storyworld

Thanks for your interest in contributing! This project welcomes contributions in the form of bug fixes, improvements, and new features.

## Areas of Interest

Some areas I'd like to explore:

- More visual styles and story genres
- Character and location portraits
- Better ways to handle story endings
- Improved visual transitions between chapters
- Theming "Read" mode
- Adding background art for each world
- Handling cases where AI models refuse to generate content

## Getting Started

### Development Setup

```bash
git clone https://github.com/jonmartin721/living-storyworld.git
cd living-storyworld
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running the Application

```bash
# Start the web interface
python3 -m living_storyworld.cli web

# Interactive terminal UI
python3 -m living_storyworld.cli play
```

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature-name`)
3. Make your changes
4. Test your changes thoroughly
5. Commit with clear, concise messages
6. Push to your fork
7. Open a Pull Request

## Code Style

- Follow existing code patterns and conventions
- Use type hints where appropriate
- Keep functions focused and reasonably sized
- Comment the "why" not the "what"

## Reporting Bugs

Found a bug? Please [open an issue](https://github.com/jonmartin721/living-story-world/issues) with:

- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)
- Relevant error messages or logs

## Questions?

Feel free to open an issue for questions or discussions about potential features.
