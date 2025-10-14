import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QSlider, QMenuBar, QLabel, QMessageBox, QStatusBar, QComboBox
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QTime
from PyQt6.QtGui import QAction, QPixmap, QIcon


class ParsLocalPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pars Local Player")
        self.setGeometry(100, 100, 980, 620)

        # --- style ---
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QPushButton { background-color: #333; color: white; border-radius: 6px; padding: 6px 14px; }
            QPushButton:hover { background-color: #444; }
            QLabel { color: #ccc; }
            QSlider::groove:horizontal { background: #222; height: 6px; border-radius: 3px; }
            QSlider::handle:horizontal { background: #ff7a00; width: 14px; border-radius: 7px; }
            QComboBox { background-color: #333; color: white; border-radius: 4px; padding: 4px; }
        """)

        # --- multimedia core ---
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.8)
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)

        # --- controls ---
        self.open_btn = QPushButton("📂 Open")
        self.play_btn = QPushButton("▶ Play")
        self.pause_btn = QPushButton("⏸ Pause")
        self.stop_btn = QPushButton("⏹ Stop")
        self.mute_btn = QPushButton("🔇 Mute")

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_label = QLabel("🔊 80%")

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.time_label = QLabel("00:00 / 00:00")

        self.loop_box = QComboBox()
        self.loop_box.addItems(["No Loop", "Loop Once", "Loop Infinite"])
        self.rate_box = QComboBox()
        self.rate_box.addItems(["0.5x", "1.0x", "1.25x", "1.5x", "2.0x"])

        # --- layout ---
        top_bar = QHBoxLayout()
        for w in [self.open_btn, self.play_btn, self.pause_btn, self.stop_btn, self.mute_btn]:
            top_bar.addWidget(w)

        mid_bar = QHBoxLayout()
        mid_bar.addWidget(self.seek_slider)
        mid_bar.addWidget(self.time_label)

        bottom_bar = QHBoxLayout()
        bottom_bar.addWidget(self.volume_label)
        bottom_bar.addWidget(self.volume_slider)
        bottom_bar.addStretch(1)
        bottom_bar.addWidget(QLabel("Loop:"))
        bottom_bar.addWidget(self.loop_box)
        bottom_bar.addWidget(QLabel("Speed:"))
        bottom_bar.addWidget(self.rate_box)

        layout = QVBoxLayout()
        layout.addWidget(self.video_widget)
        layout.addLayout(mid_bar)
        layout.addLayout(top_bar)
        layout.addLayout(bottom_bar)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # --- menu ---
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        file_menu = menubar.addMenu("File")
        file_menu.addAction("Open File", self.open_file)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        info_menu = menubar.addMenu("Info")
        info_menu.addAction("Show Metadata", self.show_metadata)
        info_menu.addAction("About Pars Local Player", self.show_about)

        # --- status ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # --- signals ---
        self.open_btn.clicked.connect(self.open_file)
        self.play_btn.clicked.connect(self.media_player.play)
        self.pause_btn.clicked.connect(self.media_player.pause)
        self.stop_btn.clicked.connect(self.media_player.stop)
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.volume_slider.valueChanged.connect(self.adjust_volume)
        self.seek_slider.sliderMoved.connect(self.set_position)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.loop_box.currentIndexChanged.connect(self.set_loop_mode)
        self.rate_box.currentIndexChanged.connect(self.change_playback_rate)

        self.metadata_dict = {}

    # --- basic control ---
    def open_file(self):
        file_filter = "Media Files (*.mp3 *.mp4 *.avi *.ogg);;All Files (*)"
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Media File", "", file_filter)
        if file_name:
            self.media_player.setSource(QUrl.fromLocalFile(file_name))
            self.media_player.play()
            self.status_bar.showMessage(f"Playing: {file_name.split('/')[-1]}")

    def adjust_volume(self):
        v = self.volume_slider.value()
        self.audio_output.setVolume(v / 100)
        self.volume_label.setText(f"🔊 {v}%")

    def toggle_mute(self):
        state = not self.audio_output.isMuted()
        self.audio_output.setMuted(state)
        self.mute_btn.setText("🔈 Unmute" if state else "🔇 Mute")

    def duration_changed(self, duration):
        self.seek_slider.setRange(0, duration)

    def position_changed(self, pos):
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(pos)
        self.seek_slider.blockSignals(False)
        self.update_time_label(pos)

    def set_position(self, position):
        self.media_player.setPosition(position)

    def update_time_label(self, pos):
        dur = self.media_player.duration()
        cur = QTime(0, 0, 0).addMSecs(pos)
        total = QTime(0, 0, 0).addMSecs(dur)
        self.time_label.setText(f"{cur.toString('mm:ss')} / {total.toString('mm:ss')}")

    # --- metadata ---
    def on_media_status_changed(self, status):
        from PyQt6.QtMultimedia import QMediaPlayer as _P
        if status in (_P.MediaStatus.LoadedMedia, _P.MediaStatus.BufferedMedia):
            self.read_metadata()

    def read_metadata(self):
        md = self.media_player.metaData()
        self.metadata_dict.clear()
        if md is None:
            self.status_bar.showMessage("No metadata interface.")
            return

        def safe_val(name):
            key = getattr(QMediaMetaData.Key, name, None)
            if key is None:
                return None
            try:
                return md.value(key)
            except Exception:
                return None

        # Získaj údaje, ktoré Qt naozaj pozná v každej verzii
        data = {
            "Title": safe_val("Title"),
            "ContributingArtist": safe_val("ContributingArtist"),
            "AlbumTitle": safe_val("AlbumTitle"),
            "Genre": safe_val("Genre"),
            "Year": safe_val("Year"),
            "Comment": safe_val("Comment"),
            "AudioCodec": safe_val("AudioCodec"),
            "VideoCodec": safe_val("VideoCodec"),
            "Resolution": safe_val("Resolution"),
            "Duration": QTime(0, 0, 0).addMSecs(self.media_player.duration()).toString("mm:ss")
        }

        self.metadata_dict = {k: v for k, v in data.items() if v not in (None, "", [])}
        self.status_bar.showMessage("Metadata loaded" if self.metadata_dict else "No metadata tags in file")

    def show_metadata(self):
        if not self.metadata_dict:
            QMessageBox.information(self, "Metadata", "No metadata available.")
            return
        html = "<h3 style='color:#ff7a00;'>Media Metadata</h3><ul>"
        for k, v in self.metadata_dict.items():
            html += f"<li><b>{k}</b>: {v}</li>"
        html += "</ul>"
        QMessageBox.information(self, "Metadata", html)

    # --- loop & speed ---
    def set_loop_mode(self):
        mode = self.loop_box.currentText()
        if mode == "No Loop":
            self.media_player.setLoops(1)
        elif mode == "Loop Once":
            self.media_player.setLoops(2)
        elif mode == "Loop Infinite":
            self.media_player.setLoops(-1)
        self.status_bar.showMessage(f"Loop mode: {mode}")

    def change_playback_rate(self):
        rate = float(self.rate_box.currentText().replace("x", ""))
        self.media_player.setPlaybackRate(rate)
        self.status_bar.showMessage(f"Playback speed: {rate}x")

    # --- about ---
    def show_about(self):
        about = QMessageBox(self)
        about.setWindowTitle("About Pars Local Player")
        pix = QPixmap("plp_logo.png")
        if not pix.isNull():
            about.setIconPixmap(pix.scaledToWidth(90, Qt.TransformationMode.SmoothTransformation))
        about.setTextFormat(Qt.TextFormat.RichText)
        about.setText("""
        <h3 style='color:#ff7a00;'>Pars Local Player</h3>
        <p style='color:#ccc;'>Open-source media player by <b>Damián Mazanec</b>.</p>
        <p style='color:#ccc;'>Supports: MP3, MP4, AVI, OGG</p>
        <p style='color:#ccc;'>Source: <a href='https://github.com/parrothat/plp'>github.com/parrothat/plp</a></p>
        """)
        about.exec()


# --- run ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("plp_logo.ico"))
    p = ParsLocalPlayer()
    p.show()
    sys.exit(app.exec())
