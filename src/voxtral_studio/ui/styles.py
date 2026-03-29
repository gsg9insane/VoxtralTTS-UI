APP_STYLESHEET = """
QWidget {
    background: #eef7ff;
    color: #162333;
    font-size: 13px;
}

QMainWindow, QTabWidget::pane, QFrame, QGroupBox {
    background: #f8fbff;
}

QGroupBox {
    border: 1px solid #bfd7ee;
    border-radius: 12px;
    margin-top: 12px;
    padding: 14px;
    font-weight: 600;
}

QGroupBox:title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #1f6fb8;
}

QTabBar::tab {
    background: #dcecff;
    color: #24415f;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
    padding: 10px 18px;
    margin-right: 4px;
}

QTabBar::tab:selected {
    background: #1f6fb8;
    color: #f4fbff;
}

QPushButton {
    background: #1f6fb8;
    color: #f5fbff;
    border: none;
    border-radius: 10px;
    padding: 9px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background: #2d86d8;
}

QPushButton:disabled {
    background: #b8cde2;
    color: #edf5fb;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTableWidget {
    background: #fcfeff;
    border: 1px solid #c3d8ec;
    border-radius: 10px;
    padding: 6px;
    selection-background-color: #2d86d8;
    selection-color: #f8fcff;
}

QHeaderView::section {
    background: #e3f0fc;
    color: #31506f;
    border: none;
    padding: 8px;
    font-weight: 600;
}

QSplitter::handle {
    background: #d5e7f7;
}

QSplitter::handle:horizontal {
    width: 8px;
}

QSplitter::handle:vertical {
    height: 8px;
}

QLabel[role="muted"] {
    color: #5f7590;
}

QLabel[role="accent"] {
    color: #1f6fb8;
    font-weight: 700;
}
"""
