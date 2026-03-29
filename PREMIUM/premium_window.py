from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from voxtral_studio.config import AppConfig, AppPaths
from voxtral_studio.models import SynthesisResult, VoiceOption
from voxtral_studio.ui.main_window import MainWindow


class PremiumWindow(MainWindow):
    def __init__(self, paths: AppPaths, config: AppConfig) -> None:
        super().__init__(paths=paths, config=config)
        self.setWindowTitle("Voxtral Studio Premium")
        self.resize(1540, 980)
        self._install_premium_shell()
        self._restore_premium_ui_state()
        self._connect_premium_refresh()
        self._refresh_premium_status()

    def _install_premium_shell(self) -> None:
        root_layout = self.centralWidget().layout()
        self.hero = self._build_hero_banner()
        self.session_board = self._build_session_board()
        root_layout.removeWidget(self.tab_widget)
        self.hero_splitter = QSplitter(Qt.Orientation.Vertical)
        self.hero_splitter.setChildrenCollapsible(True)
        self.hero_splitter.addWidget(self.hero)
        self.hero_splitter.addWidget(self.tab_widget)
        self.hero_splitter.setStretchFactor(0, 1)
        self.hero_splitter.setStretchFactor(1, 5)
        self.hero_splitter.setSizes([170, 790])
        root_layout.insertWidget(2, self.hero_splitter, 1)

        synthesis_page = self.tab_widget.widget(0)
        synthesis_layout = synthesis_page.layout()
        synthesis_layout.insertWidget(0, self.session_board)

        self.tab_widget.setTabText(0, "Composer")
        self.tab_widget.setTabText(1, "Clone Lab")
        self.tab_widget.setTabText(2, "Engine Room")

    def _build_hero_banner(self) -> QWidget:
        hero = QFrame()
        hero.setObjectName("PremiumHero")
        layout = QHBoxLayout(hero)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        copy_column = QVBoxLayout()
        kicker = QLabel("Premium Studio")
        kicker.setObjectName("PremiumKicker")
        title = QLabel("Direction, cloning, export, and runtime control in one performance cockpit.")
        title.setObjectName("PremiumTitle")
        title.setWordWrap(True)
        self.hero_title = title
        copy = QLabel(
            "This premium pass keeps the exact same Voxtral engine, but reframes the workflow for longer sessions: faster status scanning, better quick actions, and clearer production context."
        )
        copy.setObjectName("PremiumCopy")
        copy.setWordWrap(True)
        self.hero_copy = copy

        actions = QHBoxLayout()
        self.hero_refresh_button = QPushButton("Refresh Voices")
        self.hero_refresh_button.setObjectName("GhostAction")
        self.hero_health_button = QPushButton("Check Health")
        self.hero_health_button.setObjectName("GhostAction")
        self.hero_output_button = QPushButton("Open Outputs")
        self.hero_output_button.setObjectName("GhostAction")
        self.hero_toggle_button = QPushButton("Collapse Hero")
        self.hero_toggle_button.setObjectName("GhostAction")
        actions.addWidget(self.hero_refresh_button)
        actions.addWidget(self.hero_health_button)
        actions.addWidget(self.hero_output_button)
        actions.addWidget(self.hero_toggle_button)
        actions.addStretch(1)

        copy_column.addWidget(kicker)
        copy_column.addWidget(title)
        copy_column.addWidget(copy)
        copy_column.addLayout(actions)
        metrics = QGridLayout()
        metrics.setSpacing(10)

        self.server_value = self._make_metric_card(metrics, 0, 0, "Runtime", "Offline")
        self.voice_value = self._make_metric_card(metrics, 0, 1, "Voice Focus", "Preset")
        self.chain_value = self._make_metric_card(metrics, 1, 0, "Export Chain", "WAV native")
        self.reference_value = self._make_metric_card(metrics, 1, 1, "Reference", "No sample")

        metrics_host = QWidget()
        metrics_host.setLayout(metrics)
        self.hero_metrics_host = metrics_host

        layout.addLayout(copy_column, 3)
        layout.addWidget(metrics_host, 2)
        return hero

    def _build_session_board(self) -> QWidget:
        board = QFrame()
        board.setObjectName("PremiumCard")
        layout = QHBoxLayout(board)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(18)

        self.board_status = QLabel("Session ready")
        self.board_status.setObjectName("PremiumValue")
        self.board_detail = QLabel(
            "Preset voices are filtered by language. Cloned voices use mood-tagged reference samples. Speed and pitch are always post-processed locally."
        )
        self.board_detail.setObjectName("PremiumCopy")
        self.board_detail.setWordWrap(True)

        copy = QVBoxLayout()
        kicker = QLabel("Studio Pulse")
        kicker.setObjectName("PremiumKicker")
        copy.addWidget(kicker)
        copy.addWidget(self.board_status)
        copy.addWidget(self.board_detail)

        self.board_mode = self._small_badge("Mode", "Preset")
        self.board_language = self._small_badge("Language", self.language_combo.currentText())
        self.board_export = self._small_badge("Output", self.output_format_combo.currentText())

        layout.addLayout(copy, 3)
        layout.addWidget(self.board_mode)
        layout.addWidget(self.board_language)
        layout.addWidget(self.board_export)
        return board

    def _make_metric_card(self, grid: QGridLayout, row: int, column: int, label: str, value: str) -> QLabel:
        card = QFrame()
        card.setObjectName("PremiumCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        metric = QLabel(label)
        metric.setObjectName("PremiumMetric")
        current = QLabel(value)
        current.setObjectName("PremiumValue")
        current.setWordWrap(True)
        layout.addWidget(metric)
        layout.addWidget(current)
        grid.addWidget(card, row, column)
        return current

    def _small_badge(self, label: str, value: str) -> QWidget:
        frame = QFrame()
        frame.setObjectName("PremiumCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        metric = QLabel(label)
        metric.setObjectName("PremiumMetric")
        current = QLabel(value)
        current.setObjectName("PremiumValue")
        current.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(metric, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(current, alignment=Qt.AlignmentFlag.AlignCenter)
        frame.current_value = current  # type: ignore[attr-defined]
        frame.setMinimumWidth(170)
        return frame

    def _connect_premium_refresh(self) -> None:
        self.hero_refresh_button.clicked.connect(self.refresh_voices_button.click)
        self.hero_health_button.clicked.connect(self.health_check_button.click)
        self.hero_output_button.clicked.connect(self.open_output_folder_button.click)
        self.hero_toggle_button.clicked.connect(self._toggle_hero)
        self.language_combo.currentTextChanged.connect(self._refresh_premium_status)
        self.output_format_combo.currentTextChanged.connect(self._refresh_premium_status)
        self.speed_spin.valueChanged.connect(self._refresh_premium_status)
        self.pitch_spin.valueChanged.connect(self._refresh_premium_status)
        self.voice_combo.currentTextChanged.connect(self._refresh_premium_status)
        self.clone_speaker_combo.currentTextChanged.connect(self._refresh_premium_status)
        self.clone_mood_combo.currentTextChanged.connect(self._refresh_premium_status)
        self.preset_voice_radio.toggled.connect(self._refresh_premium_status)
        self.clone_voice_radio.toggled.connect(self._refresh_premium_status)

    def _refresh_premium_status(self) -> None:
        if not hasattr(self, "server_value"):
            return
        runtime_text = self.health_state_label.text() if self.health_state_label.text() else "Not checked"
        self.server_value.setText(runtime_text)

        if self.preset_voice_radio.isChecked():
            voice_focus = self.voice_combo.currentText() or "Preset"
            reference = "Preset mode"
            mode = "Preset"
        else:
            voice_focus = self.clone_speaker_combo.currentText() or "Cloned"
            reference = self.clone_sample_label.text()
            mode = f"Mood: {self.clone_mood_combo.currentText() or 'n/a'}"

        chain = self.output_format_combo.currentText()
        if abs(self.speed_spin.value() - 1.0) > 1e-6 or abs(self.pitch_spin.value()) > 1e-6:
            chain = f"{chain} with local mastering"
        else:
            chain = f"{chain} native"

        self.voice_value.setText(voice_focus)
        self.chain_value.setText(chain)
        self.reference_value.setText(reference)
        self.board_status.setText(self.generation_status_label.text() or "Session ready")
        self.board_detail.setText(
            f"Language {self.language_combo.currentText()} | Speed {self.speed_spin.value():.2f}x | Pitch {self.pitch_spin.value():.1f} st"
        )
        self.board_mode.current_value.setText(mode)  # type: ignore[attr-defined]
        self.board_language.current_value.setText(self.language_combo.currentText())  # type: ignore[attr-defined]
        self.board_export.current_value.setText(self.output_format_combo.currentText())  # type: ignore[attr-defined]

    def _on_health_changed(self, healthy: bool, message: str) -> None:
        super()._on_health_changed(healthy, message)
        self._refresh_premium_status()

    def _on_refresh_voices_success(self, grouped: dict[str, list[VoiceOption]]) -> None:
        super()._on_refresh_voices_success(grouped)
        self._refresh_premium_status()

    def _on_generation_success(self, result: SynthesisResult) -> None:
        super()._on_generation_success(result)
        self._refresh_premium_status()

    def _on_generation_error(self, trace: str) -> None:
        super()._on_generation_error(trace)
        self._refresh_premium_status()

    def _update_clone_reference_preview(self) -> None:
        super()._update_clone_reference_preview()
        self._refresh_premium_status()

    def _toggle_hero(self) -> None:
        collapsed = self.hero_toggle_button.text() == "Expand Hero"
        if not collapsed:
            self.hero_title.setVisible(False)
            self.hero_copy.setVisible(False)
            self.hero_metrics_host.setVisible(False)
            self.hero_splitter.setSizes([86, 1])
            self.hero_toggle_button.setText("Expand Hero")
        else:
            self.hero_title.setVisible(True)
            self.hero_copy.setVisible(True)
            self.hero_metrics_host.setVisible(True)
            sizes = self.config.ui.premium_hero_splitter or [170, 790]
            self.hero_splitter.setSizes(sizes)
            self.hero_toggle_button.setText("Collapse Hero")

    def _capture_ui_state(self) -> None:
        super()._capture_ui_state()
        self.config.ui.premium_hero_collapsed = hasattr(self, "hero_toggle_button") and (
            self.hero_toggle_button.text() == "Expand Hero"
        )
        if hasattr(self, "hero_splitter"):
            sizes = self.hero_splitter.sizes()
            if sizes and sizes[0] > 0:
                self.config.ui.premium_hero_splitter = sizes

    def _restore_premium_ui_state(self) -> None:
        sizes = self.config.ui.premium_hero_splitter
        if hasattr(self, "hero_splitter") and len(sizes) == self.hero_splitter.count():
            self.hero_splitter.setSizes(sizes)
        if self.config.ui.premium_hero_collapsed and hasattr(self, "hero_toggle_button"):
            self.hero_title.setVisible(False)
            self.hero_copy.setVisible(False)
            self.hero_metrics_host.setVisible(False)
            self.hero_splitter.setSizes([86, 1])
            self.hero_toggle_button.setText("Expand Hero")
