from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Label, Button, Header, Footer
from appdata import AppDataPaths
from pathlib import Path
from tomlkit.toml_file import TOMLFile
from tomlkit import document
import getpass
import tomllib

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

    def compose(self) -> ComposeResult:
        confdata = load_config()
        yield Header()
        yield Label("Sidestep", id="title")
        yield Label(f"Student ID: {confdata.get('studentid', 'Unknown')}", id="user-id")
        yield Footer()


if __name__ == "__main__":
    app = Sidestep()
    app.run()
