from __future__ import annotations

import shlex
import shutil
from pathlib import Path

import httpx
from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal

from voxtral_studio.config import RuntimeSettings, detect_python_candidates, project_root


class ServerManager(QObject):
    log_received = Signal(str)
    state_changed = Signal(str)
    health_changed = Signal(bool, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_output)
        self.process.stateChanged.connect(self._on_state_changed)
        self.process.errorOccurred.connect(self._on_error)
        self.process.finished.connect(self._on_finished)

        self.host = "127.0.0.1"
        self.port = 8000

        self.health_timer = QTimer(self)
        self.health_timer.setInterval(2500)
        self.health_timer.timeout.connect(self.poll_health)
        self.vllm_cli_module = "vllm.entrypoints.cli.main"

    def start(self, settings: RuntimeSettings) -> None:
        if self.is_running:
            return

        self.host = settings.host
        self.port = settings.port
        server_arguments = [
            "serve",
            settings.model,
            "--omni",
            "--host",
            settings.host,
            "--port",
            str(settings.port),
        ]
        if settings.extra_args.strip():
            server_arguments.extend(shlex.split(settings.extra_args, posix=False))

        try:
            executable, arguments, resolution_note = self._resolve_launcher(settings, server_arguments)
        except RuntimeError as exc:
            self.log_received.emit(str(exc))
            self.state_changed.emit("stopped")
            self.health_changed.emit(False, "Runtime not available")
            return

        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONIOENCODING", "utf-8")
        self.process.setProcessEnvironment(environment)
        self.process.setWorkingDirectory(str(project_root()))
        self.process.start(executable, arguments)
        self.health_timer.start()
        if resolution_note:
            self.log_received.emit(resolution_note)
        self.log_received.emit(f"$ {executable} {' '.join(arguments)}")

    def stop(self) -> None:
        if not self.is_running:
            return
        self.process.terminate()
        if not self.process.waitForFinished(5000):
            self.process.kill()
        self.health_timer.stop()

    @property
    def is_running(self) -> bool:
        return self.process.state() != QProcess.ProcessState.NotRunning

    def poll_health(self) -> None:
        try:
            response = httpx.get(
                f"http://{self.host}:{self.port}/health",
                timeout=1.0,
            )
            healthy = response.status_code == 200
            self.health_changed.emit(healthy, "Server ready" if healthy else f"Health: {response.status_code}")
        except Exception as exc:
            self.health_changed.emit(False, str(exc))

    def _on_output(self) -> None:
        raw = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if raw.strip():
            self.log_received.emit(raw.rstrip())

    def _on_state_changed(self, state: QProcess.ProcessState) -> None:
        mapping = {
            QProcess.ProcessState.NotRunning: "stopped",
            QProcess.ProcessState.Starting: "starting",
            QProcess.ProcessState.Running: "running",
        }
        self.state_changed.emit(mapping.get(state, "unknown"))

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self.log_received.emit(
                "Process error: FailedToStart. Su Windows di solito significa comando non trovato oppure runtime non installato."
            )
            self.log_received.emit(
                "Controlla `Runtime > Command` oppure installa il runtime con `scripts\\setup_and_run.ps1 -InstallRuntime -SkipLaunch`."
            )
        else:
            self.log_received.emit(f"Process error: {error}")

    def _on_finished(self) -> None:
        self.health_timer.stop()
        self.state_changed.emit("stopped")
        self.health_changed.emit(False, "Server stopped")

    def _resolve_launcher(self, settings: RuntimeSettings, server_arguments: list[str]) -> tuple[str, list[str], str]:
        command = settings.server_command.strip()
        if not command or command.lower() == "auto":
            return self._auto_launcher(server_arguments)

        if command.lower() in {"vllm", "vllm.exe"}:
            resolved = shutil.which(command)
            if resolved:
                return resolved, server_arguments, "Using vllm executable from PATH."
            return self._python_module_launcher(server_arguments, requested_command=command)

        candidate_path = Path(command)
        if candidate_path.exists():
            if candidate_path.name.lower().startswith("python"):
                return str(candidate_path), ["-m", self.vllm_cli_module, *server_arguments], (
                    f"Using configured Python interpreter with `-m {self.vllm_cli_module}`."
                )
            return str(candidate_path), server_arguments, "Using configured executable path."

        resolved = shutil.which(command)
        if resolved:
            if Path(resolved).name.lower().startswith("python"):
                return resolved, ["-m", self.vllm_cli_module, *server_arguments], (
                    f"Using configured Python command with `-m {self.vllm_cli_module}`."
                )
            return resolved, server_arguments, "Using configured command from PATH."

        return self._python_module_launcher(server_arguments, requested_command=command)

    def _auto_launcher(self, server_arguments: list[str]) -> tuple[str, list[str], str]:
        resolved_vllm = shutil.which("vllm")
        if resolved_vllm:
            return resolved_vllm, server_arguments, "Auto-detected `vllm` executable in PATH."
        return self._python_module_launcher(server_arguments, requested_command="auto")

    def _python_module_launcher(self, server_arguments: list[str], requested_command: str) -> tuple[str, list[str], str]:
        for python_path in detect_python_candidates(project_root()):
            if not python_path.exists():
                continue
            if self._python_has_vllm(python_path):
                return str(python_path), ["-m", self.vllm_cli_module, *server_arguments], (
                    f"`{requested_command}` non trovato come eseguibile; uso {python_path.name} -m {self.vllm_cli_module}."
                )

        venv_python = project_root() / ".venv" / "Scripts" / "python.exe"
        raise RuntimeError(
            "Runtime Voxtral non trovato. Nessun comando `vllm` disponibile e il virtualenv del progetto non contiene il modulo `vllm`.\n"
            f"Python rilevato nel progetto: {venv_python}\n"
            "Installa il runtime con `scripts\\setup_and_run.ps1 -InstallRuntime -SkipLaunch` "
            "oppure in manuale con `.\\.venv\\Scripts\\python.exe -m pip install -U vllm` "
            "e `.\\.venv\\Scripts\\python.exe -m pip install git+https://github.com/vllm-project/vllm-omni.git --upgrade`."
        )

    def _python_has_vllm(self, python_path: Path) -> bool:
        candidates: list[Path] = []
        if python_path.parent.name.lower() == "scripts":
            candidates.append(python_path.parents[1] / "Lib" / "site-packages")
        candidates.append(python_path.parent / "Lib" / "site-packages")
        for site_packages in candidates:
            if (site_packages / "vllm").exists():
                return True
        return False
