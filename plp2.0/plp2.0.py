import os
import sys
import json
import random
from pathlib import Path
from dataclasses import dataclass

from PyQt6.QtCore import Qt, QUrl, QTime, QSize, QSettings
from PyQt6.QtGui import (
    QIcon, QPixmap, QFont, QAction, QKeySequence, QFontDatabase,
    QPainter, QColor
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox, QStatusBar,
    QMenuBar, QToolBar, QLabel, QSlider, QComboBox, QTextEdit, QHBoxLayout,
    QVBoxLayout, QListWidget, QListWidgetItem, QDockWidget, QLineEdit,
    QInputDialog, QPushButton, QTabWidget, QStyle
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData
from PyQt6.QtMultimediaWidgets import QVideoWidget

try:
    from PyQt6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except Exception:
    _HAS_SVG = False


APP_NAME = "Pars Local Player 2.1"
ORG_NAME = "ParrotHat Foundation"

APP_DIR = Path(__file__).resolve().parent
ICON_DIR = APP_DIR / "icons"
FONT_PATH = APP_DIR / "fonts" / "inter.ttf"


SUPPORTED_EXTS = {
    # video containers
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".3gp", ".3g2",
    ".flv", ".wmv", ".asf", ".mpg", ".mpeg", ".mpe", ".ts", ".m2ts",
    ".mts", ".vob", ".ogv", ".divx",
    # audio containers
    ".mp3", ".flac", ".ogg", ".opus", ".wav", ".m4a", ".aac", ".wma",
    ".aiff", ".aif", ".aifc", ".alac", ".ape", ".mka",
    # playlists
    ".m3u", ".m3u8", ".pls",
}

FILE_FILTER = (
    "Media Files ("
    "*.mp4 *.mkv *.avi *.mov *.webm *.m4v *.3gp *.3g2 *.flv *.wmv *.asf "
    "*.mpg *.mpeg *.mpe *.ts *.m2ts *.mts *.vob *.ogv *.divx "
    "*.mp3 *.flac *.ogg *.opus *.wav *.m4a *.aac *.wma *.aiff *.aif *.aifc *.alac *.ape *.mka "
    "*.m3u *.m3u8 *.pls"
    ");;All Files (*)"
)


@dataclass
class PlaylistEntry:
    url: QUrl
    title: str


class ClickSeekSlider(QSlider):
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.maximum() > self.minimum():
            x = e.position().x()
            w = max(1.0, float(self.width()))
            ratio = min(1.0, max(0.0, x / w))
            new_val = int(self.minimum() + ratio * (self.maximum() - self.minimum()))
            self.setValue(new_val)
            self.sliderMoved.emit(new_val)
            e.accept()
        super().mousePressEvent(e)


class ParsLocalPlayer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.settings = QSettings(ORG_NAME, "PLP")
        self.setWindowTitle(APP_NAME)
        self.resize(1320, 780)
        self.setAcceptDrops(True)

        self._icon_cache: dict[tuple[str, int, str], QIcon] = {}
        self._last_dir = self.settings.value("paths/last_dir", str(Path.home()))
        self._recent: list[str] = self._load_recent()

        # playback state
        self.entries: list[PlaylistEntry] = []
        self.current_index: int = -1
        self.shuffle_enabled = False
        self.repeat_mode = "Off"  # Off | One | All
        self._ab_enabled = False
        self._ab_a = 0
        self._ab_b = 0

        self._build_style()
        self._build_multimedia()
        self._build_ui()
        self._build_menu()
        self._build_toolbar()
        self._wire_signals()
        self._restore_state()

        self._log("Ready")

    # ------------------- Style / Icons / Font -------------------

    def _build_style(self):
        # Load Inter from fonts/inter.ttf (optional)
        if FONT_PATH.exists():
            font_id = QFontDatabase.addApplicationFont(str(FONT_PATH))
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                self.setFont(QFont(families[0], 10))
            else:
                self.setFont(QFont("Inter", 10))
        else:
            self.setFont(QFont("Inter", 10))

        # Dark UI
        self.setStyleSheet("""
            QMainWindow { background: #0b0f14; }
            QWidget { color: #e7eefc; }
            QDockWidget::title {
                background:#0f1720; padding:6px; border-bottom:1px solid #1f2a37;
            }
            QMenuBar { background:#0f1720; color:#e7eefc; border-bottom:1px solid #1f2a37; }
            QMenuBar::item:selected { background:#16202b; }
            QMenu { background:#0f1720; color:#e7eefc; border:1px solid #1f2a37; }
            QMenu::item:selected { background:#16202b; }

            QLabel { color:#e7eefc; }
            QTextEdit, QListWidget, QLineEdit {
                background:#0f1720; color:#e7eefc;
                border:1px solid #1f2a37; border-radius:10px;
            }
            QListWidget::item { padding:6px; border-radius:8px; }
            QListWidget::item:selected { background:#16202b; }

            QPushButton {
                background:#0f1720;
                border:1px solid #1f2a37;
                border-radius:10px;
                padding:7px 10px;
            }
            QPushButton:hover { background:#16202b; }
            QPushButton:disabled { color:#7a8799; }

            QComboBox {
                background:#0f1720;
                border:1px solid #1f2a37;
                border-radius:10px;
                padding:6px 10px;
            }
            QComboBox::drop-down { border:0; }

            QSlider::groove:horizontal { background:#1b2633; height:6px; border-radius:3px; }
            QSlider::handle:horizontal { background:#4ea1ff; width:14px; margin:-5px 0; border-radius:7px; }

            QStatusBar { background:#0f1720; border-top:1px solid #1f2a37; }
            QTabWidget::pane { border:1px solid #1f2a37; border-radius:10px; }
            QTabBar::tab {
                background:#0f1720; border:1px solid #1f2a37;
                padding:6px 10px; border-top-left-radius:10px; border-top-right-radius:10px;
            }
            QTabBar::tab:selected { background:#16202b; }
        """)

    def _svg_icon(self, name: str, size: int = 18, color: str = "#e7eefc") -> QIcon:
        key = (name, size, color)
        if key in self._icon_cache:
            return self._icon_cache[key]

        path = ICON_DIR / f"{name}.svg"
        if not path.exists():
            icon = QIcon()
            self._icon_cache[key] = icon
            return icon

        # If SVG renderer not available, use path directly (no tint)
        if not _HAS_SVG:
            icon = QIcon(str(path))
            self._icon_cache[key] = icon
            return icon

        try:
            svg = path.read_text(encoding="utf-8", errors="ignore")
            # Lucide usually uses currentColor; replace for tint
            svg = svg.replace("currentColor", color)
            data = svg.encode("utf-8")

            renderer = QSvgRenderer(data)
            pm = QPixmap(size, size)
            pm.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pm)
            renderer.render(painter)
            painter.end()

            icon = QIcon(pm)
        except Exception:
            icon = QIcon(str(path))

        self._icon_cache[key] = icon
        return icon

    # ------------------- Multimedia -------------------

    def _build_multimedia(self):
        self.media = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.media.setAudioOutput(self.audio)

        self.video = QVideoWidget(self)
        self.media.setVideoOutput(self.video)

        vol = int(self.settings.value("audio/volume", 80))
        self.audio.setVolume(max(0, min(100, vol)) / 100.0)
        self.audio.setMuted(bool(self.settings.value("audio/muted", False, type=bool)))

    # ------------------- UI -------------------

    def _build_ui(self):
        # Central
        self.seek_slider = ClickSeekSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)

        self.time_label = QLabel("00:00 / 00:00")
        self.now_label = QLabel("No media loaded")
        self.now_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.audio.volume() * 100))
        self.volume_label = QLabel(f"{self.volume_slider.value()}%")

        self.rate_box = QComboBox()
        self.rate_box.addItems(["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"])
        self.rate_box.setCurrentText(str(self.settings.value("playback/rate", "1.0x")))

        self.repeat_box = QComboBox()
        self.repeat_box.addItems(["Off", "One", "All"])
        self.repeat_box.setCurrentText(str(self.settings.value("playback/repeat", "Off")))

        self.shuffle_btn = QPushButton("Shuffle")
        self.shuffle_btn.setCheckable(True)
        self.shuffle_btn.setChecked(bool(self.settings.value("playback/shuffle", False, type=bool)))
        self.shuffle_enabled = self.shuffle_btn.isChecked()

        self.ab_a_btn = QPushButton("Set A")
        self.ab_b_btn = QPushButton("Set B")
        self.ab_clear_btn = QPushButton("Clear A-B")

        # Use icons on these buttons
        self.shuffle_btn.setIcon(self._svg_icon("shuffle", 18))
        self.ab_a_btn.setIcon(self._svg_icon("flag", 18))
        self.ab_b_btn.setIcon(self._svg_icon("flag", 18))
        self.ab_clear_btn.setIcon(self._svg_icon("x-circle", 18))

        # Info / Log dock
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setFont(QFont("Consolas", 9))

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))

        tabs = QTabWidget()
        tabs.addTab(self.info_text, "Media Info")
        tabs.addTab(self.log_text, "Log")

        self.info_dock = QDockWidget("Info", self)
        self.info_dock.setWidget(tabs)
        self.info_dock.setObjectName("dock_info")
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.info_dock)

        # Playlist dock
        self.playlist_list = QListWidget()
        self.playlist_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        self.playlist_search = QLineEdit()
        self.playlist_search.setPlaceholderText("Search playlist...")

        self.btn_add = QPushButton("Add")
        self.btn_add.setIcon(self._svg_icon("plus", 18))

        self.btn_add_folder = QPushButton("Folder")
        self.btn_add_folder.setIcon(self._svg_icon("folder-plus", 18))

        self.btn_remove = QPushButton("Remove")
        self.btn_remove.setIcon(self._svg_icon("trash", 18))

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setIcon(self._svg_icon("delete", 18))

        self.btn_up = QPushButton("Up")
        self.btn_up.setIcon(self._svg_icon("chevron-up", 18))

        self.btn_down = QPushButton("Down")
        self.btn_down.setIcon(self._svg_icon("chevron-down", 18))

        plist_top = QHBoxLayout()
        plist_top.addWidget(self.playlist_search)

        plist_btns = QHBoxLayout()
        for w in (self.btn_add, self.btn_add_folder, self.btn_remove, self.btn_clear, self.btn_up, self.btn_down):
            plist_btns.addWidget(w)

        plist_layout = QVBoxLayout()
        plist_layout.addLayout(plist_top)
        plist_layout.addWidget(self.playlist_list, stretch=1)
        plist_layout.addLayout(plist_btns)

        plist_container = QWidget()
        plist_container.setLayout(plist_layout)

        self.playlist_dock = QDockWidget("Playlist", self)
        self.playlist_dock.setWidget(plist_container)
        self.playlist_dock.setObjectName("dock_playlist")
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.playlist_dock)

        # Central layout
        top_row = QHBoxLayout()
        top_row.addWidget(self.now_label, 1)

        mid_row = QHBoxLayout()
        mid_row.addWidget(self.seek_slider, 1)
        mid_row.addWidget(self.time_label)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(QLabel("Volume"))
        bottom_row.addWidget(self.volume_slider, 1)
        bottom_row.addWidget(self.volume_label)
        bottom_row.addSpacing(12)
        bottom_row.addWidget(QLabel("Speed"))
        bottom_row.addWidget(self.rate_box)
        bottom_row.addSpacing(12)
        bottom_row.addWidget(QLabel("Repeat"))
        bottom_row.addWidget(self.repeat_box)
        bottom_row.addWidget(self.shuffle_btn)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.ab_a_btn)
        bottom_row.addWidget(self.ab_b_btn)
        bottom_row.addWidget(self.ab_clear_btn)

        layout = QVBoxLayout()
        layout.addLayout(top_row)
        layout.addWidget(self.video, stretch=20)
        layout.addLayout(mid_row)
        layout.addLayout(bottom_row)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.status = QStatusBar(self)
        self.setStatusBar(self.status)

    def _build_menu(self):
        mbar = QMenuBar(self)
        self.setMenuBar(mbar)

        # File
        self.file_menu = mbar.addMenu("File")
        self.act_open = QAction("Open Files...", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open_folder = QAction("Open Folder...", self)
        self.act_open_folder.setShortcut(QKeySequence("Ctrl+Shift+O"))
        self.act_open_stream = QAction("Open Stream URL...", self)
        self.act_open_stream.setShortcut(QKeySequence("Ctrl+L"))
        self.act_open_playlist = QAction("Open Playlist...", self)
        self.act_open_playlist.setShortcut(QKeySequence("Ctrl+P"))
        self.act_save_playlist = QAction("Save Playlist...", self)
        self.act_save_playlist.setShortcut(QKeySequence.StandardKey.Save)
        self.act_exit = QAction("Exit", self)
        self.act_exit.setShortcut(QKeySequence.StandardKey.Quit)

        self.recent_menu = self.file_menu.addMenu("Open Recent")
        self.act_clear_recent = QAction("Clear Recent", self)

        self.file_menu.addAction(self.act_open)
        self.file_menu.addAction(self.act_open_folder)
        self.file_menu.addAction(self.act_open_stream)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.act_open_playlist)
        self.file_menu.addAction(self.act_save_playlist)
        self.file_menu.addSeparator()
        self.file_menu.addMenu(self.recent_menu)
        self.file_menu.addAction(self.act_clear_recent)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.act_exit)

        # Playback
        self.play_menu = mbar.addMenu("Playback")
        self.act_play_pause = QAction("Play/Pause", self)
        self.act_play_pause.setShortcut(QKeySequence("Space"))
        self.act_stop = QAction("Stop", self)
        self.act_stop.setShortcut(QKeySequence("S"))
        self.act_prev = QAction("Previous", self)
        self.act_prev.setShortcut(QKeySequence("P"))
        self.act_next = QAction("Next", self)
        self.act_next.setShortcut(QKeySequence("N"))
        self.act_seek_back = QAction("Seek -5s", self)
        self.act_seek_back.setShortcut(QKeySequence(Qt.Key.Key_Left))
        self.act_seek_fwd = QAction("Seek +5s", self)
        self.act_seek_fwd.setShortcut(QKeySequence(Qt.Key.Key_Right))
        self.act_jump = QAction("Jump to Time...", self)
        self.act_jump.setShortcut(QKeySequence("Ctrl+J"))

        self.play_menu.addAction(self.act_play_pause)
        self.play_menu.addAction(self.act_stop)
        self.play_menu.addSeparator()
        self.play_menu.addAction(self.act_prev)
        self.play_menu.addAction(self.act_next)
        self.play_menu.addSeparator()
        self.play_menu.addAction(self.act_seek_back)
        self.play_menu.addAction(self.act_seek_fwd)
        self.play_menu.addAction(self.act_jump)

        # Audio
        self.audio_menu = mbar.addMenu("Audio")
        self.act_mute = QAction("Mute", self)
        self.act_mute.setShortcut(QKeySequence("M"))
        self.audio_menu.addAction(self.act_mute)

        # Video
        self.video_menu = mbar.addMenu("Video")
        self.act_fullscreen = QAction("Fullscreen", self)
        self.act_fullscreen.setShortcut(QKeySequence("F"))
        self.act_ontop = QAction("Always on Top", self)
        self.act_ontop.setCheckable(True)
        self.video_menu.addAction(self.act_fullscreen)
        self.video_menu.addSeparator()
        self.video_menu.addAction(self.act_ontop)

        # View
        self.view_menu = mbar.addMenu("View")
        self.act_toggle_playlist = QAction("Show Playlist", self)
        self.act_toggle_playlist.setCheckable(True)
        self.act_toggle_playlist.setChecked(True)

        self.act_toggle_info = QAction("Show Info", self)
        self.act_toggle_info.setCheckable(True)
        self.act_toggle_info.setChecked(True)

        self.view_menu.addAction(self.act_toggle_playlist)
        self.view_menu.addAction(self.act_toggle_info)

        # Tools
        self.tools_menu = mbar.addMenu("Tools")
        self.act_screenshot = QAction("Screenshot...", self)
        self.act_screenshot.setShortcut(QKeySequence("Ctrl+K"))
        self.act_copy_info = QAction("Copy Media Info", self)
        self.act_copy_info.setShortcut(QKeySequence("Ctrl+I"))
        self.act_reset = QAction("Reset Player", self)
        self.act_reset.setShortcut(QKeySequence("Ctrl+R"))

        self.tools_menu.addAction(self.act_screenshot)
        self.tools_menu.addAction(self.act_copy_info)
        self.tools_menu.addSeparator()
        self.tools_menu.addAction(self.act_reset)

        # Help
        self.help_menu = mbar.addMenu("Help")
        self.act_about = QAction("About", self)
        self.help_menu.addAction(self.act_about)

        self._rebuild_recent_menu()

    def _build_toolbar(self):
        tb = QToolBar("Controls", self)
        tb.setIconSize(QSize(20, 20))
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

        def mk_action(text, icon_name, shortcut=None, tip=None):
            act = QAction(self._svg_icon(icon_name, 20), text, self)
            if shortcut:
                act.setShortcut(QKeySequence(shortcut))
            if tip:
                act.setToolTip(tip)
            return act

        self.t_act_open = mk_action("Open", "folder", None, "Open files")
        self.t_act_stream = mk_action("Stream", "globe", None, "Open stream URL")
        self.t_act_prev = mk_action("Previous", "skip-back", None, "Previous")
        self.t_act_play = mk_action("Play/Pause", "play", None, "Play/Pause")
        self.t_act_next = mk_action("Next", "skip-forward", None, "Next")
        self.t_act_stop = mk_action("Stop", "stop-circle", None, "Stop")
        self.t_act_shot = mk_action("Screenshot", "camera", None, "Screenshot")
        self.t_act_mute = mk_action("Mute", "volume-x", None, "Mute")
        self.t_act_reset = mk_action("Reset", "refresh-cw", None, "Reset")

        tb.addAction(self.t_act_open)
        tb.addAction(self.t_act_stream)
        tb.addSeparator()
        tb.addAction(self.t_act_prev)
        tb.addAction(self.t_act_play)
        tb.addAction(self.t_act_next)
        tb.addAction(self.t_act_stop)
        tb.addSeparator()
        tb.addAction(self.t_act_shot)
        tb.addAction(self.t_act_mute)
        tb.addAction(self.t_act_reset)

    def _wire_signals(self):
        # Menu
        self.act_open.triggered.connect(self.open_files)
        self.act_open_folder.triggered.connect(self.open_folder)
        self.act_open_stream.triggered.connect(self.open_stream)
        self.act_open_playlist.triggered.connect(self.load_playlist)
        self.act_save_playlist.triggered.connect(self.save_playlist)
        self.act_exit.triggered.connect(self.close)
        self.act_clear_recent.triggered.connect(self.clear_recent)

        self.act_play_pause.triggered.connect(self.play_pause)
        self.act_stop.triggered.connect(self.stop)
        self.act_prev.triggered.connect(self.prev_track)
        self.act_next.triggered.connect(self.next_track)
        self.act_seek_back.triggered.connect(lambda: self.seek_relative(-5000))
        self.act_seek_fwd.triggered.connect(lambda: self.seek_relative(5000))
        self.act_jump.triggered.connect(self.jump_to_time)

        self.act_mute.triggered.connect(self.toggle_mute)
        self.act_fullscreen.triggered.connect(self.toggle_fullscreen)
        self.act_ontop.toggled.connect(self.set_always_on_top)

        self.act_toggle_playlist.toggled.connect(self.playlist_dock.setVisible)
        self.act_toggle_info.toggled.connect(self.info_dock.setVisible)

        self.act_screenshot.triggered.connect(self.screenshot)
        self.act_copy_info.triggered.connect(self.copy_media_info)
        self.act_reset.triggered.connect(self.reset_player)

        self.act_about.triggered.connect(self.about)

        # Toolbar
        self.t_act_open.triggered.connect(self.open_files)
        self.t_act_stream.triggered.connect(self.open_stream)
        self.t_act_prev.triggered.connect(self.prev_track)
        self.t_act_play.triggered.connect(self.play_pause)
        self.t_act_next.triggered.connect(self.next_track)
        self.t_act_stop.triggered.connect(self.stop)
        self.t_act_shot.triggered.connect(self.screenshot)
        self.t_act_mute.triggered.connect(self.toggle_mute)
        self.t_act_reset.triggered.connect(self.reset_player)

        # Controls
        self.volume_slider.valueChanged.connect(self.adjust_volume)
        self.rate_box.currentTextChanged.connect(self.change_playback_rate)
        self.repeat_box.currentTextChanged.connect(self.change_repeat_mode)
        self.shuffle_btn.toggled.connect(self.toggle_shuffle)

        self.ab_a_btn.clicked.connect(self.set_ab_a)
        self.ab_b_btn.clicked.connect(self.set_ab_b)
        self.ab_clear_btn.clicked.connect(self.clear_ab)

        self.seek_slider.sliderMoved.connect(self.media.setPosition)

        # Playlist dock buttons
        self.btn_add.clicked.connect(self.open_files)
        self.btn_add_folder.clicked.connect(self.open_folder)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_playlist)
        self.btn_up.clicked.connect(lambda: self.move_selected(-1))
        self.btn_down.clicked.connect(lambda: self.move_selected(+1))
        self.playlist_list.itemDoubleClicked.connect(self._playlist_double_clicked)
        self.playlist_search.textChanged.connect(self._playlist_apply_filter)

        # Media signals
        self.media.positionChanged.connect(self.update_position)
        self.media.durationChanged.connect(self.update_duration)
        self.media.mediaStatusChanged.connect(self.on_media_status)
        self.media.metaDataChanged.connect(self.refresh_media_info)
        self.media.errorOccurred.connect(self.on_error)
        self.media.playbackStateChanged.connect(self.on_state_changed)

    # ------------------- File / Playlist -------------------

    def open_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Open Media Files", self._last_dir, FILE_FILTER
        )
        if not files:
            return
        self._last_dir = str(Path(files[0]).parent)
        self.settings.setValue("paths/last_dir", self._last_dir)

        self.add_files_to_playlist(files, auto_play=(self.current_index < 0))

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Folder", self._last_dir)
        if not folder:
            return
        self._last_dir = folder
        self.settings.setValue("paths/last_dir", self._last_dir)

        paths = []
        for p in sorted(Path(folder).iterdir()):
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                if p.suffix.lower() in {".m3u", ".m3u8", ".pls"}:
                    continue
                paths.append(str(p))
        if not paths:
            self._notify("No supported media files found in this folder.")
            return

        self.add_files_to_playlist(paths, auto_play=(self.current_index < 0))

    def open_stream(self):
        url, ok = QInputDialog.getText(
            self, "Open Stream", "Enter URL (http/https/rtsp/m3u8):"
        )
        if not ok or not url.strip():
            return
        qurl = QUrl(url.strip())
        title = url.strip()

        self.entries.append(PlaylistEntry(qurl, title))
        self._playlist_render()
        if self.current_index < 0:
            self.play_index(0)

    def add_files_to_playlist(self, files: list[str], auto_play: bool = True):
        first_added_index = len(self.entries)
        for f in files:
            p = Path(f)
            if not p.exists():
                continue
            if p.suffix.lower() in {".m3u", ".m3u8", ".pls"}:
                # load playlist file directly
                self._load_playlist_from_path(str(p))
                continue

            url = QUrl.fromLocalFile(str(p))
            self.entries.append(PlaylistEntry(url, p.name))
            self._add_recent(str(p))

        self._playlist_render()
        if auto_play and len(self.entries) > 0:
            self.play_index(max(0, first_added_index))

    def load_playlist(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Playlist", self._last_dir,
            "Playlists (*.m3u *.m3u8 *.pls);;All Files (*)"
        )
        if not path:
            return
        self._last_dir = str(Path(path).parent)
        self.settings.setValue("paths/last_dir", self._last_dir)
        self._load_playlist_from_path(path)

    def _load_playlist_from_path(self, path: str):
        p = Path(path)
        if not p.exists():
            return
        ext = p.suffix.lower()
        added_any = False

        try:
            text = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            self._notify("Failed to read playlist.")
            return

        if ext in {".m3u", ".m3u8"}:
            for line in text:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "://" in line:
                    self.entries.append(PlaylistEntry(QUrl(line), line))
                    added_any = True
                else:
                    # relative file path
                    fp = (p.parent / line).resolve()
                    if fp.exists():
                        self.entries.append(PlaylistEntry(QUrl.fromLocalFile(str(fp)), fp.name))
                        self._add_recent(str(fp))
                        added_any = True

        elif ext == ".pls":
            # very small PLS parser
            kv = {}
            for line in text:
                line = line.strip()
                if not line or line.startswith("["):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    kv[k.strip()] = v.strip()
            idx = 1
            while True:
                key = f"File{idx}"
                if key not in kv:
                    break
                val = kv[key]
                title = kv.get(f"Title{idx}", val)
                if "://" in val:
                    self.entries.append(PlaylistEntry(QUrl(val), title))
                    added_any = True
                else:
                    fp = (p.parent / val).resolve()
                    if fp.exists():
                        self.entries.append(PlaylistEntry(QUrl.fromLocalFile(str(fp)), title))
                        self._add_recent(str(fp))
                        added_any = True
                idx += 1

        if not added_any:
            self._notify("Playlist loaded, but no playable entries were found.")
            return

        self._playlist_render()
        if self.current_index < 0 and self.entries:
            self.play_index(0)

    def save_playlist(self):
        if not self.entries:
            self._notify("Playlist is empty.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Playlist", self._last_dir, "M3U Playlist (*.m3u)"
        )
        if not path:
            return
        if not path.lower().endswith(".m3u"):
            path += ".m3u"

        lines = ["#EXTM3U"]
        for e in self.entries:
            if e.url.isLocalFile():
                lines.append(e.url.toLocalFile())
            else:
                lines.append(e.url.toString())

        try:
            Path(path).write_text("\n".join(lines), encoding="utf-8")
            self._log(f"Saved playlist: {path}")
            self.status.showMessage(f"Saved playlist: {Path(path).name}", 3000)
        except Exception:
            self._notify("Failed to save playlist.")

    def _playlist_render(self):
        self.playlist_list.blockSignals(True)
        self.playlist_list.clear()
        for idx, e in enumerate(self.entries):
            item = QListWidgetItem(e.title)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            if idx == self.current_index:
                item.setIcon(self._svg_icon("play-circle", 18, "#4ea1ff"))
            else:
                item.setIcon(self._svg_icon("music", 18, "#e7eefc"))
            self.playlist_list.addItem(item)
        self.playlist_list.blockSignals(False)
        self._playlist_apply_filter(self.playlist_search.text())

    def _playlist_apply_filter(self, text: str):
        q = (text or "").strip().lower()
        for i in range(self.playlist_list.count()):
            it = self.playlist_list.item(i)
            it.setHidden(bool(q) and q not in it.text().lower())

    def _playlist_double_clicked(self, item: QListWidgetItem):
        idx = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(idx, int):
            self.play_index(idx)

    def remove_selected(self):
        row = self.playlist_list.currentRow()
        if row < 0 or row >= len(self.entries):
            return
        remove_idx = self.playlist_list.item(row).data(Qt.ItemDataRole.UserRole)
        if not isinstance(remove_idx, int):
            return

        del self.entries[remove_idx]
        if self.current_index == remove_idx:
            self.stop()
            self.current_index = -1
        elif self.current_index > remove_idx:
            self.current_index -= 1

        self._playlist_render()
        if self.current_index < 0 and self.entries:
            self.play_index(0)

    def clear_playlist(self):
        self.stop()
        self.entries.clear()
        self.current_index = -1
        self._playlist_render()
        self.now_label.setText("No media loaded")
        self.info_text.setText("")
        self.status.showMessage("Playlist cleared", 2000)

    def move_selected(self, delta: int):
        row = self.playlist_list.currentRow()
        if row < 0:
            return
        idx = self.playlist_list.item(row).data(Qt.ItemDataRole.UserRole)
        if not isinstance(idx, int):
            return
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(self.entries):
            return

        self.entries[idx], self.entries[new_idx] = self.entries[new_idx], self.entries[idx]

        if self.current_index == idx:
            self.current_index = new_idx
        elif self.current_index == new_idx:
            self.current_index = idx

        self._playlist_render()
        # restore selection
        for i in range(self.playlist_list.count()):
            it = self.playlist_list.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == new_idx:
                self.playlist_list.setCurrentRow(i)
                break

    # ------------------- Playback -------------------

    def play_index(self, idx: int):
        if idx < 0 or idx >= len(self.entries):
            return

        self.current_index = idx
        entry = self.entries[idx]
        self.media.setSource(entry.url)
        self.media.play()

        self.now_label.setText(entry.title)
        self.status.showMessage(f"Playing: {entry.title}", 3000)
        self._playlist_render()

        # ensure AB loop reset when track changes
        self._ab_enabled = False
        self._ab_a = 0
        self._ab_b = 0

    def play_pause(self):
        state = self.media.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.media.pause()
        else:
            if self.current_index < 0 and self.entries:
                self.play_index(0)
            else:
                self.media.play()

    def stop(self):
        self.media.stop()

    def next_track(self):
        if not self.entries:
            return
        if self.current_index < 0:
            self.play_index(0)
            return

        nxt = self._next_index()
        if nxt is None:
            self.stop()
            return
        self.play_index(nxt)

    def prev_track(self):
        if not self.entries:
            return
        if self.current_index < 0:
            self.play_index(0)
            return

        if self.shuffle_enabled:
            prv = random.randrange(0, len(self.entries))
            self.play_index(prv)
            return

        prv = self.current_index - 1
        if prv < 0:
            if self.repeat_mode == "All":
                prv = len(self.entries) - 1
            else:
                prv = 0
        self.play_index(prv)

    def _next_index(self):
        if self.repeat_mode == "One":
            return self.current_index

        if self.shuffle_enabled:
            if len(self.entries) == 1:
                return self.current_index
            choices = [i for i in range(len(self.entries)) if i != self.current_index]
            return random.choice(choices)

        nxt = self.current_index + 1
        if nxt >= len(self.entries):
            if self.repeat_mode == "All":
                return 0
            return None
        return nxt

    def seek_relative(self, ms: int):
        pos = self.media.position()
        self.media.setPosition(max(0, pos + ms))

    def jump_to_time(self):
        if self.media.duration() <= 0:
            return
        txt, ok = QInputDialog.getText(self, "Jump to Time", "Time (mm:ss or hh:mm:ss):")
        if not ok or not txt.strip():
            return
        t = txt.strip()
        parts = t.split(":")
        try:
            if len(parts) == 2:
                mm, ss = int(parts[0]), int(parts[1])
                ms = (mm * 60 + ss) * 1000
            elif len(parts) == 3:
                hh, mm, ss = int(parts[0]), int(parts[1]), int(parts[2])
                ms = (hh * 3600 + mm * 60 + ss) * 1000
            else:
                return
            self.media.setPosition(max(0, min(self.media.duration(), ms)))
        except Exception:
            return

    def update_position(self, pos: int):
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(pos)
        self.seek_slider.blockSignals(False)

        dur = self.media.duration()
        self.time_label.setText(f"{self._fmt_time(pos)} / {self._fmt_time(dur)}")

        # A-B loop
        if self._ab_enabled and self._ab_b > self._ab_a > 0:
            if pos >= self._ab_b:
                self.media.setPosition(self._ab_a)

    def update_duration(self, dur: int):
        self.seek_slider.setRange(0, max(0, dur))
        self.time_label.setText(f"{self._fmt_time(self.media.position())} / {self._fmt_time(dur)}")

    def on_media_status(self, status):
        # Advance playlist when a track ends
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            nxt = self._next_index()
            if nxt is not None:
                self.play_index(nxt)
            else:
                self.stop()

    def on_error(self, err, msg):
        if msg:
            self._notify(msg)
        self._log(f"Error: {msg}")

    def on_state_changed(self, state):
        # Toolbar play icon flip (best-effort)
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.t_act_play.setIcon(self._svg_icon("pause-circle", 20))
        else:
            self.t_act_play.setIcon(self._svg_icon("play", 20))

    # ------------------- Audio / Video -------------------

    def adjust_volume(self, v: int):
        v = max(0, min(100, int(v)))
        self.audio.setVolume(v / 100.0)
        self.volume_label.setText(f"{v}%")
        self.settings.setValue("audio/volume", v)

    def toggle_mute(self):
        muted = not self.audio.isMuted()
        self.audio.setMuted(muted)
        self.settings.setValue("audio/muted", muted)
        self.t_act_mute.setIcon(self._svg_icon("volume-x" if muted else "volume-2", 20))
        self.status.showMessage("Muted" if muted else "Unmuted", 2000)

    def change_playback_rate(self, text: str):
        try:
            rate = float(text.replace("x", "").strip())
        except Exception:
            rate = 1.0
        self.media.setPlaybackRate(rate)
        self.settings.setValue("playback/rate", text)
        self._log(f"Playback rate: {rate}x")

    def change_repeat_mode(self, mode: str):
        self.repeat_mode = mode
        self.settings.setValue("playback/repeat", mode)
        self._log(f"Repeat: {mode}")

    def toggle_shuffle(self, enabled: bool):
        self.shuffle_enabled = enabled
        self.settings.setValue("playback/shuffle", enabled)
        self._log(f"Shuffle: {'On' if enabled else 'Off'}")

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def set_always_on_top(self, enabled: bool):
        flags = self.windowFlags()
        if enabled:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    # ------------------- A-B Loop -------------------

    def set_ab_a(self):
        if self.media.duration() <= 0:
            return
        self._ab_a = self.media.position()
        self._ab_enabled = False
        self.status.showMessage(f"A set at {self._fmt_time(self._ab_a)}", 2500)

    def set_ab_b(self):
        if self.media.duration() <= 0:
            return
        self._ab_b = self.media.position()
        if self._ab_a > 0 and self._ab_b > self._ab_a:
            self._ab_enabled = True
            self.status.showMessage(
                f"A-B loop enabled ({self._fmt_time(self._ab_a)} -> {self._fmt_time(self._ab_b)})",
                3000
            )
        else:
            self._ab_enabled = False
            self.status.showMessage("B must be after A", 2500)

    def clear_ab(self):
        self._ab_enabled = False
        self._ab_a = 0
        self._ab_b = 0
        self.status.showMessage("A-B loop cleared", 2000)

    # ------------------- Screenshot / Info -------------------

    def screenshot(self):
        frame = self.video.grab()
        if frame.isNull():
            self._notify("Screenshot failed.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", self._last_dir, "PNG Image (*.png)")
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        ok = frame.save(path)
        if ok:
            self.status.showMessage(f"Saved screenshot: {Path(path).name}", 3000)
            self._log(f"Screenshot saved: {path}")
        else:
            self._notify("Failed to save screenshot.")

    def refresh_media_info(self):
        md = self.media.metaData()
        url = self.media.source()
        lines = []

        lines.append(f"Title: {self.now_label.text()}")
        lines.append(f"Source: {url.toString() if url.isValid() else 'N/A'}")
        if url.isLocalFile():
            p = Path(url.toLocalFile())
            if p.exists():
                try:
                    size = p.stat().st_size
                    lines.append(f"File: {p.name}")
                    lines.append(f"Path: {p}")
                    lines.append(f"Size: {self._fmt_bytes(size)}")
                except Exception:
                    pass

        dur = self.media.duration()
        if dur > 0:
            lines.append(f"Duration: {self._fmt_time(dur)}")

        def add_k(label, key):
            try:
                v = md.value(key)
                if v:
                    lines.append(f"{label}: {v}")
            except Exception:
                pass

        add_k("Audio Codec", QMediaMetaData.Key.AudioCodec)
        add_k("Video Codec", QMediaMetaData.Key.VideoCodec)
        add_k("Audio Bitrate", QMediaMetaData.Key.AudioBitRate)
        add_k("Video Bitrate", QMediaMetaData.Key.VideoBitRate)
        add_k("Sample Rate", QMediaMetaData.Key.AudioSampleRate)
        add_k("Channels", QMediaMetaData.Key.ChannelCount)
        add_k("Frame Rate", QMediaMetaData.Key.VideoFrameRate)
        add_k("Resolution", QMediaMetaData.Key.Resolution)
        add_k("Language", QMediaMetaData.Key.Language)
        add_k("Album", QMediaMetaData.Key.AlbumTitle)
        add_k("Artist", QMediaMetaData.Key.AlbumArtist)
        add_k("Track", QMediaMetaData.Key.TrackNumber)
        add_k("Year", QMediaMetaData.Key.Year)

        self.info_text.setText("\n".join(str(x) for x in lines if x is not None))

    def copy_media_info(self):
        txt = self.info_text.toPlainText().strip()
        if not txt:
            return
        QApplication.clipboard().setText(txt)
        self.status.showMessage("Media info copied to clipboard", 2000)

    # ------------------- Reset / About -------------------

    def reset_player(self):
        self.stop()
        self.media.setSource(QUrl())
        self.seek_slider.setValue(0)
        self.seek_slider.setRange(0, 0)
        self.now_label.setText("No media loaded")
        self.info_text.setText("")
        self.current_index = -1
        self._ab_enabled = False
        self._ab_a = 0
        self._ab_b = 0
        self._playlist_render()
        self.status.showMessage("Reset complete", 2000)
        self._log("Reset complete")

    def about(self):
        msg = QMessageBox(self)
        msg.setWindowTitle(f"About {APP_NAME}")

        icon_path_png = APP_DIR / "plp_logo.png"
        if icon_path_png.exists():
            pix = QPixmap(str(icon_path_png))
            if not pix.isNull():
                msg.setIconPixmap(pix.scaledToWidth(96, Qt.TransformationMode.SmoothTransformation))

        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(f"""
            <div style="color:#e7eefc;">
                <h3>{APP_NAME}</h3>
                <p>
                    Created by <b>ParrotHat</b><br/>
                    Built with Python + PyQt6 (QtMultimedia)
                </p>
                <p>
                    Playlist, streaming, screenshots, A-B loop, shortcuts, and metadata panel.
                </p>
                <p>
                    © 2025 {ORG_NAME}
                </p>
            </div>
        """)
        msg.exec()

    # ------------------- Drag & Drop -------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        files = []
        for u in urls:
            if u.isLocalFile():
                files.append(u.toLocalFile())
            else:
                self.entries.append(PlaylistEntry(u, u.toString()))
        if files:
            self.add_files_to_playlist(files, auto_play=(self.current_index < 0))
        else:
            self._playlist_render()

    # ------------------- Recent -------------------

    def _load_recent(self) -> list[str]:
        try:
            raw = self.settings.value("recent/files", "[]")
            data = json.loads(raw) if isinstance(raw, str) else []
            if isinstance(data, list):
                return [str(x) for x in data if isinstance(x, str)]
        except Exception:
            pass
        return []

    def _save_recent(self):
        self.settings.setValue("recent/files", json.dumps(self._recent[:20]))

    def _add_recent(self, path: str):
        path = str(Path(path))
        if path in self._recent:
            self._recent.remove(path)
        self._recent.insert(0, path)
        self._recent = self._recent[:20]
        self._save_recent()
        self._rebuild_recent_menu()

    def clear_recent(self):
        self._recent = []
        self._save_recent()
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self):
        self.recent_menu.clear()
        if not self._recent:
            act = QAction("(empty)", self)
            act.setEnabled(False)
            self.recent_menu.addAction(act)
            return

        for p in self._recent[:12]:
            name = Path(p).name
            act = QAction(name, self)
            act.setToolTip(p)

            def _open_recent(_, path=p):
                if Path(path).exists():
                    self.add_files_to_playlist([path], auto_play=True)
                else:
                    self._notify("File not found.")
                    if path in self._recent:
                        self._recent.remove(path)
                        self._save_recent()
                        self._rebuild_recent_menu()

            act.triggered.connect(_open_recent)
            self.recent_menu.addAction(act)

    # ------------------- Persistence -------------------

    def _restore_state(self):
        # docks
        geo = self.settings.value("window/geometry", None)
        st = self.settings.value("window/state", None)
        if geo:
            self.restoreGeometry(geo)
        if st:
            self.restoreState(st)

        # repeat/shuffle
        self.repeat_mode = self.repeat_box.currentText()
        self.shuffle_enabled = self.shuffle_btn.isChecked()

        # mute icon
        self.t_act_mute.setIcon(self._svg_icon("volume-x" if self.audio.isMuted() else "volume-2", 20))

        # playback rate
        self.change_playback_rate(self.rate_box.currentText())

    def closeEvent(self, event):
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("window/state", self.saveState())
        self.settings.setValue("playback/repeat", self.repeat_box.currentText())
        self.settings.setValue("playback/shuffle", self.shuffle_btn.isChecked())
        self.settings.setValue("playback/rate", self.rate_box.currentText())
        super().closeEvent(event)

    # ------------------- Helpers -------------------

    def _fmt_time(self, ms: int) -> str:
        if ms <= 0:
            return "00:00"
        t = QTime(0, 0, 0).addMSecs(ms)
        if ms >= 3600_000:
            return t.toString("hh:mm:ss")
        return t.toString("mm:ss")

    def _fmt_bytes(self, n: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        x = float(n)
        i = 0
        while x >= 1024 and i < len(units) - 1:
            x /= 1024.0
            i += 1
        if i == 0:
            return f"{int(x)} {units[i]}"
        return f"{x:.2f} {units[i]}"

    def _notify(self, text: str):
        QMessageBox.warning(self, APP_NAME, text)

    def _log(self, text: str):
        self.log_text.append(text)
        self.status.showMessage(text, 2500)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # App icon (optional)
    ico = APP_DIR / "plp_logo.ico"
    if ico.exists():
        app.setWindowIcon(QIcon(str(ico)))

    win = ParsLocalPlayer()
    win.show()
    sys.exit(app.exec())
