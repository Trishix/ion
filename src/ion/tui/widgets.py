from __future__ import annotations

from pathlib import Path

from PIL import Image
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, RichLog, Static, TextArea
from textual.widgets.option_list import Option


class Transcript(RichLog):
    def on_resize(self, event) -> None:
        # Rebuild after this widget receives its final width, rather than the
        # earlier app resize event (which precedes sidebar/layout changes).
        if event.size.width != getattr(self, '_last_width', None):
            self._last_width = event.size.width
            self.call_after_refresh(self.app._reflow_transcript)


class Brand(Static):
    """Render the supplied PNG as terminal cells; no graphics protocol required."""

    def render(self) -> Text:
        with Image.open(Path(__file__).parent / 'assets' / 'logo.png') as source:
            gray = source.convert('L')
            bounds = gray.point(lambda value: 255 if value > 70 else 0).getbbox()
            pixels = gray.crop(bounds).resize((16, 16), Image.Resampling.LANCZOS)
        wordmark = ['█ █▀█ █▄ █', '█ █▄█ █ ▀█']
        output = Text()
        for row in range(8):
            for col in range(16):
                top = pixels.getpixel((col, row * 2)) > 100
                bottom = pixels.getpixel((col, row * 2 + 1)) > 100
                output.append('█' if top and bottom else '▀' if top else '▄' if bottom else ' ', style='#e7e5e4')
            output.append('    ' + (wordmark[row - 3] if row in (3, 4) else '          '), style='bold #e7e5e4')
            if row != 7:
                output.append('\n')
        return output


class Composer(TextArea):
    BINDINGS = [
        Binding('enter', 'submit', 'Send', priority=True),
        Binding('shift+enter', 'line_break', 'New line', priority=True),
        Binding('ctrl+j', 'line_break', 'New line', priority=True),
    ]

    class Submitted(Message):
        pass

    def action_submit(self) -> None:
        self.post_message(self.Submitted())

    def action_line_break(self) -> None:
        self.insert('\n')

    async def on_key(self, event) -> None:
        if getattr(self.app, 'leader_next', False):
            event.prevent_default()
            event.stop()
            await self.app.on_key(event)


class Picker(ModalScreen[str | None]):
    BINDINGS = [('escape', 'dismiss(None)', 'Close')]

    def __init__(self, title: str, items: list[tuple[str, str]], hint: str = '') -> None:
        super().__init__()
        self.heading, self.items, self.hint = title, items, hint

    def compose(self) -> ComposeResult:
        with Vertical(id='dialog'):
            yield Static(self.heading, id='dialog-title', markup=False)
            yield Input(placeholder='Search…', id='filter')
            yield OptionList(*(Option(label, id=key) for key, label in self.items), id='choices', markup=False)
            yield Static(self.hint or '↑↓ navigate   enter select   esc close', id='dialog-hint', markup=False)

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.casefold()
        choices = self.query_one(OptionList)
        choices.clear_options()
        choices.add_options(Option(label, id=key) for key, label in self.items if query in label.casefold())
        if choices.option_count:
            choices.highlighted = 0

    def on_key(self, event) -> None:
        if event.key in ('up', 'down') and self.query_one(Input).has_focus:
            choices = self.query_one(OptionList)
            choices.action_cursor_down() if event.key == 'down' else choices.action_cursor_up()
            event.prevent_default()
            event.stop()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one(OptionList).action_select()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)


class EntryDialog(ModalScreen[str | None]):
    BINDINGS = [('escape', 'dismiss(None)', 'Close')]

    def __init__(self, title: str, value: str = '', hint: str = '', secret: bool = False) -> None:
        super().__init__()
        self.heading, self.value, self.hint, self.secret = title, value, hint, secret

    def compose(self) -> ComposeResult:
        with Vertical(id='entry-dialog'):
            yield Static(self.heading, id='dialog-title', markup=False)
            yield Input(value=self.value, password=self.secret, placeholder='API key' if self.secret else 'Repository path', id='entry')
            yield Static(self.hint, id='dialog-hint', markup=False)

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value.strip():
            self.dismiss(event.value.strip())
