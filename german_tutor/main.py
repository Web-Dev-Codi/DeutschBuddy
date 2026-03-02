from textual.app import App, ComposeResult
from textual.widgets import Header, Footer


class GermanTutorApp(App):
    """Main GermanTutor Textual application."""

    TITLE = "GermanTutor"
    CSS_PATH = "styles/main.tcss"
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()


def run() -> None:
    app = GermanTutorApp()
    app.run()


if __name__ == "__main__":
    run()
