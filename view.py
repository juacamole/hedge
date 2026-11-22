import os
from datetime import datetime

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.theme import Theme
from textual.widgets import (
    DataTable,
    Footer,
    Input,
    Label,
    ListItem,
    ListView,
    Sparkline,
    Static,
)

import storage
from capture import perplexity
from capture import run as run_prompt
from render import alt_count, alts_text, fmt, output_text, run_label, token_row

DEFAULTS = {
    "model": "qwen3.8-27b-abliterated",
    "n_predict": "20",
    "n_probs": "10",
    "temperature": "1",
    "seed": "-1",
}
INPUT_TYPES = {"model": "text", "temperature": "number"}
MONO = Theme(
    name="mono",
    primary="#c8c8c8",
    secondary="#8a8a8a",
    accent="#e0e0e0",
    foreground="#c8c8c8",
    background="#000000",
    surface="#000000",
    panel="#1a1a1a",
    boost="#0e0e0e",
    warning="#c8c8c8",
    error="#ffffff",
    success="#c8c8c8",
    dark=True,
    variables={
        "input-cursor-background": "#e0e0e0",
        "input-cursor-foreground": "#000000",
        "input-selection-background": "#3a3a3a",
        "footer-key-foreground": "#e0e0e0",
        "footer-description-foreground": "#6e6e6e",
        "block-cursor-background": "#2e2e2e",
        "block-cursor-foreground": "#ffffff",
    },
)
TITLES = {
    "#settings": "settings",
    "#runs": "runs",
    "#output": "output",
    "#tokens": "tokens",
    "#alts": "alternatives",
}


class Settings(Vertical, can_focus=True):
    BINDINGS = [
        Binding("j,down", "cursor(1)", "down", show=False),
        Binding("k,up", "cursor(-1)", "up", show=False),
        Binding("enter", "edit", "edit"),
    ]

    cursor = reactive(0)

    def watch_cursor(self, cursor: int) -> None:
        for i, row in enumerate(self.query(".row")):
            row.set_class(i == cursor, "-cursor")

    def on_mount(self) -> None:
        self.watch_cursor(self.cursor)

    def action_cursor(self, step: int) -> None:
        self.cursor = max(0, min(self.cursor + step, len(self.query(".row")) - 1))

    def action_edit(self) -> None:
        row = self.query(".row")[self.cursor]
        row.add_class("-editing")
        field = row.query_one(Input)
        field.focus()
        field.cursor_position = len(field.value)

    def on_descendant_blur(self, event) -> None:
        if isinstance(event.widget, Input):
            row = event.widget.parent
            row.remove_class("-editing")
            row.query_one(".value", Label).update(event.widget.value)

    def on_click(self, event) -> None:
        rows = list(self.query(".row"))
        node = event.widget
        while node is not None and node not in rows:
            node = node.parent
        if node is not None:
            self.cursor = rows.index(node)
            self.action_edit()


class Hedge(App):
    CSS_PATH = "hedge.tcss"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("escape", "browse", "back", priority=True),
        Binding("p", "focus_prompt", "prompt"),
        Binding("e", "focus_settings", "settings"),
        Binding("l", "move(1)", "tok→"),
        Binding("h", "move(-1)", "tok←"),
        Binding("j", "alt(1)", "alt↓"),
        Binding("k", "alt(-1)", "alt↑"),
        Binding("r", "send", "run"),
        Binding("s", "save", "save"),
        Binding("q", "quit", "quit"),
    ]

    def __init__(self, preloaded: list[tuple[dict, str]] | None = None) -> None:
        super().__init__()
        self.preloaded = preloaded or []
        self.runs: list[dict] = []
        self.current: dict | None = None
        self.selected = 0
        self.alt = 0
        self.saved: list[dict] = []
        self.busy = False

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="left"):
                with Settings(id="settings"):
                    for key, value in DEFAULTS.items():
                        with Horizontal(classes="row"):
                            yield Label(key, classes="key")
                            yield Label(value, classes="value", markup=False)
                            yield Input(
                                value=value,
                                id=key,
                                type=INPUT_TYPES.get(key, "integer"),
                                select_on_focus=False,
                            )
                yield ListView(id="runs")
            with Vertical(id="right"):
                with VerticalScroll(id="output"):
                    yield Static("", id="text")
                yield Sparkline([], id="spark", summary_function=min)
                yield DataTable(id="tokens", cursor_type="row", zebra_stripes=False)
                yield Static("", id="alts")
        yield Static("", id="status")
        yield Input(placeholder="prompt, enter to run", id="prompt")
        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(MONO)
        self.theme = "mono"
        for widget_id, title in TITLES.items():
            self.query_one(widget_id).border_title = title
        self.query_one(DataTable).add_columns(
            "pos", "token", "prob", "margin", "best other"
        )
        for result, label in self.preloaded:
            self.add_run(result, label)
        if not self.preloaded:
            self.load_saved()
        self.query_one("#prompt").focus()

    def load_saved(self) -> None:
        skipped = 0
        for path in storage.saved_paths():
            try:
                result = storage.load(path)
            except (OSError, ValueError):
                skipped += 1
                continue
            self.saved.append(result)
            self.add_run(result, os.path.basename(path)[5:-5])
        if skipped:
            self.set_status(f"skipped {skipped} unreadable run files")

    def set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(Text(message))

    def read_settings(self) -> dict:
        settings = {"prompt": self.query_one("#prompt", Input).value}
        for key in DEFAULTS:
            raw = self.query_one(f"#{key}", Input).value.strip()
            kind = INPUT_TYPES.get(key, "integer")
            if kind == "text":
                settings[key] = raw
            elif kind == "number":
                settings[key] = float(raw)
            else:
                settings[key] = int(raw)
        return settings

    def action_send(self) -> None:
        if self.busy:
            self.set_status("still generating…")
            return
        try:
            settings = self.read_settings()
        except ValueError:
            self.set_status("check the settings: a number field is empty or invalid")
            return
        if not settings["prompt"]:
            self.set_status("prompt is empty")
            return
        self.busy = True
        self.set_status("generating…")
        self.generate(settings)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in DEFAULTS:
            self.query_one(Settings).focus()
            return
        self.action_send()

    @work(thread=True)
    def generate(self, settings: dict) -> None:
        try:
            result = run_prompt(settings)
        except Exception as error:
            self.call_from_thread(self.run_finished, None, f"request failed: {error}")
            return
        self.call_from_thread(self.run_finished, result, "")

    def run_finished(self, result: dict | None, message: str) -> None:
        self.busy = False
        if result is None:
            self.set_status(message)
            return
        label = f"{datetime.now():%H:%M:%S} t={result['meta']['temperature']}"
        self.add_run(result, label)
        self.set_status(f"{len(result['records'])} tokens")

    def add_run(self, result: dict, label: str) -> None:
        self.runs.append(result)
        index = len(self.runs) - 1
        runs = self.query_one("#runs", ListView)
        runs.append(ListItem(Label(run_label(result, label)), name=str(index)))
        self.call_after_refresh(setattr, runs, "index", index)
        self.show_run(result)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is not None and event.item.name is not None:
            self.show_run(self.runs[int(event.item.name)])

    def show_run(self, result: dict) -> None:
        if result is self.current:
            return
        self.current = result
        records = result["records"]
        table = self.query_one(DataTable)
        table.clear()
        for rec in records:
            table.add_row(*token_row(rec))
        self.query_one(Sparkline).data = [rec["prob"] for rec in records]
        ppl = perplexity(records) if records else None
        self.query_one("#output").border_subtitle = f"perplexity {fmt(ppl)}"
        self.select_token(0)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.select_token(event.cursor_row)

    def select_token(self, index: int) -> None:
        if self.current is None or not self.current["records"]:
            return
        records = self.current["records"]
        self.selected = max(0, min(index, len(records) - 1))
        self.alt = 0
        self.query_one("#text", Static).update(output_text(self.current, self.selected))
        self.show_alts()

    def show_alts(self) -> None:
        rec = self.current["records"][self.selected]
        self.query_one("#alts", Static).update(alts_text(rec, self.alt))

    def action_alt(self, step: int) -> None:
        if self.current is None or not self.current["records"]:
            return
        count = alt_count(self.current["records"][self.selected])
        self.alt = max(0, min(self.alt + step, count - 1))
        self.show_alts()

    def action_move(self, step: int) -> None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return
        row = max(0, min(table.cursor_row + step, table.row_count - 1))
        table.move_cursor(row=row)

    def action_browse(self) -> None:
        if isinstance(self.focused, Input) and self.focused.id in DEFAULTS:
            self.query_one(Settings).focus()
            return
        self.query_one(DataTable).focus()

    def action_focus_prompt(self) -> None:
        self.query_one("#prompt").focus()

    def action_focus_settings(self) -> None:
        self.query_one(Settings).focus()

    def action_save(self) -> None:
        if self.current is None:
            self.set_status("nothing to save")
            return
        if any(run is self.current for run in self.saved):
            self.set_status("already saved")
            return
        path = storage.default_path()
        try:
            storage.save(self.current, path)
        except OSError as error:
            self.set_status(f"save failed: {error}")
            return
        self.saved.append(self.current)
        self.set_status(f"saved {path}")
