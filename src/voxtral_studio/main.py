from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from voxtral_studio.config import AppPaths, load_config
from voxtral_studio.ui.main_window import MainWindow
from voxtral_studio.ui.styles import APP_STYLESHEET


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Voxtral Studio")
    app.setStyleSheet(APP_STYLESHEET)

    paths = AppPaths()
    config = load_config(paths)
    window = MainWindow(paths=paths, config=config)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
