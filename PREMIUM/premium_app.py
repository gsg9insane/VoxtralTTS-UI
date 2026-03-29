from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT / "PREMIUM") not in sys.path:
    sys.path.insert(0, str(ROOT / "PREMIUM"))

from PySide6.QtWidgets import QApplication

from premium_styles import PREMIUM_STYLESHEET
from premium_window import PremiumWindow
from voxtral_studio.config import AppPaths, load_config
from voxtral_studio.ui.styles import APP_STYLESHEET


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Voxtral Studio Premium")
    app.setStyleSheet(APP_STYLESHEET + PREMIUM_STYLESHEET)

    paths = AppPaths(ROOT)
    config = load_config(paths)
    window = PremiumWindow(paths=paths, config=config)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

