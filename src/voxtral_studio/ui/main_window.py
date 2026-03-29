from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from voxtral_studio.config import (
    AppConfig,
    AppPaths,
    DEFAULT_REMOTE_BASE_URL,
    DEFAULT_MOODS,
    DEFAULT_SERVER_VOICES,
    LOCAL_PROVIDER,
    POST_PROCESSABLE_FORMATS,
    REMOTE_PROVIDER,
    SERVER_RESPONSE_FORMATS,
    SUPPORTED_LANGUAGES,
    organize_voices_by_language,
    save_config,
)
from voxtral_studio.models import SynthesisRequest, SynthesisResult, VoiceOption
from voxtral_studio.services.audio_tools import AudioProcessor
from voxtral_studio.services.server_manager import ServerManager
from voxtral_studio.services.tts_client import TTSClient
from voxtral_studio.services.voice_library import VoiceLibrary
from voxtral_studio.ui.workers import WorkerThread


class MainWindow(QMainWindow):
    def __init__(self, paths: AppPaths, config: AppConfig) -> None:
        super().__init__()
        self.paths = paths
        self.config = config
        self.voice_library = VoiceLibrary(paths)
        self.server_manager = ServerManager(self)
        self.audio_output = QAudioOutput(self)
        self.audio_player = QMediaPlayer(self)
        self.audio_player.setAudioOutput(self.audio_output)
        self.active_workers: list[WorkerThread] = []
        self.server_voice_groups = self._default_local_voice_groups()
        self.last_result: SynthesisResult | None = None

        self.setWindowTitle("Voxtral Studio")
        self.resize(1360, 920)

        self._build_ui()
        self._wire_events()
        self._load_runtime_into_form()
        self._refresh_voice_library_ui()
        self._apply_voice_groups(self.server_voice_groups)
        self._restore_ui_state()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._persist_config()
        self.server_manager.stop()
        super().closeEvent(event)

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        header = QLabel("Voxtral Studio")
        header.setProperty("role", "accent")
        header.setStyleSheet("font-size: 26px;")
        subtitle = QLabel(
            "Native desktop control room for local Voxtral TTS, preset voices, cloned voice profiles, mood-tagged references, and export mastering."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty("role", "muted")
        root_layout.addWidget(header)
        root_layout.addWidget(subtitle)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self._build_synthesis_tab(), "Synthesis")
        self.tab_widget.addTab(self._build_voice_library_tab(), "Voice Library")
        self.tab_widget.addTab(self._build_runtime_tab(), "Runtime")
        root_layout.addWidget(self.tab_widget, 1)

        self.setCentralWidget(root)

    def _build_synthesis_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        controls_group = QGroupBox("Synthesis Controls")
        controls_layout = QVBoxLayout(controls_group)

        source_group = QGroupBox("Voice Source")
        source_layout = QVBoxLayout(source_group)
        self.preset_voice_radio = QRadioButton("Use preset server voice")
        self.clone_voice_radio = QRadioButton("Use cloned voice sample")
        self.preset_voice_radio.setChecked(True)
        self.voice_mode_group = QButtonGroup(self)
        self.voice_mode_group.setExclusive(True)
        self.voice_mode_group.addButton(self.preset_voice_radio)
        self.voice_mode_group.addButton(self.clone_voice_radio)
        source_layout.addWidget(self.preset_voice_radio)
        source_layout.addWidget(self.clone_voice_radio)

        preset_box = QGroupBox("Preset Voices")
        preset_box.setMinimumWidth(460)
        preset_form = QFormLayout(preset_box)
        preset_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.language_combo = QComboBox()
        for code, label in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(label, userData=code)
        self.voice_combo = QComboBox()
        self.voice_combo.setMinimumContentsLength(22)
        self.refresh_voices_button = QPushButton("Refresh voices")
        self.voice_meta_label = QLabel("Select a voice to see supported languages and metadata.")
        self.voice_meta_label.setWordWrap(True)
        self.voice_meta_label.setProperty("role", "muted")
        self.voice_meta_label.setMinimumHeight(42)
        preset_form.addRow("Language", self.language_combo)
        preset_form.addRow("Voice", self.voice_combo)
        preset_form.addRow("Details", self.voice_meta_label)
        preset_form.addRow("", self.refresh_voices_button)

        clone_box = QGroupBox("Cloned Voice Profiles")
        clone_box.setMinimumWidth(420)
        clone_form = QFormLayout(clone_box)
        clone_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.clone_speaker_combo = QComboBox()
        self.clone_speaker_combo.setMinimumContentsLength(20)
        self.clone_mood_combo = QComboBox()
        self.clone_mood_combo.setEditable(True)
        self.clone_sample_label = QLabel("No cloned sample selected")
        self.clone_sample_label.setWordWrap(True)
        self.clone_sample_label.setProperty("role", "muted")
        clone_form.addRow("Speaker", self.clone_speaker_combo)
        clone_form.addRow("Mood", self.clone_mood_combo)
        clone_form.addRow("Reference", self.clone_sample_label)

        self.source_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.source_splitter.setChildrenCollapsible(False)
        self.source_splitter.addWidget(preset_box)
        self.source_splitter.addWidget(clone_box)
        self.source_splitter.setStretchFactor(0, 2)
        self.source_splitter.setStretchFactor(1, 2)
        controls_layout.addWidget(source_group)
        controls_layout.addWidget(self.source_splitter)

        synthesis_grid = QGridLayout()
        self.output_format_combo = QComboBox()
        self.output_format_combo.setMinimumWidth(180)
        for fmt in POST_PROCESSABLE_FORMATS:
            self.output_format_combo.addItem(fmt.upper(), userData=fmt)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setMinimumWidth(150)
        self.speed_spin.setDecimals(2)
        self.speed_spin.setRange(0.5, 1.75)
        self.speed_spin.setSingleStep(0.05)
        self.speed_spin.setValue(1.0)

        self.pitch_spin = QDoubleSpinBox()
        self.pitch_spin.setMinimumWidth(150)
        self.pitch_spin.setDecimals(1)
        self.pitch_spin.setRange(-12.0, 12.0)
        self.pitch_spin.setSingleStep(0.5)
        self.pitch_spin.setValue(0.0)

        self.timeout_note = QLabel(
            "With the public Voxtral checkpoint, preset voices work locally. Speed and pitch are applied after generation, and voice cloning depends on encoder weights that are not shipped in the open-source checkpoint."
        )
        self.timeout_note.setWordWrap(True)
        self.timeout_note.setProperty("role", "muted")

        synthesis_grid.addWidget(QLabel("Output format"), 0, 0)
        synthesis_grid.addWidget(self.output_format_combo, 0, 1)
        synthesis_grid.addWidget(QLabel("Speed"), 0, 2)
        synthesis_grid.addWidget(self.speed_spin, 0, 3)
        synthesis_grid.addWidget(QLabel("Pitch (semitones)"), 0, 4)
        synthesis_grid.addWidget(self.pitch_spin, 0, 5)
        controls_layout.addLayout(synthesis_grid)
        controls_layout.addWidget(self.timeout_note)

        text_group = QGroupBox("Text")
        text_layout = QVBoxLayout(text_group)
        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText("Paste or type the text you want Voxtral to speak...")
        self.text_input.setMinimumHeight(190)
        text_layout.addWidget(self.text_input)

        actions_layout = QHBoxLayout()
        self.generate_button = QPushButton("Generate")
        self.save_as_button = QPushButton("Save As")
        self.open_output_folder_button = QPushButton("Open Output Folder")
        self.save_as_button.setEnabled(False)
        actions_layout.addWidget(self.generate_button)
        actions_layout.addWidget(self.save_as_button)
        actions_layout.addWidget(self.open_output_folder_button)
        actions_layout.addStretch(1)
        text_layout.addLayout(actions_layout)

        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        self.generation_status_label = QLabel("Ready")
        self.generation_status_label.setProperty("role", "accent")
        self.output_path_label = QLabel("No audio generated yet")
        self.output_path_label.setWordWrap(True)
        self.output_path_label.setProperty("role", "muted")

        playback_buttons = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        playback_buttons.addWidget(self.play_button)
        playback_buttons.addWidget(self.pause_button)
        playback_buttons.addWidget(self.stop_button)
        playback_buttons.addStretch(1)

        output_layout.addWidget(self.generation_status_label)
        output_layout.addWidget(self.output_path_label)
        output_layout.addLayout(playback_buttons)

        self.synthesis_splitter = QSplitter(Qt.Orientation.Vertical)
        self.synthesis_splitter.setChildrenCollapsible(False)
        self.synthesis_splitter.addWidget(controls_group)
        self.synthesis_splitter.addWidget(text_group)
        self.synthesis_splitter.addWidget(output_group)
        self.synthesis_splitter.setStretchFactor(0, 3)
        self.synthesis_splitter.setStretchFactor(1, 4)
        self.synthesis_splitter.setStretchFactor(2, 2)
        self.synthesis_splitter.setSizes([320, 360, 180])

        layout.addWidget(self.synthesis_splitter)
        return page

    def _build_voice_library_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.voice_library_splitter = QSplitter(Qt.Orientation.Horizontal)

        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        table_group = QGroupBox("Saved Reference Samples")
        group_layout = QVBoxLayout(table_group)
        self.voice_table = QTableWidget(0, 6)
        self.voice_table.setHorizontalHeaderLabels(
            ["Speaker", "Mood", "Language", "Duration", "File", "Added"]
        )
        self.voice_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.voice_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.voice_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.voice_table.horizontalHeader().setStretchLastSection(True)
        group_layout.addWidget(self.voice_table)

        buttons = QHBoxLayout()
        self.delete_sample_button = QPushButton("Delete Selected")
        self.open_voice_folder_button = QPushButton("Open Voice Folder")
        buttons.addWidget(self.delete_sample_button)
        buttons.addWidget(self.open_voice_folder_button)
        buttons.addStretch(1)
        group_layout.addLayout(buttons)
        table_layout.addWidget(table_group)

        form_panel = QWidget()
        form_layout = QVBoxLayout(form_panel)
        import_group = QGroupBox("Import New Voice Sample")
        import_form = QFormLayout(import_group)

        self.import_speaker_edit = QLineEdit()
        self.import_language_combo = QComboBox()
        for code, label in SUPPORTED_LANGUAGES:
            self.import_language_combo.addItem(label, userData=code)

        self.import_mood_combo = QComboBox()
        self.import_mood_combo.setEditable(True)
        for mood in DEFAULT_MOODS:
            self.import_mood_combo.addItem(mood)

        self.import_notes_edit = QTextEdit()
        self.import_notes_edit.setPlaceholderText("Optional notes about the sample or intended use...")
        self.import_notes_edit.setFixedHeight(110)
        self.import_tags_edit = QLineEdit()
        self.import_tags_edit.setPlaceholderText("Optional comma-separated tags")
        self.import_consent_checkbox = QCheckBox("I confirm I have the right to use and clone this voice sample.")

        self.import_status_label = QLabel("Recommended reference length from Mistral materials: roughly 3-25 seconds.")
        self.import_status_label.setWordWrap(True)
        self.import_status_label.setProperty("role", "muted")

        self.import_button = QPushButton("Import Audio Sample")
        import_form.addRow("Speaker", self.import_speaker_edit)
        import_form.addRow("Language", self.import_language_combo)
        import_form.addRow("Mood", self.import_mood_combo)
        import_form.addRow("Notes", self.import_notes_edit)
        import_form.addRow("Tags", self.import_tags_edit)
        import_form.addRow("", self.import_consent_checkbox)
        import_form.addRow("", self.import_button)
        import_form.addRow("", self.import_status_label)

        form_layout.addWidget(import_group)
        form_layout.addStretch(1)

        self.voice_library_splitter.addWidget(table_panel)
        self.voice_library_splitter.addWidget(form_panel)
        self.voice_library_splitter.setSizes([840, 400])

        layout.addWidget(self.voice_library_splitter)
        return page

    def _build_runtime_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        runtime_group = QGroupBox("Server Runtime")
        runtime_form = QFormLayout(runtime_group)
        runtime_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.server_command_edit = QLineEdit()
        self.server_command_edit.setPlaceholderText("auto")
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("Local server", userData=LOCAL_PROVIDER)
        self.provider_combo.addItem("Mistral API", userData=REMOTE_PROVIDER)
        self.model_edit = QLineEdit()
        self.remote_model_edit = QLineEdit()
        self.host_edit = QLineEdit()
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(8000)
        self.extra_args_edit = QLineEdit()
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(10.0, 1200.0)
        self.timeout_spin.setValue(180.0)
        self.timeout_spin.setDecimals(1)
        self.timeout_spin.setSingleStep(5.0)
        self.ffmpeg_edit = QLineEdit()
        self.api_base_url_edit = QLineEdit()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Paste key here or use MISTRAL_API_KEY")
        self.save_api_key_checkbox = QCheckBox("Save API key in config.json")
        self.pass_language_checkbox = QCheckBox("Pass language hint to the endpoint when supported")
        self.runtime_state_label = QLabel("Server stopped")
        self.runtime_state_label.setProperty("role", "accent")
        self.health_state_label = QLabel("Not checked yet")
        self.health_state_label.setProperty("role", "muted")

        runtime_form.addRow("Backend", self.provider_combo)
        runtime_form.addRow("Command", self.server_command_edit)
        runtime_form.addRow("Local model / path", self.model_edit)
        runtime_form.addRow("Remote model", self.remote_model_edit)
        runtime_form.addRow("Host", self.host_edit)
        runtime_form.addRow("Port", self.port_spin)
        runtime_form.addRow("API base URL", self.api_base_url_edit)
        runtime_form.addRow("API key", self.api_key_edit)
        runtime_form.addRow("", self.save_api_key_checkbox)
        runtime_form.addRow("Extra args", self.extra_args_edit)
        runtime_form.addRow("Request timeout", self.timeout_spin)
        runtime_form.addRow("ffmpeg command", self.ffmpeg_edit)
        runtime_form.addRow("", self.pass_language_checkbox)
        runtime_form.addRow("Process state", self.runtime_state_label)
        runtime_form.addRow("Health", self.health_state_label)

        runtime_actions = QHBoxLayout()
        self.start_server_button = QPushButton("Start Local Server")
        self.stop_server_button = QPushButton("Stop Server")
        self.health_check_button = QPushButton("Check Health")
        runtime_actions.addWidget(self.start_server_button)
        runtime_actions.addWidget(self.stop_server_button)
        runtime_actions.addWidget(self.health_check_button)
        runtime_actions.addStretch(1)

        self.runtime_docs_label = QLabel(
            "Runtime launcher: `auto` prova prima `vllm` nel PATH e su Windows fa fallback al Python del progetto. Nota pratica: la UI gira su Windows, ma per il backend `vLLM` ufficiale potresti dover usare WSL2/Linux."
        )
        self.runtime_docs_label.setWordWrap(True)
        self.runtime_docs_label.setProperty("role", "muted")

        log_group = QGroupBox("Server Log")
        log_layout = QVBoxLayout(log_group)
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)

        layout.addWidget(runtime_group)
        layout.addLayout(runtime_actions)
        layout.addWidget(self.runtime_docs_label)
        layout.addWidget(log_group, 1)
        return page

    def _wire_events(self) -> None:
        self.language_combo.currentIndexChanged.connect(self._update_voice_combo_for_language)
        self.voice_combo.currentIndexChanged.connect(self._update_voice_metadata_preview)
        self.voice_combo.currentTextChanged.connect(self._update_voice_metadata_preview)
        self.clone_speaker_combo.currentIndexChanged.connect(self._update_clone_moods)
        self.clone_mood_combo.currentTextChanged.connect(self._update_clone_reference_preview)
        self.generate_button.clicked.connect(self._generate_audio)
        self.save_as_button.clicked.connect(self._save_current_output_as)
        self.open_output_folder_button.clicked.connect(lambda: self._open_folder(self.paths.output_dir))
        self.play_button.clicked.connect(self.audio_player.play)
        self.pause_button.clicked.connect(self.audio_player.pause)
        self.stop_button.clicked.connect(self.audio_player.stop)
        self.import_button.clicked.connect(self._import_sample)
        self.delete_sample_button.clicked.connect(self._delete_selected_sample)
        self.open_voice_folder_button.clicked.connect(lambda: self._open_folder(self.paths.voice_dir))
        self.refresh_voices_button.clicked.connect(self._refresh_server_voices)
        self.start_server_button.clicked.connect(self._start_server)
        self.stop_server_button.clicked.connect(self.server_manager.stop)
        self.health_check_button.clicked.connect(self._check_health)
        self.server_manager.log_received.connect(self._append_log)
        self.server_manager.state_changed.connect(self._on_server_state_changed)
        self.server_manager.health_changed.connect(self._on_health_changed)
        self.preset_voice_radio.toggled.connect(self._update_voice_source_mode)
        self.clone_voice_radio.toggled.connect(self._update_voice_source_mode)
        self.model_edit.textChanged.connect(self._update_voice_source_mode)
        self.remote_model_edit.textChanged.connect(self._update_voice_source_mode)
        self.provider_combo.currentIndexChanged.connect(self._update_runtime_provider_ui)

    def _load_runtime_into_form(self) -> None:
        runtime = self.config.runtime
        self.provider_combo.setCurrentIndex(0 if runtime.provider == LOCAL_PROVIDER else 1)
        self.server_command_edit.setText(runtime.server_command)
        self.model_edit.setText(runtime.model)
        self.remote_model_edit.setText(runtime.remote_model)
        self.host_edit.setText(runtime.host)
        self.port_spin.setValue(runtime.port)
        self.extra_args_edit.setText(runtime.extra_args)
        self.timeout_spin.setValue(runtime.request_timeout)
        self.ffmpeg_edit.setText(runtime.ffmpeg_command)
        self.api_base_url_edit.setText(runtime.api_base_url)
        self.api_key_edit.setText(runtime.api_key)
        self.save_api_key_checkbox.setChecked(runtime.save_api_key)
        self.pass_language_checkbox.setChecked(runtime.pass_language_hint)
        self._update_runtime_provider_ui()
        self._update_voice_source_mode()

    def _persist_config(self) -> None:
        self._capture_ui_state()
        runtime = self.config.runtime
        runtime.provider = str(self.provider_combo.currentData())
        runtime.server_command = self.server_command_edit.text().strip() or "auto"
        runtime.model = self.model_edit.text().strip() or runtime.model
        runtime.remote_model = self.remote_model_edit.text().strip() or runtime.remote_model
        runtime.host = self.host_edit.text().strip() or "127.0.0.1"
        runtime.port = self.port_spin.value()
        runtime.api_base_url = self.api_base_url_edit.text().strip() or DEFAULT_REMOTE_BASE_URL
        runtime.extra_args = self.extra_args_edit.text().strip()
        runtime.request_timeout = self.timeout_spin.value()
        runtime.ffmpeg_command = self.ffmpeg_edit.text().strip() or "ffmpeg"
        runtime.pass_language_hint = self.pass_language_checkbox.isChecked()
        runtime.save_api_key = self.save_api_key_checkbox.isChecked()
        in_memory_api_key = self.api_key_edit.text().strip()
        runtime.api_key = in_memory_api_key
        saved_api_key = in_memory_api_key if runtime.save_api_key else ""
        runtime.api_key = saved_api_key
        save_config(self.paths, self.config)
        runtime.api_key = in_memory_api_key

    def _capture_ui_state(self) -> None:
        ui = self.config.ui
        if hasattr(self, "synthesis_splitter"):
            ui.synthesis_splitter = self.synthesis_splitter.sizes()
        if hasattr(self, "source_splitter"):
            ui.source_splitter = self.source_splitter.sizes()
        if hasattr(self, "voice_library_splitter"):
            ui.voice_library_splitter = self.voice_library_splitter.sizes()

    def _restore_ui_state(self) -> None:
        ui = self.config.ui
        if hasattr(self, "synthesis_splitter") and len(ui.synthesis_splitter) == self.synthesis_splitter.count():
            self.synthesis_splitter.setSizes(ui.synthesis_splitter)
        if hasattr(self, "source_splitter") and len(ui.source_splitter) == self.source_splitter.count():
            self.source_splitter.setSizes(ui.source_splitter)
        if hasattr(self, "voice_library_splitter") and len(ui.voice_library_splitter) == self.voice_library_splitter.count():
            self.voice_library_splitter.setSizes(ui.voice_library_splitter)

    def _update_runtime_provider_ui(self) -> None:
        remote = self._is_remote_provider()
        self.server_command_edit.setEnabled(not remote)
        self.model_edit.setEnabled(not remote)
        self.host_edit.setEnabled(not remote)
        self.port_spin.setEnabled(not remote)
        self.extra_args_edit.setEnabled(not remote)
        self.start_server_button.setEnabled(not remote)
        self.stop_server_button.setEnabled(not remote)
        self.remote_model_edit.setEnabled(remote)
        self.api_base_url_edit.setEnabled(remote)
        self.api_key_edit.setEnabled(remote)
        self.save_api_key_checkbox.setEnabled(remote)
        self.pass_language_checkbox.setEnabled(not remote)
        self.refresh_voices_button.setText("Refresh saved voices" if remote else "Refresh voices")
        self.voice_combo.setEditable(remote)
        self.runtime_docs_label.setText(
            "Remote mode uses the official Mistral API. Set API base URL, remote model, and an API key here or via MISTRAL_API_KEY."
            if remote
            else "Runtime launcher: `auto` prova prima `vllm` nel PATH e su Windows fa fallback al Python del progetto. Nota pratica: la UI gira su Windows, ma per il backend `vLLM` ufficiale potresti dover usare WSL2/Linux."
        )
        self._update_voice_source_mode()

    def _update_voice_source_mode(self) -> None:
        cloning_supported = self._voice_cloning_supported()
        if not cloning_supported and self.clone_voice_radio.isChecked():
            self.preset_voice_radio.setChecked(True)

        self.clone_voice_radio.setEnabled(cloning_supported)
        self.clone_voice_radio.setToolTip(
            ""
            if cloning_supported
            else "The public Voxtral-4B-TTS-2603 checkpoint does not include the encoder weights needed for local voice cloning."
        )
        preset_enabled = self.preset_voice_radio.isChecked()
        self.language_combo.setEnabled(True)
        self.voice_combo.setEnabled(preset_enabled)
        self.refresh_voices_button.setEnabled(preset_enabled)
        clone_enabled = (not preset_enabled) and cloning_supported
        self.clone_speaker_combo.setEnabled(clone_enabled)
        self.clone_mood_combo.setEnabled(clone_enabled)
        if self._is_remote_provider() and self.voice_combo.lineEdit() is not None:
            self.voice_combo.lineEdit().setPlaceholderText("Paste a Mistral voice_id or refresh saved voices")
        self._update_voice_metadata_preview()
        self._update_clone_reference_preview()

    def _current_language_code(self) -> str:
        return str(self.language_combo.currentData())

    def _apply_voice_groups(self, grouped: dict[str, list[VoiceOption]]) -> None:
        self.server_voice_groups = grouped
        self._update_voice_combo_for_language()

    def _update_voice_combo_for_language(self) -> None:
        if self._is_remote_provider():
            language_label = self.language_combo.currentText() or "English"
            voices = self.server_voice_groups.get(language_label, [])
            if not voices:
                seen_values: set[str] = set()
                voices = []
                for options in self.server_voice_groups.values():
                    for option in options:
                        if option.value in seen_values:
                            continue
                        seen_values.add(option.value)
                        voices.append(option)
        else:
            language_label = self.language_combo.currentText() or "English"
            voices = self.server_voice_groups.get(language_label, [])
        self.voice_combo.blockSignals(True)
        current_text = self.voice_combo.currentText()
        self.voice_combo.clear()
        for option in voices:
            self.voice_combo.addItem(option.label, userData=option)
        if self._is_remote_provider() and current_text and self.voice_combo.findText(current_text) < 0:
            self.voice_combo.setEditText(current_text)
        self.voice_combo.blockSignals(False)
        self._update_voice_metadata_preview()

    def _refresh_voice_library_ui(self) -> None:
        samples = self.voice_library.all_samples()
        self.voice_table.setRowCount(len(samples))
        for row, sample in enumerate(samples):
            self.voice_table.setItem(row, 0, QTableWidgetItem(sample.speaker_name))
            self.voice_table.setItem(row, 1, QTableWidgetItem(sample.mood))
            self.voice_table.setItem(row, 2, QTableWidgetItem(sample.language_code))
            self.voice_table.setItem(row, 3, QTableWidgetItem(f"{sample.duration_seconds:.1f}s"))
            self.voice_table.setItem(row, 4, QTableWidgetItem(sample.file_name))
            self.voice_table.setItem(row, 5, QTableWidgetItem(sample.created_at[:19].replace("T", " ")))
            self.voice_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, sample.sample_id)

        speakers = self.voice_library.speakers()
        current_speaker = self.clone_speaker_combo.currentText()
        self.clone_speaker_combo.blockSignals(True)
        self.clone_speaker_combo.clear()
        self.clone_speaker_combo.addItems(speakers)
        if current_speaker and current_speaker in speakers:
            self.clone_speaker_combo.setCurrentText(current_speaker)
        self.clone_speaker_combo.blockSignals(False)
        self._update_clone_moods()

    def _update_clone_moods(self) -> None:
        speaker = self.clone_speaker_combo.currentText()
        moods = self.voice_library.moods_for_speaker(speaker)
        self.clone_mood_combo.blockSignals(True)
        self.clone_mood_combo.clear()
        self.clone_mood_combo.addItems(moods)
        self.clone_mood_combo.blockSignals(False)
        self._update_clone_reference_preview()

    def _update_clone_reference_preview(self) -> None:
        if not self._voice_cloning_supported():
            self.clone_sample_label.setText(
                "Voice cloning is unavailable with the public Voxtral-4B-TTS-2603 checkpoint because the required encoder weights are not included."
            )
            return
        if self.preset_voice_radio.isChecked():
            self.clone_sample_label.setText("Preset mode active")
            return
        speaker = self.clone_speaker_combo.currentText()
        mood = self.clone_mood_combo.currentText().strip().lower()
        sample = self.voice_library.find(speaker, mood)
        if sample is None:
            self.clone_sample_label.setText("No sample available for the selected speaker + mood.")
            return
        self.clone_sample_label.setText(
            f"{sample.file_name} | {sample.language_code} | {sample.duration_seconds:.1f}s | {sample.path}"
        )

    def _create_client(self) -> TTSClient:
        runtime = self.config.runtime
        return TTSClient(
            provider=runtime.provider,
            host=runtime.host,
            port=runtime.port,
            api_base_url=runtime.api_base_url,
            api_key=runtime.resolved_api_key(),
            model=runtime.active_model(),
            timeout=runtime.request_timeout,
            pass_language_hint=runtime.pass_language_hint,
        )

    def _run_worker(self, fn, on_success, on_error, *args, **kwargs) -> None:
        worker = WorkerThread(fn, *args, **kwargs)
        worker.succeeded.connect(on_success)
        worker.failed.connect(on_error)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self.active_workers.append(worker)
        worker.start()

    def _cleanup_worker(self, worker: WorkerThread) -> None:
        if worker in self.active_workers:
            self.active_workers.remove(worker)
        worker.deleteLater()

    def _refresh_server_voices(self) -> None:
        self._persist_config()
        self.generation_status_label.setText("Refreshing voice list...")
        self._run_worker(
            self._create_client().list_server_voices,
            self._on_refresh_voices_success,
            self._on_background_error,
        )

    def _on_refresh_voices_success(self, grouped: dict[str, list[VoiceOption]]) -> None:
        self._apply_voice_groups(grouped)
        total = sum(len(values) for values in grouped.values())
        self.generation_status_label.setText(f"Loaded {total} voices")

    def _generate_audio(self) -> None:
        text = self.text_input.toPlainText().strip()
        if not text:
            self._show_error("Text is required before generating audio.")
            return

        request = self._build_synthesis_request()
        if request is None:
            return

        self._persist_config()
        self.generate_button.setEnabled(False)
        self.generation_status_label.setText("Generating audio...")
        self._run_worker(
            self._perform_generation,
            self._on_generation_success,
            self._on_generation_error,
            request,
        )

    def _build_synthesis_request(self) -> SynthesisRequest | None:
        language_code = self._current_language_code()
        response_format = str(self.output_format_combo.currentData())
        text = self.text_input.toPlainText().strip()
        speed = self.speed_spin.value()
        pitch = self.pitch_spin.value()

        if self.preset_voice_radio.isChecked():
            voice = self._selected_voice_value()
            if not voice:
                self._show_error("Choose a voice or paste a remote voice_id before generating audio.")
                return None
            return SynthesisRequest(
                text=text,
                language_code=language_code,
                response_format=response_format,
                speed=speed,
                pitch_semitones=pitch,
                preset_voice=voice,
            )

        if not self._voice_cloning_supported():
            self._show_error(
                "Voice cloning is not available with the public Voxtral-4B-TTS-2603 checkpoint. Preset voices work, but the open-source checkpoint does not ship the encoder weights required for local cloning."
            )
            return None

        speaker = self.clone_speaker_combo.currentText().strip()
        mood = self.clone_mood_combo.currentText().strip().lower()
        sample = self.voice_library.find(speaker, mood)
        if sample is None:
            self._show_error("Choose a cloned speaker and a mood that has a reference sample.")
            return None
        return SynthesisRequest(
            text=text,
            language_code=language_code,
            response_format=response_format,
            speed=speed,
            pitch_semitones=pitch,
            reference_audio_path=sample.path,
            reference_audio_name=sample.file_name,
        )

    def _perform_generation(self, request: SynthesisRequest) -> SynthesisResult:
        client = self._create_client()
        processor = AudioProcessor(self.config.runtime.ffmpeg_command)
        if request.reference_audio_path:
            request.reference_audio_data_url = processor.prepare_reference_audio_data_url(request.reference_audio_path)

        final_format = request.response_format
        must_post_process = request.needs_post_processing or final_format not in SERVER_RESPONSE_FORMATS
        force_server_format = "wav" if must_post_process else None
        audio_bytes, server_format = client.generate(request, force_server_format=force_server_format)

        final_bytes = audio_bytes
        sample_rate = 24_000
        if must_post_process:
            decoded_audio, sample_rate = processor.decode_audio(audio_bytes, server_format)
            transformed_audio, sample_rate = processor.apply_speed_pitch(
                decoded_audio,
                sample_rate,
                request.speed,
                request.pitch_semitones,
            )
            final_bytes = processor.export(transformed_audio, sample_rate, final_format)

        voice_label = request.preset_voice or (request.reference_audio_name or "cloned_voice")
        safe_voice = voice_label.replace(" ", "_").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.paths.output_dir / f"{timestamp}_{safe_voice}.{final_format}"
        output_path.write_bytes(final_bytes)

        return SynthesisResult(
            audio_bytes=final_bytes,
            output_path=output_path,
            server_format=server_format,
            final_format=final_format,
            sample_rate=sample_rate,
            voice_label=voice_label,
            language_code=request.language_code,
        )

    def _on_generation_success(self, result: SynthesisResult) -> None:
        self.last_result = result
        self.generate_button.setEnabled(True)
        self.save_as_button.setEnabled(True)
        can_preview = result.final_format != "pcm"
        self.play_button.setEnabled(can_preview)
        self.pause_button.setEnabled(can_preview)
        self.stop_button.setEnabled(can_preview)
        self.output_path_label.setText(str(result.output_path))
        self.generation_status_label.setText(
            f"Generated {result.final_format.upper()} | {result.voice_label} | {result.language_code}"
        )
        if can_preview:
            self.audio_player.setSource(QUrl.fromLocalFile(str(result.output_path)))

    def _on_generation_error(self, trace: str) -> None:
        self.generate_button.setEnabled(True)
        self.generation_status_label.setText("Generation failed")
        self._show_error(trace, title="Generation Error")

    def _save_current_output_as(self) -> None:
        if self.last_result is None:
            return
        suggested = self.last_result.output_path.name
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Save audio",
            str(self.paths.output_dir / suggested),
            "Audio files (*.*)",
        )
        if not target:
            return
        Path(target).write_bytes(self.last_result.audio_bytes)
        self.output_path_label.setText(target)

    def _import_sample(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose voice sample",
            str(self.paths.root),
            "Audio files (*.wav *.mp3 *.flac *.ogg *.opus *.m4a *.aac)",
        )
        if not path:
            return
        speaker = self.import_speaker_edit.text().strip()
        mood = self.import_mood_combo.currentText().strip().lower()
        tags = [value.strip() for value in self.import_tags_edit.text().split(",") if value.strip()]
        try:
            sample = self.voice_library.import_sample(
                source_path=Path(path),
                speaker_name=speaker,
                language_code=str(self.import_language_combo.currentData()),
                mood=mood,
                consent_confirmed=self.import_consent_checkbox.isChecked(),
                notes=self.import_notes_edit.toPlainText(),
                tags=tags,
            )
        except Exception as exc:
            self._show_error(str(exc), title="Import Error")
            return

        recommendation = "Ideal range for zero-shot cloning is roughly 3-25 seconds."
        if sample.duration_seconds < 3.0 or sample.duration_seconds > 25.0:
            recommendation = (
                f"Imported, but this sample is {sample.duration_seconds:.1f}s. "
                "Consider a clean 3-25 second reference for stronger results."
            )
        else:
            recommendation = f"Imported {sample.file_name} ({sample.duration_seconds:.1f}s)."

        self.import_status_label.setText(recommendation)
        self.import_consent_checkbox.setChecked(False)
        self._refresh_voice_library_ui()
        self.clone_speaker_combo.setCurrentText(sample.speaker_name)
        self.clone_mood_combo.setCurrentText(sample.mood)
        self.tab_widget.setCurrentIndex(0)

    def _delete_selected_sample(self) -> None:
        row = self.voice_table.currentRow()
        if row < 0:
            self._show_error("Select a sample to delete.")
            return
        cell = self.voice_table.item(row, 0)
        sample_id = cell.data(Qt.ItemDataRole.UserRole) if cell else None
        if not sample_id:
            return
        self.voice_library.delete_sample(str(sample_id))
        self._refresh_voice_library_ui()

    def _start_server(self) -> None:
        self._persist_config()
        if self._is_remote_provider():
            self._show_error("Remote API mode is active. There is no local server to start.")
            return
        self.server_manager.start(self.config.runtime)

    def _check_health(self) -> None:
        self._persist_config()
        healthy, message = self._create_client().check_health()
        self._on_health_changed(healthy, message)

    def _on_server_state_changed(self, state: str) -> None:
        self.runtime_state_label.setText(state.title())

    def _on_health_changed(self, healthy: bool, message: str) -> None:
        self.health_state_label.setText(message)
        self.health_state_label.setProperty("role", "accent" if healthy else "muted")
        self.health_state_label.style().unpolish(self.health_state_label)
        self.health_state_label.style().polish(self.health_state_label)

    def _append_log(self, text: str) -> None:
        self.log_output.appendPlainText(text)

    def _on_background_error(self, trace: str) -> None:
        self.generate_button.setEnabled(True)
        self._show_error(trace)

    def _open_folder(self, path: Path) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _show_error(self, message: str, title: str = "Voxtral Studio") -> None:
        QMessageBox.critical(self, title, message)

    def _voice_cloning_supported(self) -> bool:
        if self._is_remote_provider():
            return True
        model = self.model_edit.text().strip() if hasattr(self, "model_edit") else self.config.runtime.model.strip()
        if not model:
            return True
        normalized = model.replace("\\", "/").rstrip("/").lower()
        if normalized in {"mistralai/voxtral-4b-tts-2603", "voxtral-4b-tts-2603"}:
            return False
        if Path(normalized).name == "voxtral-4b-tts-2603":
            return False
        return True

    def _is_remote_provider(self) -> bool:
        return str(self.provider_combo.currentData()) == REMOTE_PROVIDER

    def _default_local_voice_groups(self) -> dict[str, list[VoiceOption]]:
        grouped = organize_voices_by_language(list(DEFAULT_SERVER_VOICES))
        label_to_code = {label: code for code, label in SUPPORTED_LANGUAGES}
        return {
            language: [
                VoiceOption(
                    label=voice,
                    value=voice,
                    languages=[label_to_code.get(language, "en")],
                    source="local",
                )
                for voice in names
            ]
            for language, names in grouped.items()
        }

    def _selected_voice_option(self) -> VoiceOption | None:
        data = self.voice_combo.currentData()
        if isinstance(data, VoiceOption):
            if self._is_remote_provider():
                current_text = self.voice_combo.currentText().strip()
                if current_text and current_text != data.label:
                    return None
            return data
        return None

    def _selected_voice_value(self) -> str:
        option = self._selected_voice_option()
        if option is not None:
            return option.value.strip()
        return self.voice_combo.currentText().strip()

    def _update_voice_metadata_preview(self) -> None:
        if not hasattr(self, "voice_meta_label"):
            return
        option = self._selected_voice_option()
        if option is None:
            if self._is_remote_provider():
                typed_value = self.voice_combo.currentText().strip()
                if typed_value:
                    self.voice_meta_label.setText(
                        f"Manual remote voice_id: {typed_value}. The language selector still filters your saved voices by their declared languages."
                    )
                else:
                    self.voice_meta_label.setText(
                        "Select a saved remote voice or paste a voice_id. The language selector filters voices by the languages declared on each saved voice."
                    )
            else:
                self.voice_meta_label.setText("Select a voice to see supported languages and metadata.")
            return

        supported_map = {code: label for code, label in SUPPORTED_LANGUAGES}
        language_names = [supported_map.get(code, code) for code in option.languages]
        details = [
            f"Voice ID: {option.value}",
            f"Languages: {', '.join(language_names) if language_names else 'not declared'}",
        ]
        if option.gender:
            details.append(f"Gender: {option.gender}")
        if option.age is not None:
            details.append(f"Age: {option.age}")
        if option.tags:
            details.append(f"Tags: {', '.join(option.tags)}")
        self.voice_meta_label.setText(" | ".join(details))
