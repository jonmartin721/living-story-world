from __future__ import annotations

from typing import Optional

from .settings import ensure_api_key_from_settings
from .storage import get_current_world


def run_tui() -> None:
    try:
        from textual.app import App, ComposeResult
        from textual.containers import Horizontal, Vertical
        from textual.reactive import reactive
        from textual.widgets import Button, Footer, Header, Input, Static
    except Exception:
        print("Textual is not installed. Run: pip install textual")
        return

    class Home(App):
        CSS = """
        Screen {align: center middle}
        #wrap {width: 80%; max-width: 100;}
        .row {height: auto;}
        Button {margin: 1 1;}
        .hint {color: #7a7a7a}
        Input {width: 100%;}
        """

        current_world: reactive[Optional[str]] = reactive(None)

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Vertical(id="wrap"):
                yield Static("Living Storyworld", classes="title")
                yield Static(
                    "Create chapters and images for your evolving world.",
                    classes="hint",
                )
                with Horizontal(classes="row"):
                    yield Button("Generate Chapter", id="gen")
                    yield Button("Build Viewer", id="build")
                    yield Button("World Setup", id="setup")
                yield Input(
                    placeholder="Type a command: chapter | build | info | init | use <slug>",
                    id="cmd",
                )
                yield Static("", id="status")
            yield Footer()

        def on_mount(self) -> None:
            ensure_api_key_from_settings()
            self.current_world = get_current_world()
            status = self.query_one("#status", Static)
            if self.current_world:
                status.update(f"Current world: [b]{self.current_world}[/b]")
            else:
                status.update("No current world. Click 'World Setup' to create one.")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            bid = event.button.id
            if bid == "gen":
                self._gen()
            elif bid == "build":
                self._build()
            elif bid == "setup":
                self._setup()

        def on_input_submitted(self, event: Input.Submitted) -> None:
            text = (event.value or "").strip().lower()
            if not text:
                return
            if text.startswith("use "):
                slug = text.split(None, 1)[1]
                import argparse

                from .cli import cmd_use

                try:
                    cmd_use(argparse.Namespace(slug=slug))
                    self.current_world = slug
                    self.query_one("#status", Static).update(
                        f"Using world: [b]{slug}[/b]"
                    )
                except SystemExit as e:
                    self.query_one("#status", Static).update(f"[red]Error:[/] {e}")
            elif text in ("chapter", "write", "next"):
                self._gen()
            elif text == "build":
                self._build()
            elif text == "info":
                self._info()
            elif text.startswith("init"):
                self._setup()
            else:
                self.query_one("#status", Static).update(
                    "Unknown command. Try: chapter | build | info | init | use <slug>"
                )

        def _gen(self) -> None:
            import argparse

            from .cli import cmd_chapter

            ns = argparse.Namespace(
                world=self.current_world, focus=None, no_images=False, preset=None
            )
            try:
                cmd_chapter(ns)
                self.query_one("#status", Static).update("Generated a new chapter.")
            except SystemExit as e:
                self.query_one("#status", Static).update(f"[red]Error:[/] {e}")

        def _build(self) -> None:
            import argparse

            from .cli import cmd_build

            ns = argparse.Namespace(world=self.current_world)
            try:
                cmd_build(ns)
                self.query_one("#status", Static).update(
                    "Built viewer (web/index.html)."
                )
            except SystemExit as e:
                self.query_one("#status", Static).update(f"[red]Error:[/] {e}")

        def _info(self) -> None:
            import argparse

            from .cli import cmd_info

            ns = argparse.Namespace(world=self.current_world)
            try:
                cmd_info(ns)
            except SystemExit as e:
                self.query_one("#status", Static).update(f"[red]Error:[/] {e}")

        def _setup(self) -> None:
            # Console wizard is simpler than masked inputs in Textual
            from .wizard import run_world_wizard

            self.exit()  # leave TUI for a moment
            run_world_wizard()
            # Relaunch TUI updated
            run_tui()

    Home().run()
