"""Portuguese desktop onboarding, local collection, evaluation and explicit activation."""
import json
import os
from pathlib import Path
import threading
import time
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QShortcut, QKeySequence, QPalette, QColor
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QTabWidget, QFormLayout, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
                               QFileDialog, QMessageBox, QPlainTextEdit, QTableWidget, QTableWidgetItem,
                               QHeaderView, QProgressBar)
from platformdirs import user_data_dir
from .camera import Camera
from .dataset import Session, Clip, DEFAULT_LABELS, label_valid
from .model import Model, train
from .profile import Profile
from .runtime import Runtime
from .calibration import Calibration
from .platforms import monitors, diagnostics, is_wayland
from .input_worker import InputSupervisor, MAX_AGE
from .safety import ACTIONS
from .storage import write_json

TARGETS = [(.1, .1), (.9, .1), (.5, .5), (.1, .9), (.9, .9)]


def button(text, callback):
    b = QPushButton(text)
    b.clicked.connect(callback)
    b.setMinimumHeight(32)
    return b


def decimal(value, low, high, step=.05):
    s = QDoubleSpinBox()
    s.setRange(low, high)
    s.setSingleStep(step)
    s.setDecimals(2)
    s.setValue(value)
    return s


def tab(tabs, title):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(12)
    tabs.addTab(widget, title)
    return layout


class Window(QMainWindow):
    def __init__(self, data_dir=None):
        super().__init__()
        self.setWindowTitle("Mouse Invisível · câmera local e gestos treinados")
        self.resize(1050, 830)
        self.data_dir = Path(data_dir or os.environ.get("MOUSE_DATA_DIR") or user_data_dir("MouseInvisivel"))
        self.profile = Profile()
        self.model, self.camera, self.input = None, None, None
        self.runtime = Runtime(self.profile)
        self.active = False
        self.last_sequence, self.last_packet = -1, None
        self.session = Session("pessoa-local")
        self.sessions = []
        self.recording = None
        self.sequence_recording = None
        self.cal_points = []
        self.cal_target = None
        self.training_thread, self.training_result = None, None
        self.training_lock = threading.Lock()
        self.screens = []
        self.display_layout = self.display_fingerprint()
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        title = QLabel("Mouse Invisível")
        title.setStyleSheet("font-size:28px;font-weight:700;")
        outer.addWidget(title)
        outer.addWidget(QLabel("Treine seus gestos. Todos os frames ficam neste computador. Nenhum vídeo é gravado."))
        top = QHBoxLayout()
        self.state = QLabel("PAUSADO · prévia sem entrada")
        self.state.setStyleSheet("font-weight:bold;color:#e8ba55;")
        top.addWidget(self.state, 1)
        self.pause_button = button("PARAR AGORA · Esc nesta janela" if is_wayland() else "PARAR AGORA · Esc", self.pause)
        self.pause_button.setStyleSheet("background:#9c3038;color:white;font-weight:bold;padding:6px 18px;")
        top.addWidget(self.pause_button)
        outer.addLayout(top)
        tabs = QTabWidget()
        outer.addWidget(tabs)
        self._control_tab(tabs)
        self._collect_tab(tabs)
        self._train_tab(tabs)
        self._profile_tab(tabs)
        self._diagnostics_tab(tabs)
        self.status = QLabel("1. Selecione os landmarks .task. 2. Abra a prévia. 3. Grave sessões e treine.")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        self.esc = QShortcut(QKeySequence("Esc"), self)
        self.esc.activated.connect(self.pause)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(30)
        self.shutdown_timer = QTimer(self)
        self.shutdown_timer.timeout.connect(self.finish_shutdown)
        self.setStyleSheet(
            "QWidget{color:#e9edf2;background-color:#20262f;}"
            "QLabel{font-size:13px;background:transparent;}"
            "QTabWidget::pane{border:1px solid #48515c;}"
            "QTabBar::tab{background:#394654;color:#e9edf2;padding:8px 12px;}"
            "QTabBar::tab:selected{background:#276f7e;}"
            "QPushButton{background:#394654;color:#e9edf2;padding:5px 10px;border:1px solid #637182;border-radius:4px;}"
            "QPushButton:hover{background:#4a5969;}"
            "QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QPlainTextEdit,QTableWidget{"
            "background:#151b23;color:#e9edf2;padding:5px;border:1px solid #48515c;}")
        palette = QPalette()
        for role, color in [(QPalette.Window, "#20262f"), (QPalette.WindowText, "#e9edf2"),
                            (QPalette.Base, "#151b23"), (QPalette.AlternateBase, "#29313b"),
                            (QPalette.Text, "#e9edf2"), (QPalette.Button, "#394654"),
                            (QPalette.ButtonText, "#e9edf2"), (QPalette.Highlight, "#338fa0")]:
            palette.setColor(role, QColor(color))
        self.setPalette(palette)

    def _control_tab(self, tabs):
        layout = tab(tabs, "1 · Prévia e controle")
        form = QFormLayout()
        self.task_path = QLineEdit()
        task_row = QHBoxLayout()
        task_row.addWidget(self.task_path, 1)
        task_row.addWidget(button("Selecionar .task", self.choose_task))
        form.addRow("Landmarks MediaPipe (arquivo local)", task_row)
        self.camera_index = QSpinBox()
        self.camera_index.setRange(0, 32)
        self.camera_index.valueChanged.connect(self.camera_changed)
        form.addRow("Câmera", self.camera_index)
        self.hand = QComboBox()
        self.hand.addItems(["Right", "Left"])
        self.hand.currentTextChanged.connect(self.hand_changed)
        form.addRow("Mão (confira na prévia espelhada)", self.hand)
        layout.addLayout(form)
        row = QHBoxLayout()
        row.addWidget(button("Abrir / reiniciar prévia", self.start_camera))
        row.addWidget(button("Fechar câmera", self.stop_camera))
        row.addWidget(button("Carregar modelo treinado JSON", self.load_model))
        layout.addLayout(row)
        self.video = QLabel("Câmera fechada · sem gravação de vídeo")
        self.video.setAlignment(Qt.AlignCenter)
        self.video.setMinimumHeight(250)
        self.video.setStyleSheet("background:#10151c;border-radius:8px;")
        layout.addWidget(self.video, 1)
        self.prediction = QLabel("Modelo pessoal ainda não carregado")
        layout.addWidget(self.prediction)
        row = QHBoxLayout()
        row.addWidget(button("Autorizar portal / testar parada global" if is_wayland()
                             else "Verificar entrada / testar Esc global", self.prepare_input))
        self.activate_button = button("Ativar controle", self.activate)
        row.addWidget(self.activate_button)
        self.stop_hint = QLabel("Parada global: autorize/verifique a entrada e teste o atalho antes de ativar.")
        self.stop_hint.setWordWrap(True)
        layout.addWidget(self.stop_hint)
        layout.addLayout(row)
        layout.addWidget(QLabel("Começa pausado. Após ativar: mostre neutral para armar; cada ação exige novo neutral.\n"
                                "Ative somente depois de conferir as previsões, calibrar e testar a parada global."))

    def _collect_tab(self, tabs):
        layout = tab(tabs, "2 · Exemplos locais")
        layout.addWidget(QLabel("Grave todos os rótulos em pelo menos duas sessões independentes. Inclua movimentos\n"
                                "neutros, transições, poses parciais e gestos parecidos em confusing. Coleta sempre pausa entrada."))
        form = QFormLayout()
        self.person = QLineEdit("pessoa-local")
        form.addRow("Identificador da pessoa (opcionalmente pseudônimo)", self.person)
        self.label = QComboBox()
        self.label.setEditable(True)
        self.label.addItems(DEFAULT_LABELS)
        form.addRow("Rótulo do próximo exemplo", self.label)
        self.duration = QSpinBox()
        self.duration.setRange(2, 15)
        self.duration.setValue(3)
        form.addRow("Duração (segundos), após 1 s de preparação", self.duration)
        layout.addLayout(form)
        row = QHBoxLayout()
        row.addWidget(button("Gravar exemplo de landmarks", self.record_clip))
        row.addWidget(button("Cancelar exemplo", self.cancel_recording))
        row.addWidget(button("Excluir último exemplo", self.delete_clip))
        layout.addLayout(row)
        sequence_row = QHBoxLayout()
        sequence_row.addWidget(button("Iniciar sequência contínua rotulada", self.start_sequence))
        sequence_row.addWidget(button("Encerrar sequência", self.end_sequence))
        layout.addLayout(sequence_row)
        layout.addWidget(QLabel("Sequência: mude o rótulo explicitamente ao mudar o gesto, incluindo neutral entre ações.\n"
                                "Mantenha cada rótulo por ≥2 s. Landmarks contínuos permitem avaliar episódios completos."))
        self.capture_progress = QProgressBar()
        self.capture_progress.setRange(0, 100)
        layout.addWidget(self.capture_progress)
        self.clips_text = QPlainTextEdit()
        self.clips_text.setReadOnly(True)
        layout.addWidget(self.clips_text, 1)
        row = QHBoxLayout()
        row.addWidget(button("Salvar / exportar sessão JSON", self.save_session))
        row.addWidget(button("Nova sessão independente", self.new_session))
        row.addWidget(button("Excluir sessão salva…", self.delete_session))
        layout.addLayout(row)
        self.refresh_clips()

    def _train_tab(self, tabs):
        layout = tab(tabs, "3 · Treinar e avaliar")
        layout.addWidget(QLabel("Separe uma sessão inteira ou uma pessoa para avaliação antes de treinar.\n"
                                "Logística e Gaussian NB são comparadas; a escolha não muda automaticamente pelos resultados."))
        row = QHBoxLayout()
        row.addWidget(button("Adicionar sessões JSON", self.add_sessions))
        row.addWidget(button("Limpar seleção de sessões", self.clear_sessions))
        layout.addLayout(row)
        self.session_table = QTableWidget(0, 3)
        self.session_table.setHorizontalHeaderLabels(["Sessão", "Pessoa", "Exemplos"])
        self.session_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.session_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.session_table.setMaximumHeight(140)
        layout.addWidget(self.session_table)
        form = QFormLayout()
        self.split = QComboBox()
        self.split.addItems(["session", "person"])
        self.split.currentTextChanged.connect(self.refresh_holdouts)
        form.addRow("Unidade de separação", self.split)
        self.holdout = QComboBox()
        form.addRow("Reservar para avaliação", self.holdout)
        self.classifier = QComboBox()
        self.classifier.addItems(["logistic", "gaussian_nb"])
        form.addRow("Classificador escolhido antes da avaliação", self.classifier)
        layout.addLayout(form)
        row = QHBoxLayout()
        self.train_button = button("Treinar · avaliar · carregar na prévia", self.train_model)
        row.addWidget(self.train_button)
        row.addWidget(button("Salvar modelo JSON", self.save_model))
        row.addWidget(button("Exportar avaliação JSON", self.export_report))
        layout.addLayout(row)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        layout.addWidget(self.report, 1)

    def _profile_tab(self, tabs):
        layout = tab(tabs, "4 · Perfil e calibração")
        form = QFormLayout()
        self.profile_name = QLineEdit(self.profile.name)
        form.addRow("Nome do perfil", self.profile_name)
        self.monitor = QComboBox()
        form.addRow("Monitor de destino", self.monitor)
        self.sensitivity = decimal(1., .1, 3.)
        self.smoothing = decimal(.08, 0., 1., .01)
        self.confidence = decimal(.8, .5, 1.)
        self.margin = decimal(.15, 0., 1.)
        self.dwell = decimal(.15, .05, 1.)
        self.scroll_step = QSpinBox()
        self.scroll_step.setRange(1, 20)
        self.scroll_step.setValue(3)
        for text, widget in [("Sensibilidade", self.sensitivity), ("Suavização (s)", self.smoothing),
                             ("Confiança mínima", self.confidence), ("Margem sobre 2º rótulo", self.margin),
                             ("Estabilidade mínima (s)", self.dwell), ("Passos de rolagem por gesto", self.scroll_step)]:
            form.addRow(text, widget)
            widget.valueChanged.connect(self.apply_profile)
        layout.addLayout(form)
        self.monitor.currentIndexChanged.connect(self.monitor_changed)
        self.mapping = QTableWidget(0, 2)
        self.mapping.setHorizontalHeaderLabels(["Rótulo treinado", "Ação"])
        self.mapping.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.mapping, 1)
        self.refresh_mapping()
        self.cal_label = QLabel("Cursor não calibrado. Prévia e coleta disponíveis.")
        self.cal_label.setWordWrap(True)
        layout.addWidget(self.cal_label)
        row = QHBoxLayout()
        row.addWidget(button("Iniciar calibração em 5 pontos", self.start_calibration))
        row.addWidget(button("Capturar ponto após 1 s", self.capture_calibration))
        row.addWidget(button("Cancelar calibração", self.cancel_calibration))
        layout.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(button("Salvar perfil JSON", self.save_profile))
        row.addWidget(button("Carregar perfil JSON", self.load_profile))
        layout.addLayout(row)
        self.refresh_monitors()

    def _diagnostics_tab(self, tabs):
        layout = tab(tabs, "5 · Diagnóstico")
        layout.addWidget(QLabel("macOS: Câmera + Acessibilidade, e Monitoramento de Entrada para Esc se necessário.\n"
                                "Windows: desktop normal; aplicações elevadas podem rejeitar entrada.\n"
                                "Linux X11: XTest. Wayland: RemoteDesktop + GlobalShortcuts com consentimento explícito.\n"
                                "Sway/wlr pode não oferecer esses portais: consulte o diagnóstico; sem fallback XWayland.\n"
                                "Nenhuma permissão é concedida automaticamente."))
        row = QHBoxLayout()
        row.addWidget(button("Atualizar diagnóstico", self.refresh_diagnostics))
        row.addWidget(button("Exportar diagnóstico JSON", self.export_diagnostics))
        layout.addLayout(row)
        self.diagnostic_text = QPlainTextEdit()
        self.diagnostic_text.setReadOnly(True)
        layout.addWidget(self.diagnostic_text, 1)
        layout.addWidget(QLabel("Arquivos .task e licenças: consulte docs/LICENSES.md e a página oficial Hand Landmarker.\n"
                                "Nenhum peso é baixado pela aplicação. CI/build não provam câmera, latência ou entrada física."))
        self.refresh_diagnostics()

    def message(self, text):
        self.status.setText(text)

    def error(self, error):
        self.pause()
        QMessageBox.warning(self, "Mouse Invisível", str(error))

    def pause(self, *_):
        self.active = False
        if self.input:
            self.input.pause()
        self.runtime.reset()
        self.state.setText("PAUSADO · prévia sem entrada")
        self.state.setStyleSheet("font-weight:bold;color:#e8ba55;")

    def choose_task(self):
        self.pause()
        path, _ = QFileDialog.getOpenFileName(self, "Landmarks licenciados", "", "MediaPipe (*.task)")
        if path:
            self.stop_camera()
            self.task_path.setText(path)

    def camera_changed(self, *_):
        if hasattr(self, "cal_label"):
            self.profile.calibration = None
            self.stop_camera()
            self.cal_label.setText("Câmera mudou: recalibre o cursor e confira o modelo na prévia.")

    def hand_changed(self, *_):
        self.pause()
        self.profile.calibration = None
        self.cal_label.setText("Mão mudou: recalibre e use sessões/modelo correspondentes.")
        if self.camera:
            self.stop_camera()
            self.message("Mão alterada; reabra a prévia e confira a classificação da mão.")

    def start_camera(self):
        if not self.stop_camera():
            return
        try:
            self.camera = Camera(self.camera_index.value(), self.task_path.text(), self.hand.currentText())
            self.last_sequence, self.last_packet = -1, None
            self.camera.start()
            self.message("Abrindo câmera local… nenhuma entrada está ativa.")
        except Exception as e:
            self.camera = None
            self.error(e)

    def stop_camera(self):
        self.pause()
        self.cancel_recording()
        self.cancel_calibration()
        if self.camera:
            if not self.camera.close():
                self.message("Driver de câmera não respondeu. Entrada pausada; reinicie o app antes de reconectar.")
                return False
            self.camera = None
        self.last_packet = None
        self.video.setText("Câmera fechada · sem gravação de vídeo")
        return True

    def current_frame(self):
        packet = self.last_packet
        if (packet is None or packet.landmark is None or time.monotonic() - packet.timestamp > MAX_AGE):
            raise ValueError("Abra a prévia e mantenha a mão selecionada visível, sem perda de tracking")
        return packet.landmark

    def prepare_input(self):
        self.pause()
        if self.input:
            if not self.input.close():
                self.error("Processo de entrada não respondeu; reinicie antes de testar novamente")
                return
        self.input = InputSupervisor()
        self.message("Verificando backend. Wayland abre diálogos de consentimento para ponteiro/monitores e parada. "
                     "Confira o atalho global informado e teste-o antes de ativar; nenhum pixel de tela é lido.")

    def activate(self):
        try:
            if self.recording or self.sequence_recording or self.cal_target is not None or (self.training_thread and self.training_thread.is_alive()):
                raise ValueError("Finalize coleta, calibração e treinamento antes de ativar")
            self.current_frame()
            self.apply_profile()
            if not self.model or not self.profile.calibration:
                raise ValueError("Carregue/treine um modelo e calibre o cursor antes de ativar")
            self.refresh_monitors()
            if not 0 <= self.monitor.currentIndex() < len(self.screens):
                raise ValueError("Nenhum monitor nativo selecionado")
            if not self.input:
                raise ValueError("Autorize/verifique a entrada e teste a parada global primeiro")
            self.input.activate()
            self.active = True
            self.runtime.reset()
            self.state.setText("ATIVO · aguardando neutral")
            self.state.setStyleSheet("font-weight:bold;color:#6be1b0;")
        except Exception as e:
            self.error(e)

    def apply_profile(self, *_):
        self.pause()
        p = self.profile
        p.name = self.profile_name.text().strip() or "Meu perfil"
        p.hand, p.camera, p.monitor = self.hand.currentText(), self.camera_index.value(), self.monitor.currentIndex()
        for k in ("sensitivity", "smoothing", "confidence", "margin", "dwell", "scroll_step"):
            setattr(p, k, getattr(self, k).value())
        p.mapping = {self.mapping.item(i, 0).text(): self.mapping.cellWidget(i, 1).currentText()
                     for i in range(self.mapping.rowCount())}
        self.runtime = Runtime(p, self.model)

    def refresh_mapping(self):
        labels = sorted(set(self.profile.mapping) | set(self.model.labels if self.model else DEFAULT_LABELS))
        self.mapping.setRowCount(len(labels))
        for i, label in enumerate(labels):
            item = QTableWidgetItem(label)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.mapping.setItem(i, 0, item)
            choice = QComboBox()
            choice.addItems(ACTIONS)
            choice.setCurrentText(self.profile.mapping.get(label, "none"))
            if label in ("neutral", "confusing"):
                choice.setCurrentText("none")
                choice.setEnabled(False)
            choice.currentTextChanged.connect(self.apply_profile)
            self.mapping.setCellWidget(i, 1, choice)

    def record_clip(self):
        self.pause()
        try:
            self.current_frame()
            label = self.label.currentText().strip()
            if not label_valid(label):
                raise ValueError("Rótulo: até 48 letras/números, _ ou -")
            if self.recording or self.sequence_recording:
                raise ValueError("Finalize ou cancele a coleta atual")
            if self.cal_target is not None:
                raise ValueError("Finalize a calibração primeiro")
            start = time.monotonic() + 1.
            self.recording = {"label": label, "start": start, "end": start + self.duration.value(), "frames": []}
            self.message("Prepare o gesto. Coleta de landmarks começa em 1 s, sem entrada.")
        except Exception as e:
            self.error(e)

    def start_sequence(self):
        self.pause()
        try:
            self.current_frame()
            if self.recording or self.sequence_recording or self.cal_target is not None:
                raise ValueError("Finalize a coleta/calibração atual primeiro")
            label = self.label.currentText().strip()
            if not label_valid(label):
                raise ValueError("Escolha um rótulo válido")
            self.sequence_recording = {"label": label, "frames": []}
            self.message("Sequência contínua: mude o rótulo ao mudar gesto. Inclua neutral entre ações; nenhum input.")
        except Exception as e:
            self.error(e)

    def append_sequence_clip(self):
        r = self.sequence_recording
        if r and r["frames"]:
            try:
                from .features import windows
                clip = Clip(r["label"], r["frames"])
                if len(list(windows(clip.frames))) < 5:
                    raise ValueError("Segmento curto demais; mantenha o próximo rótulo por ≥2 s")
                self.session.clips.append(clip)
                self.refresh_clips()
            except ValueError as e:
                self.message(str(e))

    def end_sequence(self):
        self.pause()
        self.append_sequence_clip()
        self.sequence_recording = None
        self.message("Sequência encerrada em memória; salve a sessão JSON.")

    def cancel_recording(self):
        self.recording = None
        self.sequence_recording = None
        self.capture_progress.setValue(0)

    def refresh_clips(self):
        self.clips_text.setPlainText(f"Sessão {self.session.id}\n" + "\n".join(
            f"{i+1}. {c.label} · {len(c.frames)} frames · {c.frames[-1].timestamp-c.frames[0].timestamp:.1f} s"
            for i, c in enumerate(self.session.clips)))

    def delete_clip(self):
        self.pause()
        if self.session.clips:
            self.session.clips.pop()
            self.refresh_clips()

    def save_session(self):
        self.pause()
        if not self.session.clips:
            self.error("Grave exemplos antes de salvar")
            return
        self.session.person = self.person.text().strip()[:128] or "pessoa-local"
        path, _ = QFileDialog.getSaveFileName(self, "Salvar landmarks locais", str(
            self.data_dir / "sessions" / f"{self.session.id}.json"), "JSON (*.json)")
        if path:
            try:
                self.session.save(path)
                self.message(f"Sessão salva localmente: {path}")
            except Exception as e:
                self.error(e)

    def new_session(self):
        self.pause()
        self.cancel_recording()
        if self.session.clips:
            if QMessageBox.question(self, "Nova sessão", "Os exemplos em memória serão descartados. Já exportou?") != QMessageBox.Yes:
                return
        self.session = Session(self.person.text().strip()[:128] or "pessoa-local")
        self.refresh_clips()

    def delete_session(self):
        self.pause()
        path, _ = QFileDialog.getOpenFileName(self, "Excluir sessão de landmarks", str(self.data_dir), "JSON (*.json)")
        if not path:
            return
        try:
            session = Session.load(path)
            if QMessageBox.question(self, "Excluir dados", f"Excluir permanentemente esta sessão?\n{path}") == QMessageBox.Yes:
                Path(path).unlink()
                self.sessions = [s for s in self.sessions if s.id != session.id]
                self.refresh_sessions()
                self.message("Sessão excluída. Modelos já treinados devem ser excluídos/re-treinados separadamente.")
        except Exception as e:
            self.error(e)

    def add_sessions(self):
        self.pause()
        paths, _ = QFileDialog.getOpenFileNames(self, "Sessões para treino/avaliação", str(self.data_dir), "JSON (*.json)")
        try:
            added = [Session.load(p) for p in paths]
            ids = {s.id for s in self.sessions}
            for s in added:
                if s.id not in ids:
                    self.sessions.append(s)
                    ids.add(s.id)
            self.refresh_sessions()
        except Exception as e:
            self.error(e)

    def clear_sessions(self):
        self.pause()
        self.sessions.clear()
        self.refresh_sessions()

    def refresh_sessions(self):
        self.session_table.setRowCount(len(self.sessions))
        for i, s in enumerate(self.sessions):
            for j, text in enumerate((s.id, s.person, str(len(s.clips)))):
                self.session_table.setItem(i, j, QTableWidgetItem(text))
        self.refresh_holdouts()

    def refresh_holdouts(self, *_):
        self.holdout.clear()
        if self.split.currentText() == "person":
            self.holdout.addItems(sorted({s.person for s in self.sessions}))
        else:
            for s in self.sessions:
                self.holdout.addItem(f"{s.id[:8]} · {s.person}", s.id)
        if self.holdout.count():
            self.holdout.setCurrentIndex(self.holdout.count()-1)

    def train_model(self):
        self.pause()
        if self.training_thread and self.training_thread.is_alive():
            return
        self.apply_profile()
        holdout = self.holdout.currentData() if self.split.currentText() == "session" else self.holdout.currentText()
        if not holdout:
            self.error("Adicione pelo menos duas sessões e selecione a avaliação")
            return
        sessions = list(self.sessions)
        kind, by_person = self.classifier.currentText(), self.split.currentText() == "person"
        confidence, margin, dwell = self.profile.confidence, self.profile.margin, self.profile.dwell
        mapping = self.profile.mapping.copy()
        self.train_button.setEnabled(False)
        self.report.setPlainText("Treinando localmente… nenhuma entrada. Não há dados enviados para rede.")
        def work():
            try:
                result = train(sessions, [holdout], kind, by_person, confidence, margin, dwell, mapping)
            except Exception as e:
                result = e
            with self.training_lock:
                self.training_result = result
        self.training_thread = threading.Thread(target=work, name="LocalTraining", daemon=True)
        self.training_thread.start()

    def set_model(self, model):
        self.pause()
        self.model = model
        self.runtime = Runtime(self.profile, model)
        self.refresh_mapping()
        self.report.setPlainText(json.dumps(model.report, indent=2, ensure_ascii=False))
        self.message("Modelo pessoal carregado na prévia. Confira previsões e calibre antes de ativar.")

    def load_model(self):
        self.pause()
        path, _ = QFileDialog.getOpenFileName(self, "Modelo pessoal JSON", str(self.data_dir), "JSON (*.json)")
        if path:
            try:
                self.set_model(Model.load(path))
            except Exception as e:
                self.error(e)

    def save_model(self):
        self.pause()
        if not self.model:
            self.error("Treine ou carregue um modelo primeiro")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salvar modelo numérico", str(self.data_dir / "gesture-model.json"), "JSON (*.json)")
        if path:
            try:
                self.model.save(path)
                self.message(f"Modelo salvo: {path}. Carregar modelo JSON testa a recarga.")
            except Exception as e:
                self.error(e)

    def export_report(self):
        self.pause()
        if not self.model:
            self.error("Não existe avaliação para exportar")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar avaliação", str(self.data_dir / "evaluation.json"), "JSON (*.json)")
        if path:
            try:
                write_json(path, self.model.report)
            except Exception as e:
                self.error(e)

    def refresh_monitors(self):
        selected = self.monitor.currentIndex()
        self.monitor.blockSignals(True)
        self.monitor.clear()
        try:
            self.screens = getattr(self.input, "screens", []) if is_wayland() and self.input else monitors()
        except Exception:
            self.screens = []
        for m in self.screens:
            self.monitor.addItem(f"{m.name}: {m.width}×{m.height} @ ({m.x},{m.y})")
        if not self.screens:
            self.monitor.addItem("Monitor indisponível; prévia/treino apenas")
        self.monitor.setCurrentIndex(max(0, min(selected, self.monitor.count()-1)))
        self.monitor.blockSignals(False)

    def monitor_changed(self, *_):
        self.pause()

    def start_calibration(self):
        self.pause()
        try:
            self.current_frame()
            self.cancel_recording()
            self.cal_points = []
            self.cal_target = 0
            self.show_target()
        except Exception as e:
            self.error(e)

    def show_target(self):
        index = len(self.cal_points)
        target = TARGETS[index]
        self.cal_label.setText(f"Ponto {index+1}/5: aponte o indicador para ({target[0]*100:.0f}%, {target[1]*100:.0f}%) "
                               "da área de movimento confortável. Clique Capturar e mantenha por 1 s.")
        # Preview overlay targets are camera-relative guidance, not OS cursor injection.
        self.message("Calibração sem entrada: superior esquerdo → superior direito → centro → inferior esquerdo → inferior direito.")

    def capture_calibration(self):
        self.pause()
        if self.cal_target is None:
            self.error("Inicie a calibração primeiro")
            return
        self.cal_target = time.monotonic() + 1.
        self.message("Mantenha o indicador no ponto solicitado por 1 s…")

    def cancel_calibration(self):
        self.cal_target = None
        self.cal_points = []

    def save_profile(self):
        self.apply_profile()
        path, _ = QFileDialog.getSaveFileName(self, "Salvar perfil", str(self.data_dir / "profiles" / "profile.json"), "JSON (*.json)")
        if path:
            try:
                self.profile.save(path)
                self.message(f"Perfil/calibração salvos: {path}")
            except Exception as e:
                self.error(e)

    def load_profile(self):
        self.pause()
        path, _ = QFileDialog.getOpenFileName(self, "Carregar perfil", str(self.data_dir), "JSON (*.json)")
        if path:
            try:
                profile = Profile.load(path)
                if not self.stop_camera():
                    raise ValueError("Driver bloqueado; reinicie o app para mudar perfil")
                # Set widgets before restoring calibration, since handedness changes invalidate old calibration.
                self.hand.setCurrentText(profile.hand)
                self.profile_name.setText(profile.name)
                self.camera_index.setValue(profile.camera)
                for k in ("sensitivity", "smoothing", "confidence", "margin", "dwell", "scroll_step"):
                    getattr(self, k).setValue(getattr(profile, k))
                self.monitor.setCurrentIndex(min(profile.monitor, self.monitor.count()-1))
                self.profile = profile
                self.runtime = Runtime(profile, self.model)
                self.refresh_mapping()
                self.cal_label.setText("Calibração carregada; confira o monitor e a prévia." if profile.calibration else "Cursor não calibrado")
                self.message("Perfil carregado pausado. Reabra a câmera e confira modelo, mão e monitor.")
            except Exception as e:
                self.error(e)

    def refresh_diagnostics(self):
        self.diagnostic_text.setPlainText(json.dumps(diagnostics(), indent=2, ensure_ascii=False))

    def export_diagnostics(self):
        path, _ = QFileDialog.getSaveFileName(self, "Diagnóstico", str(self.data_dir / "diagnostics.json"), "JSON (*.json)")
        if path:
            try:
                write_json(path, diagnostics())
            except Exception as e:
                self.error(e)

    def tick(self):
        layout = self.display_fingerprint()
        if is_wayland() and layout != self.display_layout:
            self.pause()
            self.profile.calibration = None
            self.cal_label.setText("Layout/DPI mudou: reautorize o portal, confira o monitor e recalibre.")
            if self.input:
                self.input.ready = False
                self.input.stop.set()
            self.message("Pausado por mudança de layout/DPI Wayland. Reautorize a entrada antes de ativar.")
        self.display_layout = layout
        if self.input:
            for kind, detail in self.input.poll():
                if kind == "monitors":
                    self.refresh_monitors()
                else:
                    self.message(detail)
                if kind == "ready":
                    self.stop_hint.setText(detail)
                if kind in ("paused", "stop", "error"):
                    self.pause()
            if self.active and (self.input.inhibit.is_set() or not self.input.process.is_alive()):
                self.pause()
        with self.training_lock:
            result = self.training_result
            self.training_result = None
        if result is not None:
            self.train_button.setEnabled(True)
            if isinstance(result, Exception):
                self.error(result)
            else:
                self.set_model(result)
        packet = self.camera.latest() if self.camera else None
        if packet is None or packet.sequence == self.last_sequence:
            if packet and time.monotonic() - packet.timestamp > MAX_AGE:
                if self.recording or self.sequence_recording:
                    self.cancel_recording()
                    self.message("Exemplo descartado: a câmera parou de entregar frames recentes.")
                if self.cal_target is not None:
                    self.cancel_calibration()
            if self.active and (not packet or time.monotonic() - packet.timestamp > MAX_AGE):
                self.pause()
                self.message("Pausado: câmera/tracking sem frames recentes")
            return
        self.last_sequence, self.last_packet = packet.sequence, packet
        if packet.rgb is None:
            self.pause()
            self.cancel_recording()
            self.cancel_calibration()
            self.message(packet.detail)
            return
        rgb = packet.rgb
        image = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888).copy()
        self.video.setPixmap(QPixmap.fromImage(image).scaled(self.video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        frame = packet.landmark
        if self.sequence_recording:
            current_label = self.label.currentText().strip()
            if frame is None or time.monotonic() - packet.timestamp > MAX_AGE or not label_valid(current_label):
                self.cancel_recording()
                self.message("Sequência interrompida por tracking/atraso/rótulo inválido; segmento atual descartado.")
            else:
                if current_label != self.sequence_recording["label"]:
                    self.append_sequence_clip()
                    self.sequence_recording = {"label": current_label, "frames": []}
                self.sequence_recording["frames"].append(frame)
        if self.recording:
            r = self.recording
            now = time.monotonic()
            if now >= r["start"]:
                if frame is None or now - packet.timestamp > MAX_AGE:
                    self.cancel_recording()
                    self.message("Exemplo descartado por perda de tracking/atraso. Grave novamente.")
                else:
                    r["frames"].append(frame)
                    self.capture_progress.setValue(min(100, int((now-r["start"])/(r["end"]-r["start"])*100)))
                    if now >= r["end"]:
                        try:
                            clip = Clip(r["label"], r["frames"])
                            from .features import windows
                            if len(list(windows(clip.frames))) < 5:
                                raise ValueError("Exemplo curto/irregular; grave novamente")
                            self.session.clips.append(clip)
                            self.refresh_clips()
                            self.message("Exemplo adicionado em memória. Salve a sessão para persistir/exportar.")
                        except Exception as e:
                            self.message(str(e))
                        self.cancel_recording()
        if self.cal_target is not None and self.cal_target > 0 and time.monotonic() >= self.cal_target:
            try:
                self.cal_points.append(self.current_frame().points[8, :2].tolist())
                if len(self.cal_points) == len(TARGETS):
                    self.profile.calibration = Calibration.fit(self.cal_points, TARGETS)
                    self.cal_label.setText(f"Calibrado · RMSE de ajuste {self.profile.calibration.error:.3f}; não é erro validado em uso.")
                    self.cancel_calibration()
                else:
                    self.cal_target = 0
                    self.show_target()
            except Exception as e:
                self.cancel_calibration()
                self.message(str(e))
        try:
            label, confidence, actions, uv = self.runtime.process(frame)
            self.prediction.setText(f"{packet.detail} · {label} · {confidence:.0%} · ações previstas: {', '.join(actions) or 'nenhuma'}"
                                    + (f" · cursor {uv[0]:.2f}, {uv[1]:.2f}" if uv is not None else ""))
            if self.active:
                if label == "lost":
                    self.pause()
                    self.message("Pausado: mão perdida ou frame atrasado. Ative novamente e mostre neutral.")
                else:
                    xy = self.screens[self.monitor.currentIndex()].map(uv) if uv is not None else None
                    self.input.publish(packet.timestamp, actions, xy, self.profile.scroll_step)
                    self.state.setText("ATIVO · " + ("armado" if self.runtime.policy.armed else "aguardando neutral / gesto"))
        except Exception as e:
            self.pause()
            self.message(str(e))

    @staticmethod
    def display_fingerprint():
        return [(s.name(), s.geometry().x(), s.geometry().y(), s.geometry().width(),
                 s.geometry().height(), round(s.logicalDotsPerInch(), 2)) for s in QApplication.screens()]

    def closeEvent(self, event):
        self.pause()
        self.timer.stop()
        self.stop_camera()
        if self.input and not self.input.close():
            self.centralWidget().setEnabled(False)
            self.message("Fechamento pendente: aguardando liberação de botões e conclusão do processo de entrada.")
            self.shutdown_timer.start(100)
            event.ignore()
            return
        self.shutdown_timer.stop()
        event.accept()

    def finish_shutdown(self):
        if self.input:
            for kind, detail in self.input.poll():
                if kind == "error":
                    self.message("Fechamento pendente: " + detail)
            if self.input.process.is_alive():
                return
        self.close()

    def request_shutdown(self):
        # Also stop fresh commands if the application exits through an OS/app quit path.
        # Non-daemon ownership makes Python wait for worker cleanup instead of killing it.
        self.pause()
        if self.input:
            self.input.stop.set()
        if self.camera:
            self.camera.stop_event.set()
