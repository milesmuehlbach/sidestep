import os
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from appdata import AppDataPaths
from pathlib import Path
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from tomlkit.toml_file import TOMLFile
from tomlkit import document
from textual.widgets import Button, Footer, Header, Label, RichLog, Static
import getpass

app_paths = AppDataPaths("sidestep")
app_paths.setup()

confpath = Path(app_paths.app_data_path) / "config.toml"
conffile = TOMLFile(confpath)


def load_config():
    if not confpath.is_file():
        first_run()
    with confpath.open("rb") as f:
        return tomllib.load(f)


def first_run():
    doc = document()
    doc.add("title", "Sidestep")
    doc.add("studentid", getpass.getuser())
    conffile.write(doc)


class Sidestep(App):
    TITLE = "Sidestep"

    CSS_PATH = "styles.tcss"

    HOME_BREW_PREFIX = Path.home() / "homebrew"

    @dataclass(frozen=True)
    class MenuAction:
        key: str
        label: str
        description: str
        handler: callable

    def _run_example_function(self) -> str:
        return "Sample function executed successfully. Replace this with your script logic."

    def _run_command(
        self, command: list[str], env: dict[str, str] | None = None
    ) -> str:
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, env=env
        )
        output = "\n".join(
            part for part in (result.stdout.strip(), result.stderr.strip()) if part
        ).strip()
        if result.returncode != 0:
            raise RuntimeError(output or f"Command failed: {' '.join(command)}")
        return output or "Done."

    def _homebrew_env(self, prefix: Path) -> dict[str, str]:
        env = os.environ.copy()
        env["HOMEBREW_PREFIX"] = str(prefix)
        env["HOMEBREW_CELLAR"] = str(prefix / "Cellar")
        env["HOMEBREW_REPOSITORY"] = str(prefix / "Homebrew")
        env["PATH"] = f"{prefix / 'bin'}:{prefix / 'sbin'}:{env.get('PATH', '')}"
        return env

    def _install_homebrew_to_home(self) -> str:
        if shutil.which("brew"):
            return f"Homebrew already installed at {shutil.which('brew')}"

        prefix = self.HOME_BREW_PREFIX
        repo = prefix / "Homebrew"
        bin_dir = prefix / "bin"
        brew_bin = bin_dir / "brew"

        prefix.mkdir(parents=True, exist_ok=True)

        if not repo.exists():
            self._run_command(
                ["git", "clone", "https://github.com/Homebrew/brew", str(repo)]
            )

        bin_dir.mkdir(parents=True, exist_ok=True)

        if brew_bin.exists() or brew_bin.is_symlink():
            brew_bin.unlink()
        brew_bin.symlink_to(Path("..") / "Homebrew" / "bin" / "brew")

        env = self._homebrew_env(prefix)
        self._run_command([str(brew_bin), "update", "--quiet"], env=env)

        shell_hint = (
            f'export PATH="{prefix / "bin"}:{prefix / "sbin"}:$PATH"\n'
            f'eval "$({prefix / "bin" / "brew"} shellenv)"'
        )
        return (
            f"Installed Homebrew to {prefix} without sudo.\n"
            f"Add this to your shell profile:\n{shell_hint}"
        )

    def _menu_actions(self) -> list[MenuAction]:
        return [
            self.MenuAction(
                key="ensure-homebrew",
                label="Install/Check Homebrew",
                description="Installs Homebrew into ~/homebrew if missing.",
                handler=self._install_homebrew_to_home,
            ),
            self.MenuAction(
                key="run-function",
                label="Run Sample Function",
                description="Scaffold action to run your Python functions.",
                handler=self._run_example_function,
            ),
        ]

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    def _log(self, message: str) -> None:
        self.query_one("#output", RichLog).write(message)

    def _set_actions_enabled(self, enabled: bool) -> None:
        for action in self._menu_actions():
            self.query_one(f"#{action.key}", Button).disabled = not enabled

    def compose(self) -> ComposeResult:
        confdata = load_config()
        yield Header()
        with Container(id="app-shell"):
            yield Label("Sidestep", id="title")
            yield Label(f"User: {confdata.get('studentid', 'Unknown')}", id="user-id")
            yield Static("Pick an action to run:", id="menu-hint")
            with Vertical(id="menu-panel"):
                for action in self._menu_actions():
                    with Horizontal(classes="menu-row"):
                        yield Button(action.label, id=action.key, variant="primary")
                        yield Static(action.description, classes="menu-description")
                yield Button("Quit", id="quit", variant="error")
            yield Static("Ready", id="status")
            yield RichLog(id="output", wrap=True, markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self._log("Welcome to Sidestep. Running initial Homebrew check...")
        self._set_actions_enabled(False)
        self.run_action("ensure-homebrew")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.exit()
            return
        self._set_actions_enabled(False)
        self.run_action(event.button.id or "")

    @work(thread=True, exclusive=True)
    def run_action(self, action_key: str) -> None:
        action = next(
            (item for item in self._menu_actions() if item.key == action_key), None
        )
        if action is None:
            self.call_from_thread(self._set_status, "Unknown action")
            self.call_from_thread(self._set_actions_enabled, True)
            return

        self.call_from_thread(self._set_status, f"Running: {action.label}")
        self.call_from_thread(self._log, f"\n>>> {action.label}")

        try:
            result = action.handler()
            self.call_from_thread(self._log, result)
            self.call_from_thread(self._set_status, "Done")
        except Exception as exc:
            self.call_from_thread(self._log, f"Error: {exc}")
            self.call_from_thread(self._set_status, "Failed")
        finally:
            self.call_from_thread(self._set_actions_enabled, True)


if __name__ == "__main__":
    app = Sidestep()
    app.run()
