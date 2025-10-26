import sys, os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QSlider, QMenuBar, QLabel, QMessageBox, QStatusBar,
    QComboBox, QTextEdit
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QTime
from PyQt6.QtGui import QIcon, QPixmap, QFont


class ParsLocalPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pars Local Player 2.0")
        self.resize(1280, 760)

        # --- Font & Style ---
        font = QFont("Inter", 10)
        self.setFont(font)
        self.setStyleSheet("""
            QMainWindow { background-color:#ffffff; }
            QPushButton {
                background-color:#ffffff;
                color:#0066ff;
                border:1px solid #0066ff;
                border-radius:8px;
                padding:6px 12px;
            }
            QPushButton:hover { background-color:#eaf2ff; }
            QLabel { color:#0066ff; }
            QSlider::groove:horizontal {
                background:#d9e3ff; height:6px; border-radius:3px;
            }
            QSlider::handle:horizontal {
                background:#0066ff; width:14px; border-radius:7px;
            }
            QComboBox {
                background-color:#ffffff; color:#0066ff;
                border:1px solid #0066ff; border-radius:4px; padding:4px;
            }
            QMenuBar { background-color:#f0f0f0; color:#0066ff; }
            QMenuBar::item:selected { background-color:#dce7ff; }
            QTextEdit {
                background-color:#f6f9ff; color:#0066ff;
                border:1px solid #bcd0ff;
                font-family:Consolas; font-size:9pt;
            }
        """)

        # --- Multimedia Core ---
        self.media = QMediaPlayer()
        self.audio = QAudioOutput()
        self.media.setAudioOutput(self.audio)
        self.video = QVideoWidget()
        self.media.setVideoOutput(self.video)

        # --- Buttons ---
        self.btn_open = QPushButton("📂 Open")
        self.btn_stream = QPushButton("🌐 Stream")
        self.btn_play = QPushButton("▶ Play")
        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_mute = QPushButton("🔇 Mute")
        self.btn_ss = QPushButton("📸 Screenshot")
        self.btn_reset = QPushButton("🔁 Reset")

        # --- Sliders ---
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_label = QLabel("🔊 80%")

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.time_label = QLabel("00:00 / 00:00")

        # --- Loop & Rate ---
        self.loop_box = QComboBox()
        self.loop_box.addItems(["No Loop", "Loop Once", "Loop Infinite"])
        self.rate_box = QComboBox()
        self.rate_box.addItems(["0.5x", "1.0x", "1.25x", "1.5x", "2.0x"])

        # --- Codec Info ---
        self.codec_info = QTextEdit()
        self.codec_info.setReadOnly(True)
        self.codec_info.setFixedHeight(100)
        self.codec_info.setText("Codec Info: (nothing loaded)")

        # --- Layouts ---
        top_bar = QHBoxLayout()
        for w in [self.btn_open, self.btn_stream, self.btn_play, self.btn_pause,
                  self.btn_stop, self.btn_ss, self.btn_mute, self.btn_reset]:
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
        layout.addWidget(self.video, stretch=30)  # extra veľké video
        layout.addLayout(mid_bar, stretch=1)
        layout.addLayout(top_bar, stretch=1)
        layout.addLayout(bottom_bar, stretch=1)
        layout.addWidget(self.codec_info, stretch=2)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # --- Menu / Status ---
        mbar = QMenuBar(self)
        self.setMenuBar(mbar)
        file_menu = mbar.addMenu("File")
        file_menu.addAction("Open File", self.open_file)
        file_menu.addAction("Open Stream", self.open_stream)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)
        info_menu = mbar.addMenu("Info")
        info_menu.addAction("About", self.about)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

        # --- Signals ---
        self.btn_open.clicked.connect(self.open_file)
        self.btn_stream.clicked.connect(self.open_stream)
        self.btn_play.clicked.connect(self.media.play)
        self.btn_pause.clicked.connect(self.media.pause)
        self.btn_stop.clicked.connect(self.media.stop)
        self.btn_mute.clicked.connect(self.toggle_mute)
        self.btn_reset.clicked.connect(self.reset_player)
        self.btn_ss.clicked.connect(self.screenshot)
        self.volume_slider.valueChanged.connect(self.adjust_volume)
        self.seek_slider.sliderMoved.connect(self.media.setPosition)
        self.media.positionChanged.connect(self.update_seek)
        self.media.durationChanged.connect(lambda d: self.seek_slider.setRange(0, d))
        self.media.metaDataChanged.connect(self.show_codec_info)
        self.loop_box.currentIndexChanged.connect(self.set_loop_mode)
        self.rate_box.currentIndexChanged.connect(self.change_playback_rate)

        self.audio.setVolume(0.8)

    # --- Media ---
    def open_file(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Open Media", "",
            "Media Files (*.mp4 *.mkv *.avi *.mov *.webm *.mp3 *.flac *.ogg *.wav *.m4a);;All Files (*)"
        )
        if f:
            self.media.setSource(QUrl.fromLocalFile(f))
            self.media.play()
            self.status.showMessage(f"Playing: {os.path.basename(f)}")

    def open_stream(self):
        from PyQt6.QtWidgets import QInputDialog
        url, ok = QInputDialog.getText(self, "Open Stream", "Enter URL (HTTP/RTSP/HLS):")
        if ok and url:
            self.media.setSource(QUrl(url))
            self.media.play()
            self.status.showMessage(f"Streaming from {url}")

    def screenshot(self):
        frame = self.video.grab()
        if not frame.isNull():
            path, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", "", "PNG Image (*.png)")
            if path:
                frame.save(path)
                self.status.showMessage(f"Saved screenshot: {path}")

    def reset_player(self):
        self.media.stop()
        self.seek_slider.setValue(0)
        self.codec_info.clear()
        self.status.showMessage("Reset complete")

    def adjust_volume(self):
        v = self.volume_slider.value()
        self.audio.setVolume(v / 100)
        self.volume_label.setText(f"🔊 {v}%")

    def toggle_mute(self):
        muted = not self.audio.isMuted()
        self.audio.setMuted(muted)
        self.btn_mute.setText("🔈 Unmute" if muted else "🔇 Mute")

    def update_seek(self, pos):
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(pos)
        self.seek_slider.blockSignals(False)
        dur = self.media.duration()
        cur = QTime(0, 0, 0).addMSecs(pos)
        total = QTime(0, 0, 0).addMSecs(dur)
        self.time_label.setText(f"{cur.toString('mm:ss')} / {total.toString('mm:ss')}")

    def show_codec_info(self):
        md = self.media.metaData()
        if not md:
            return
        acodec = md.value(QMediaMetaData.Key.AudioCodec)
        vcodec = md.value(QMediaMetaData.Key.VideoCodec)
        dur = QTime(0, 0, 0).addMSecs(self.media.duration()).toString("mm:ss")
        info = []
        if vcodec: info.append(f"🎞 Video Codec: {vcodec}")
        if acodec: info.append(f"🎧 Audio Codec: {acodec}")
        info.append(f"⏱ Duration: {dur}")
        self.codec_info.setText("\n".join(info))

    def set_loop_mode(self):
        mode = self.loop_box.currentText()
        if "Infinite" in mode:
            self.media.setLoops(-1)
        elif "Once" in mode:
            self.media.setLoops(2)
        else:
            self.media.setLoops(1)

    def change_playback_rate(self):
        rate = float(self.rate_box.currentText().replace("x", ""))
        self.media.setPlaybackRate(rate)

    def about(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("About Pars Local Player 2.0 Vetverti")
        pix = QPixmap("plp_logo.png")
        if not pix.isNull():
            msg.setIconPixmap(pix.scaledToWidth(90, Qt.TransformationMode.SmoothTransformation))
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText("""
        <h3 style='color:#0066ff;'>Pars Local Player 2.0 – Vetverti Edition</h3>
        <p style='color:#0066ff;'>
        Created by <b>ParrotHat/b><br>
        Built with Python + QtMultimedia + FFmpeg
        </p>
        <p style='color:#0066ff;'>
        Vetverti Edition introduces a new <b>Cobalt UI</b> look — light, clean and fast.<br>
        Now with <b>streaming</b>, <b>screenshots</b>, and <b>codec info panel</b>.
        </p>
        <p style='color:#0066ff;'>
        <a href='https://github.com/parrothat/plp'>github.com/parrothat/plp</a><br>
        © 2025 ParrotHat Foundation
        </p>
        """)
        msg.exec()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("plp_logo.ico"))
    win = ParsLocalPlayer()
    win.show()
    sys.exit(app.exec())
