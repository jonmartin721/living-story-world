from __future__ import annotations

import argparse
import os
from getpass import getpass
from pathlib import Path
from typing import Optional

from rich import print
from rich.table import Table

from .config import STYLE_PACKS, load_config, save_config
from .generator import generate_chapter
from .image import generate_scene_image
from .models import WorldConfig, WorldState
from .presets import PRESETS, DEFAULT_PRESET
from .settings import UserSettings, load_user_settings, save_user_settings, ensure_api_key_from_settings
from .storage import (
    WORLDS_DIR,
    ensure_world_dirs,
    get_current_world,
    read_json,
    set_current_world,
    slugify,
    write_json,
)
from .world import init_world, load_world, save_world, tick_world
from .tui import run_tui


def cmd_init(args: argparse.Namespace) -> None:
    slug = args.slug or slugify(args.title)
    style = args.style if args.style in STYLE_PACKS else "storybook-ink"
    image_model = args.image_model if hasattr(args, 'image_model') and args.image_model else "flux-dev"
    init_world(args.title, args.theme, style, slug, image_model=image_model)
    print(f"[bold green]Initialized[/] world '[cyan]{args.title}[/]' at [magenta]worlds/{slug}[/]")
    print(f"[dim]Image model: {image_model}[/]")


def cmd_use(args: argparse.Namespace) -> None:
    if not (WORLDS_DIR / args.slug).exists():
        raise SystemExit(f"[red]World not found:[/] {args.slug}")
    set_current_world(args.slug)
    print(f"Current world set to: [cyan]{args.slug}[/]")


def cmd_tick(args: argparse.Namespace) -> None:
    slug = args.world or get_current_world()
    if not slug:
        raise SystemExit("[yellow]No world chosen.[/] Use --world or `story use <slug>`. ")
    n = tick_world(slug)
    print(f"Ticked world '[cyan]{slug}[/]' to tick=[bold]{n}[/]")


def cmd_chapter(args: argparse.Namespace) -> None:
    slug = args.world or get_current_world()
    if not slug:
        raise SystemExit("[yellow]No world chosen.[/] Use --world or `story use <slug>`. ")
    # Ensure API key available
    if not ensure_api_key_from_settings():
        print("[red]OpenAI API key missing.[/] Run `story setup` first or export OPENAI_API_KEY.")
        raise SystemExit(2)
    cfg, state, dirs = load_world(slug)

    # Generate markdown via OpenAI
    settings = load_user_settings()
    ch = generate_chapter(
        dirs["base"],
        cfg,
        state,
        focus=args.focus,
        make_scene_image=not args.no_images,
    )

    # Update state
    state.chapters.append(ch.__dict__)
    state.next_chapter += 1
    save_world(slug, cfg, state, dirs)
    print(f"Wrote chapter [bold]{ch.number}[/]: [white]{ch.title}[/] -> [blue]{ch.filename}[/]")

    # Optionally generate the scene image immediately if a prompt exists
    if not args.no_images and ch.scene_prompt:
        out = generate_scene_image(
            dirs["base"], cfg.image_model, cfg.style_pack, ch.scene_prompt, chapter_num=ch.number
        )
        print(f"Generated scene image -> [green]{out.relative_to(dirs['base'])}[/]")


def cmd_image(args: argparse.Namespace) -> None:
    slug = args.world or get_current_world()
    if not slug:
        raise SystemExit("[yellow]No world chosen.[/] Use --world or `story use <slug>`. ")
    if not ensure_api_key_from_settings():
        print("[red]OpenAI API key missing.[/] Run `story setup` first or export OPENAI_API_KEY.")
        raise SystemExit(2)
    cfg, state, dirs = load_world(slug)
    if args.kind == "scene":
        if not args.prompt and args.chapter is None:
            raise SystemExit("[yellow]Provide --prompt or --chapter[/] to render a scene.")
        prompt = args.prompt
        chap_num = args.chapter
        if chap_num is not None and not prompt:
            # Try to pull from chapter record
            for c in state.chapters:
                if c.get("number") == chap_num:
                    prompt = c.get("scene_prompt")
                    break
        if not prompt:
            raise SystemExit("[yellow]No prompt found[/] for the requested chapter.")
        out = generate_scene_image(dirs["base"], cfg.image_model, cfg.style_pack, prompt, chapter_num=chap_num)
        print(f"Generated scene image -> [green]{out.relative_to(dirs['base'])}[/]")
    else:
        raise SystemExit("[yellow]Only 'scene' images are implemented in MVP.[/]")


def cmd_info(args: argparse.Namespace) -> None:
    slug = args.world or get_current_world()
    if not slug:
        worlds = [p.name for p in (WORLDS_DIR.glob("*/"))]
        print("[bold]Worlds:[/] ", ", ".join(worlds) or "(none)")
        current = get_current_world()
        if current:
            print("[bold]Current:[/] ", current)
        return
    cfg, state, dirs = load_world(slug)
    print(f"[bold]Title[/]: {cfg.title} | [bold]Slug[/]: {cfg.slug} | [bold]Theme[/]: {cfg.theme}")
    print(f"[bold]Style[/]: {cfg.style_pack} | [bold]Text[/]: {cfg.text_model} | [bold]Image[/]: {cfg.image_model}")
    print(f"[bold]Ticks[/]: {state.tick} | [bold]Chapters[/]: {len(state.chapters)}")


def cmd_build(args: argparse.Namespace) -> None:
    slug = args.world or get_current_world()
    if not slug:
        raise SystemExit("[yellow]No world chosen.[/] Use --world or `story use <slug>`. ")
    cfg, state, dirs = load_world(slug)
    # Build a simple index.html that lists chapters with first scene image if available
    media_idx = read_json(dirs["base"] / "media" / "index.json", [])
    scene_for_chapter = {}
    for m in media_idx:
        if m.get("type") == "scene" and m.get("chapter"):
            scene_for_chapter[m["chapter"]] = m["file"]

    items = []
    for ch in state.chapters:
        num = ch.number
        items.append({
            "title": ch.title,
            "file": f"chapters/{ch.filename}",
            "scene": scene_for_chapter.get(num),
        })

    # SECURITY: Escape HTML to prevent XSS
    import html as html_lib

    html = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>" + html_lib.escape(cfg.title) + "</title>",
        "<style>body{font-family:system-ui, sans-serif;max-width:920px;margin:3rem auto;padding:0 1rem} img{max-width:100%;height:auto;border-radius:6px} .chapter{margin:2rem 0;padding:1rem;border:1px solid #eee;border-radius:8px} .title{margin:0 0 .5rem;font-size:1.1rem;font-weight:600} .meta{color:#666;font-size:.9rem}</style>",
        "</head><body>",
        f"<h1>{html_lib.escape(cfg.title)}</h1>",
    ]
    if not items:
        html.append("<p>No chapters yet. Use <code>story chapter</code> to create one.</p>")
    for it in items:
        html.append("<div class='chapter'>")
        html.append(f"<div class='title'>{html_lib.escape(it['title'])}</div>")
        if it.get("scene"):
            # Scene path is from our own generation, but escape anyway
            html.append(f"<img src='{html_lib.escape(it['scene'])}' alt='scene image'>")
        html.append(f"<div class='meta'><a href='{html_lib.escape(it['file'])}'>Read markdown</a></div>")
        html.append("</div>")
    html.append("</body></html>")

    (dirs["web"] / "index.html").write_text("\n".join(html), encoding="utf-8")
    print(f"Built web index -> [green]{ (dirs['web'] / 'index.html').relative_to(dirs['base']) }[/]")


def cmd_setup(args: argparse.Namespace) -> None:
    s = load_user_settings()
    print("[bold]Living Storyworld Setup[/]")
    if os.environ.get("OPENAI_API_KEY"):
        print("Found OPENAI_API_KEY in environment. [green]Great![/]")
        s.openai_api_key = os.environ["OPENAI_API_KEY"]
    else:
        if s.openai_api_key:
            print("A saved API key already exists. Press Enter to keep it.")
        key = getpass("OpenAI API Key: ")
        if key.strip():
            s.openai_api_key = key.strip()
            os.environ["OPENAI_API_KEY"] = s.openai_api_key
            print("Saved API key to user settings.")
        elif not s.openai_api_key:
            print("[yellow]No key provided.[/] You can set it later with `story setup` or env var.")
    # Defaults
    if args.style and args.style in STYLE_PACKS:
        s.default_style_pack = args.style
    if args.preset and args.preset in PRESETS:
        s.default_preset = args.preset
    save_user_settings(s)
    print(f"Default style: [cyan]{s.default_style_pack}[/] | Default preset: [cyan]{s.default_preset}[/]")


def main(argv: Optional[list[str]] = None) -> None:
    p = argparse.ArgumentParser(prog="story", description="Living Storyworld CLI (no-args opens the interactive UI)")
    sub = p.add_subparsers(dest="cmd", required=False)

    sp = sub.add_parser("init", help="Create a new storyworld")
    sp.add_argument("--title", required=True)
    sp.add_argument("--theme", required=True, help="A short phrase describing the world's theme")
    sp.add_argument("--style", choices=list(STYLE_PACKS.keys()), default="storybook-ink")
    sp.add_argument("--image-model", choices=["flux-dev", "flux-schnell"], default="flux-dev",
                    help="Image generation model: flux-dev (quality, ~$0.025) or flux-schnell (fast, ~$0.003)")
    sp.add_argument("--slug", help="Directory name for the world")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("use", help="Set the current world by slug")
    sp.add_argument("slug")
    sp.set_defaults(func=cmd_use)

    sp = sub.add_parser("info", help="Show world info or list worlds")
    sp.add_argument("--world", help="Slug to inspect (optional)")
    sp.set_defaults(func=cmd_info)

    sp = sub.add_parser("tick", help="Advance the world simulation tick")
    sp.add_argument("--world", help="World slug (optional; defaults to current)")
    sp.set_defaults(func=cmd_tick)

    sp = sub.add_parser("chapter", help="Generate the next chapter using OpenAI")
    sp.add_argument("--world", help="World slug (optional; defaults to current)")
    sp.add_argument("--focus", help="Optional focus (character/location/goal)")
    sp.add_argument("--preset", choices=list(PRESETS.keys()), default=None, help="Narrative style preset")
    sp.add_argument("--no-images", action="store_true", help="Do not auto-generate a scene image")
    sp.set_defaults(func=cmd_chapter)

    sp = sub.add_parser("image", help="Generate images (MVP: scene)")
    sp.add_argument("kind", choices=["scene"])  # future: character, item
    sp.add_argument("--world", help="World slug (optional; defaults to current)")
    sp.add_argument("--chapter", type=int, help="Chapter number (to reuse its scene prompt)")
    sp.add_argument("--prompt", help="Explicit prompt override")
    sp.set_defaults(func=cmd_image)

    sp = sub.add_parser("build", help="Build a simple web index of chapters and images")
    sp.add_argument("--world", help="World slug (optional; defaults to current)")
    sp.set_defaults(func=cmd_build)

    sp = sub.add_parser("setup", help="Configure API key and defaults")
    sp.add_argument("--style", choices=list(STYLE_PACKS.keys()))
    sp.add_argument("--preset", choices=list(PRESETS.keys()))
    sp.set_defaults(func=cmd_setup)

    sp = sub.add_parser("web", help="Launch the web interface")
    sp.add_argument("--port", type=int, default=8001, help="Port to run the server on (default: 8001)")
    sp.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    def _web(args: argparse.Namespace) -> None:
        import webbrowser
        import time
        from threading import Timer

        url = f"http://localhost:{args.port}"

        if not args.no_browser:
            # Open browser after a short delay
            def open_browser():
                time.sleep(1.5)
                webbrowser.open(url)
            Timer(0, open_browser).start()

        print(f"[bold green]Starting web server at {url}[/]")
        print("[dim]Press Ctrl+C to stop[/]")
        print()
        print("[yellow]SECURITY:[/] This server binds to localhost only (127.0.0.1)")
        print("[yellow]Do NOT expose this to the internet without adding authentication[/]")
        print()

        # Run uvicorn
        import uvicorn
        uvicorn.run(
            "living_storyworld.webapp:app",
            host="127.0.0.1",
            port=args.port,
            log_level="info"
        )
    sp.set_defaults(func=_web)

    sp = sub.add_parser("play", help="Launch the interactive terminal UI")
    def _play(_: argparse.Namespace) -> None:
        run_tui()
    sp.set_defaults(func=_play)

    sp = sub.add_parser("desktop", help="Launch the desktop application")
    sp.add_argument("--port", type=int, default=8001, help="Port to run the server on (default: 8001)")
    def _desktop(args: argparse.Namespace) -> None:
        from living_storyworld.desktop import launch_desktop
        launch_desktop(port=args.port)
    sp.set_defaults(func=_desktop)

    args = p.parse_args(argv)
    if not args.cmd:
        # No subcommand provided: launch TUI by default
        run_tui()
        return
    args.func(args)


if __name__ == "__main__":
    main()
