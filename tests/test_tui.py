from pathlib import Path

import pytest
from textual.widgets import Button

from ion.config import load_config
from ion.tui.app import IonApp


@pytest.mark.asyncio
async def test_model_picker_opens_without_key_or_network(tmp_path, monkeypatch):
    monkeypatch.setenv("ION_DATA_DIR", str(tmp_path / "ion-data"))
    for name in ("GROQ_API_KEY", "AI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    app = IonApp(load_config(Path(__file__).resolve().parents[1] / "ion.toml"))
    async with app.run_test():
        assert app.query_one("#cancel", Button).disabled
        await app.show_models()
        assert app.query_one("#models").display
        assert len(app.query("#models Button")) == len(app.config.profiles)
