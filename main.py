import sys
import os
import subprocess
import zipfile
import shutil
import requests  # For downloading ffmpeg if needed
from io import BytesIO
from PyQt5 import QtWidgets, QtGui, QtCore
from PIL import Image
from urllib.request import urlopen, Request  # For downloading images in Credits tab

# If you want fallback to OpenCV for video durations
try:
    import cv2
except ImportError:
    cv2 = None

# If you want fallback to Mutagen for audio durations
try:
    from mutagen import File as MutagenFile
except ImportError:
    MutagenFile = None

# Set the OpenGL context attribute for Qt WebEngine before creating the QApplication
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)

# Multimedia imports for video/audio preview
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

# -------------------------------
# Custom error dialog (for copyable error messages)
# -------------------------------
def show_error_dialog(title, error_text):
    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle(title)
    layout = QtWidgets.QVBoxLayout(dialog)
    text_edit = QtWidgets.QTextEdit()
    text_edit.setReadOnly(True)
    text_edit.setPlainText(error_text)
    layout.addWidget(text_edit)
    button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
    button_box.accepted.connect(dialog.accept)
    layout.addWidget(button_box)
    dialog.exec_()

# -------------------------------
# 1. Download / unpack ffmpeg if not present
# -------------------------------
def ensure_ffmpeg_exists(ffmpeg_folder="ffmpeg_bin"):
    """
    Checks if ffmpeg.exe and ffprobe.exe exist in ffmpeg_folder.
    If not, downloads a portable build from a known URL and extracts them.
    Returns the paths to ffmpeg_exe and ffprobe_exe.
    NOTE: Replace the FF_URL below with a stable, trusted link to a Windows build of ffmpeg.
    """
    FF_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

    ffmpeg_path = os.path.join(ffmpeg_folder, "ffmpeg.exe")
    ffprobe_path = os.path.join(ffmpeg_folder, "ffprobe.exe")

    if not os.path.exists(ffmpeg_path) or not os.path.exists(ffprobe_path):
        print("FFmpeg not found locally. Downloading...")
        os.makedirs(ffmpeg_folder, exist_ok=True)
        resp = requests.get(FF_URL, stream=True)
        resp.raise_for_status()
        zip_data = BytesIO(resp.content)
        with zipfile.ZipFile(zip_data) as zf:
            for member in zf.namelist():
                low_member = member.lower().replace("\\", "/")
                if "ffmpeg.exe" in low_member or "ffprobe.exe" in low_member:
                    filename = os.path.basename(member)
                    if not filename:
                        continue
                    target_path = os.path.join(ffmpeg_folder, filename)
                    with open(target_path, "wb") as out_file:
                        out_file.write(zf.read(member))
        print("FFmpeg downloaded and extracted to:", ffmpeg_folder)
    return ffmpeg_path, ffprobe_path

ffmpeg_exe, ffprobe_exe = ensure_ffmpeg_exists()

# -------------------------------
# Helper functions
# -------------------------------
def get_duration(filepath):
    """
    Get video duration with ffprobe, fallback to OpenCV if available.
    """
    try:
        cmd = [
            ffprobe_exe, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            filepath
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        dur_str = result.stdout.strip()
        dur_val = float(dur_str)
        if dur_val <= 0:
            raise ValueError("Non-positive duration")
        return dur_val
    except Exception as e:
        print("ffprobe for video failed:", e)
        if cv2:
            try:
                cap = cv2.VideoCapture(filepath)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    if fps > 0 and frames > 0:
                        return frames / fps
            except:
                pass
        return None

def get_audio_duration(filepath):
    """
    Get audio duration with ffprobe, fallback to Mutagen if available.
    """
    try:
        cmd = [
            ffprobe_exe, "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            filepath
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        dur_str = result.stdout.strip()
        dur_val = float(dur_str)
        if dur_val <= 0:
            raise ValueError("Non-positive duration")
        return dur_val
    except Exception as e:
        print("ffprobe for audio failed:", e)
        if MutagenFile:
            try:
                audio = MutagenFile(filepath)
                if audio and hasattr(audio.info, 'length'):
                    return audio.info.length
            except:
                pass
        return None

def find_quality_for_target_size(img, target_size_bytes, min_quality=10, max_quality=95):
    best_quality = None
    best_diff = float('inf')
    low = min_quality
    high = max_quality
    best_buffer = None
    while low <= high:
        mid = (low + high) // 2
        buffer = BytesIO()
        img.save(buffer, "JPEG", quality=mid)
        size = buffer.tell()
        diff = abs(size - target_size_bytes)
        if diff < best_diff:
            best_diff = diff
            best_quality = mid
            best_buffer = buffer.getvalue()
        if size > target_size_bytes:
            high = mid - 1
        else:
            low = mid + 1
    return best_quality, best_buffer

# -------------------------------
# Modern Style Sheet
# -------------------------------
modernStyle = """
QWidget {
    background-color: #1d1f21;
    color: #c5c8c6;
    font-family: 'Segoe UI', sans-serif;
    font-size: 10pt;
}
QPushButton {
    background-color: #5e0080;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 8px;
}
QPushButton:hover {
    background-color: #7000a0;
}
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #282a2e;
    color: #c5c8c6;
    border: 1px solid #373b41;
    border-radius: 4px;
    padding: 4px;
}
QTabWidget::pane {
    border: 1px solid #5e0080;
}
QTabBar::tab {
    background: #282a2e;
    color: #c5c8c6;
    padding: 10px;
    border: 1px solid #373b41;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background: #5e0080;
}
QCheckBox {
    spacing: 6px;
}
"""

#############################
# ImageCompressorTab
#############################
class ImageCompressorTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.imagePath = ""
        self.initUI()

    def initUI(self):
        layout = QtWidgets.QVBoxLayout()
        fileLayout = QtWidgets.QHBoxLayout()
        self.fileLabel = QtWidgets.QLabel("No image selected")
        selectBtn = QtWidgets.QPushButton("Select Image")
        selectBtn.clicked.connect(self.selectImage)
        previewBtn = QtWidgets.QPushButton("Preview Image")
        previewBtn.clicked.connect(self.previewImage)
        fileLayout.addWidget(self.fileLabel)
        fileLayout.addWidget(selectBtn)
        fileLayout.addWidget(previewBtn)
        layout.addLayout(fileLayout)

        qualityLayout = QtWidgets.QHBoxLayout()
        qualityLabel = QtWidgets.QLabel("Quality (1-100):")
        self.qualitySpin = QtWidgets.QSpinBox()
        self.qualitySpin.setRange(1, 100)
        self.qualitySpin.setValue(85)
        qualityLayout.addWidget(qualityLabel)
        qualityLayout.addWidget(self.qualitySpin)
        layout.addLayout(qualityLayout)

        resizeLayout = QtWidgets.QHBoxLayout()
        self.resizeCheck = QtWidgets.QCheckBox("Resize Image")
        widthLabel = QtWidgets.QLabel("Width:")
        self.widthSpin = QtWidgets.QSpinBox()
        self.widthSpin.setRange(1, 10000)
        self.widthSpin.setValue(800)
        heightLabel = QtWidgets.QLabel("Height:")
        self.heightSpin = QtWidgets.QSpinBox()
        self.heightSpin.setRange(1, 10000)
        self.heightSpin.setValue(600)
        resizeLayout.addWidget(self.resizeCheck)
        resizeLayout.addWidget(widthLabel)
        resizeLayout.addWidget(self.widthSpin)
        resizeLayout.addWidget(heightLabel)
        resizeLayout.addWidget(self.heightSpin)
        layout.addLayout(resizeLayout)

        targetLayout = QtWidgets.QHBoxLayout()
        self.useTargetSizeCheck = QtWidgets.QCheckBox("Use Target File Size")
        targetLabel = QtWidgets.QLabel("Target Size (MB):")
        self.targetSizeSpin = QtWidgets.QDoubleSpinBox()
        self.targetSizeSpin.setRange(0.1, 100)
        self.targetSizeSpin.setDecimals(2)
        self.targetSizeSpin.setValue(1.0)
        targetLayout.addWidget(self.useTargetSizeCheck)
        targetLayout.addWidget(targetLabel)
        targetLayout.addWidget(self.targetSizeSpin)
        layout.addLayout(targetLayout)

        compressBtn = QtWidgets.QPushButton("Compress Image")
        compressBtn.clicked.connect(self.compressImage)
        layout.addWidget(compressBtn)

        btnLayout = QtWidgets.QHBoxLayout()
        resetBtn = QtWidgets.QPushButton("Reset")
        resetBtn.clicked.connect(self.resetFields)
        helpBtn = QtWidgets.QPushButton("Help")
        helpBtn.clicked.connect(self.showHelp)
        closeBtn = QtWidgets.QPushButton("Close")
        closeBtn.clicked.connect(QtWidgets.qApp.quit)
        btnLayout.addWidget(resetBtn)
        btnLayout.addWidget(helpBtn)
        btnLayout.addWidget(closeBtn)
        layout.addLayout(btnLayout)

        self.setLayout(layout)

    def resetFields(self):
        self.fileLabel.setText("No image selected")
        self.imagePath = ""
        self.qualitySpin.setValue(85)
        self.resizeCheck.setChecked(False)
        self.widthSpin.setValue(800)
        self.heightSpin.setValue(600)
        self.useTargetSizeCheck.setChecked(False)
        self.targetSizeSpin.setValue(1.0)

    def showHelp(self):
        QtWidgets.QMessageBox.information(self, "Image Compressor Help",
            "Select an image file, choose quality, optionally resize or set a target file size, then click 'Compress Image'.")

    def selectImage(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)")
        if fileName:
            self.imagePath = fileName
            self.fileLabel.setText(os.path.basename(fileName))

    def previewImage(self):
        if not self.imagePath:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select an image first.")
            return
        previewDialog = QtWidgets.QDialog(self)
        previewDialog.setWindowTitle("Image Preview")
        layout = QtWidgets.QVBoxLayout(previewDialog)
        label = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap(self.imagePath)
        scaled_pixmap = pixmap.scaled(800, 600, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        label.setPixmap(scaled_pixmap)
        layout.addWidget(label)
        previewDialog.exec_()

    def compressImage(self):
        if not self.imagePath:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select an image file first.")
            return
        try:
            img = Image.open(self.imagePath)
            if self.resizeCheck.isChecked():
                img = img.resize(
                    (self.widthSpin.value(), self.heightSpin.value()),
                    Image.ANTIALIAS
                )
            savePath, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save Compressed Image", "",
                "JPEG Files (*.jpg);;PNG Files (*.png);;All Files (*)")
            if not savePath:
                return

            ext = os.path.splitext(savePath)[1].lower()
            if self.useTargetSizeCheck.isChecked() and ext in [".jpg", ".jpeg"]:
                target_size_bytes = self.targetSizeSpin.value() * 1024 * 1024
                quality, buffer = find_quality_for_target_size(img, target_size_bytes)
                if quality is not None:
                    with open(savePath, "wb") as f:
                        f.write(buffer)
                    QtWidgets.QMessageBox.information(self, "Success",
                        f"Image compressed using quality={quality}!")
                else:
                    show_error_dialog("Warning", "Could not determine an optimal quality setting.")
            else:
                quality = self.qualitySpin.value()
                if ext in [".jpg", ".jpeg"]:
                    img = img.convert("RGB")
                    img.save(savePath, "JPEG", quality=quality)
                elif ext == ".png":
                    img.save(savePath, "PNG", optimize=True)
                else:
                    img = img.convert("RGB")
                    img.save(savePath, "JPEG", quality=quality)
                QtWidgets.QMessageBox.information(self, "Success",
                    "Image compressed successfully!")
        except Exception as e:
            show_error_dialog("Error", f"Failed to compress image.\nError: {str(e)}")

#############################
# VideoCompressorTab
#############################
class VideoCompressorTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.videoPath = ""
        self.initUI()

    def initUI(self):
        layout = QtWidgets.QVBoxLayout()

        fileLayout = QtWidgets.QHBoxLayout()
        self.fileLabel = QtWidgets.QLabel("No video selected")
        selectBtn = QtWidgets.QPushButton("Select Video")
        selectBtn.clicked.connect(self.selectVideo)
        previewBtn = QtWidgets.QPushButton("Preview Video")
        previewBtn.clicked.connect(self.previewVideo)
        fileLayout.addWidget(self.fileLabel)
        fileLayout.addWidget(selectBtn)
        fileLayout.addWidget(previewBtn)
        layout.addLayout(fileLayout)

        bitrateLayout = QtWidgets.QHBoxLayout()
        bitrateLabel = QtWidgets.QLabel("Bitrate (kbps):")
        self.bitrateSpin = QtWidgets.QSpinBox()
        self.bitrateSpin.setRange(100, 10000)
        self.bitrateSpin.setValue(1000)
        bitrateLayout.addWidget(bitrateLabel)
        bitrateLayout.addWidget(self.bitrateSpin)
        layout.addLayout(bitrateLayout)

        resLayout = QtWidgets.QHBoxLayout()
        widthLabel = QtWidgets.QLabel("Width:")
        self.videoWidthSpin = QtWidgets.QSpinBox()
        self.videoWidthSpin.setRange(1, 10000)
        self.videoWidthSpin.setValue(640)
        heightLabel = QtWidgets.QLabel("Height:")
        self.videoHeightSpin = QtWidgets.QSpinBox()
        self.videoHeightSpin.setRange(1, 10000)
        self.videoHeightSpin.setValue(480)
        resLayout.addWidget(widthLabel)
        resLayout.addWidget(self.videoWidthSpin)
        resLayout.addWidget(heightLabel)
        resLayout.addWidget(self.videoHeightSpin)
        layout.addLayout(resLayout)

        frLayout = QtWidgets.QHBoxLayout()
        frLabel = QtWidgets.QLabel("Frame Rate (fps):")
        self.frameRateSpin = QtWidgets.QSpinBox()
        self.frameRateSpin.setRange(1, 120)
        self.frameRateSpin.setValue(30)
        frLayout.addWidget(frLabel)
        frLayout.addWidget(self.frameRateSpin)
        layout.addLayout(frLayout)

        codecLayout = QtWidgets.QHBoxLayout()
        codecLabel = QtWidgets.QLabel("Codec:")
        self.codecCombo = QtWidgets.QComboBox()
        self.codecCombo.addItem("H.264 (libx264)", "libx264")
        self.codecCombo.addItem("HEVC (libx265)", "libx265")
        codecLayout.addWidget(codecLabel)
        codecLayout.addWidget(self.codecCombo)
        layout.addLayout(codecLayout)

        targetLayout = QtWidgets.QHBoxLayout()
        self.useTargetSizeCheck = QtWidgets.QCheckBox("Use Target File Size")
        targetLabel = QtWidgets.QLabel("Target Size (MB):")
        self.targetSizeSpin = QtWidgets.QDoubleSpinBox()
        self.targetSizeSpin.setRange(0.1, 500)
        self.targetSizeSpin.setDecimals(2)
        self.targetSizeSpin.setValue(10.0)
        targetLayout.addWidget(self.useTargetSizeCheck)
        targetLayout.addWidget(targetLabel)
        targetLayout.addWidget(self.targetSizeSpin)
        layout.addLayout(targetLayout)

        compressBtn = QtWidgets.QPushButton("Compress Video")
        compressBtn.clicked.connect(self.compressVideo)
        layout.addWidget(compressBtn)

        btnLayout = QtWidgets.QHBoxLayout()
        resetBtn = QtWidgets.QPushButton("Reset")
        resetBtn.clicked.connect(self.resetFields)
        helpBtn = QtWidgets.QPushButton("Help")
        helpBtn.clicked.connect(self.showHelp)
        closeBtn = QtWidgets.QPushButton("Close")
        closeBtn.clicked.connect(QtWidgets.qApp.quit)
        btnLayout.addWidget(resetBtn)
        btnLayout.addWidget(helpBtn)
        btnLayout.addWidget(closeBtn)
        layout.addLayout(btnLayout)

        self.setLayout(layout)

    def resetFields(self):
        self.fileLabel.setText("No video selected")
        self.videoPath = ""
        self.bitrateSpin.setValue(1000)
        self.videoWidthSpin.setValue(640)
        self.videoHeightSpin.setValue(480)
        self.frameRateSpin.setValue(30)
        self.codecCombo.setCurrentIndex(0)
        self.useTargetSizeCheck.setChecked(False)
        self.targetSizeSpin.setValue(10.0)

    def showHelp(self):
        QtWidgets.QMessageBox.information(self, "Video Compressor Help",
            "Select a video file, set bitrate, resolution, frame rate, and codec.\n"
            "Optionally, enable target file size to recalculate video bitrate.\n"
            "Then click 'Compress Video'.")

    def selectVideo(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Video", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*)")
        if fileName:
            self.videoPath = fileName
            self.fileLabel.setText(os.path.basename(fileName))

    def previewVideo(self):
        if not self.videoPath:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select a video file first.")
            return
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Video Preview")
        dlg.resize(800, 600)
        layout = QtWidgets.QVBoxLayout(dlg)
        videoWidget = QVideoWidget()
        layout.addWidget(videoWidget)
        player = QMediaPlayer(dlg)
        player.setVideoOutput(videoWidget)
        url = QtCore.QUrl.fromLocalFile(self.videoPath)
        player.setMedia(QMediaContent(url))
        player.play()
        dlg.exec_()

    def compressVideo(self):
        if not self.videoPath:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select a video file first.")
            return
        try:
            savePath, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save Compressed Video", "",
                "MP4 Files (*.mp4);;All Files (*)")
            if not savePath:
                return

            width = self.videoWidthSpin.value()
            height = self.videoHeightSpin.value()
            fps = self.frameRateSpin.value()
            codec = self.codecCombo.currentData()

            if self.useTargetSizeCheck.isChecked():
                dur = get_duration(self.videoPath)
                if not dur:
                    show_error_dialog("Warning", "Could not determine video duration.")
                    return
                total_bits = self.targetSizeSpin.value() * 1024 * 1024 * 8
                audio_bitrate = 128000
                audio_bits = audio_bitrate * dur
                video_bits = total_bits - audio_bits
                if video_bits <= 0:
                    show_error_dialog("Warning", "Target size too small for the audio track.")
                    return
                computed_bitrate = int((video_bits / dur) / 1000)
                bitrate = computed_bitrate
            else:
                bitrate = self.bitrateSpin.value()

            command = [
                ffmpeg_exe,
                "-i", self.videoPath,
                "-c:v", codec,
                f"-b:v", f"{bitrate}k",
                "-vf", f"scale={width}:{height}",
                "-r", str(fps),
                "-c:a", "aac" if self.useTargetSizeCheck.isChecked() else "copy",
                ("-b:a", "128k") if self.useTargetSizeCheck.isChecked() else (),
                savePath
            ]
            cmd_final = []
            for part in command:
                if isinstance(part, tuple):
                    cmd_final.extend(part)
                else:
                    if part:
                        cmd_final.append(part)

            process = subprocess.run(cmd_final, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            if process.returncode == 0:
                QtWidgets.QMessageBox.information(self, "Success", "Video compressed successfully!")
            else:
                show_error_dialog("Error", f"Video compression failed.\nError: {process.stderr}")
        except Exception as e:
            show_error_dialog("Error", f"Failed to compress video.\nError: {str(e)}")

#############################
# AudioCompressorTab
#############################
class AudioCompressorTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.audioPath = ""
        self.initUI()

    def initUI(self):
        layout = QtWidgets.QVBoxLayout()

        # File selection with preview
        fileLayout = QtWidgets.QHBoxLayout()
        self.fileLabel = QtWidgets.QLabel("No audio selected")
        selectBtn = QtWidgets.QPushButton("Select Audio")
        selectBtn.clicked.connect(self.selectAudio)
        previewBtn = QtWidgets.QPushButton("Preview Audio")
        previewBtn.clicked.connect(self.previewAudio)
        fileLayout.addWidget(self.fileLabel)
        fileLayout.addWidget(selectBtn)
        fileLayout.addWidget(previewBtn)
        layout.addLayout(fileLayout)

        # Bitrate option
        bitrateLayout = QtWidgets.QHBoxLayout()
        bitrateLabel = QtWidgets.QLabel("Bitrate (kbps):")
        self.bitrateSpin = QtWidgets.QSpinBox()
        self.bitrateSpin.setRange(64, 320)
        self.bitrateSpin.setValue(128)
        bitrateLayout.addWidget(bitrateLabel)
        bitrateLayout.addWidget(self.bitrateSpin)
        layout.addLayout(bitrateLayout)

        # Sample Rate option
        sampleLayout = QtWidgets.QHBoxLayout()
        sampleLabel = QtWidgets.QLabel("Sample Rate (Hz):")
        self.sampleSpin = QtWidgets.QSpinBox()
        self.sampleSpin.setRange(8000, 96000)
        self.sampleSpin.setValue(44100)
        sampleLayout.addWidget(sampleLabel)
        sampleLayout.addWidget(self.sampleSpin)
        layout.addLayout(sampleLayout)

        # Channels option
        channelLayout = QtWidgets.QHBoxLayout()
        channelLabel = QtWidgets.QLabel("Channels:")
        self.channelCombo = QtWidgets.QComboBox()
        self.channelCombo.addItem("Mono (1)", 1)
        self.channelCombo.addItem("Stereo (2)", 2)
        channelLayout.addWidget(channelLabel)
        channelLayout.addWidget(self.channelCombo)
        layout.addLayout(channelLayout)

        # Codec selection
        codecLayout = QtWidgets.QHBoxLayout()
        codecLabel = QtWidgets.QLabel("Codec:")
        self.codecCombo = QtWidgets.QComboBox()
        self.codecCombo.addItem("AAC (aac)", "aac")
        self.codecCombo.addItem("MP3 (libmp3lame)", "libmp3lame")
        codecLayout.addWidget(codecLabel)
        codecLayout.addWidget(self.codecCombo)
        layout.addLayout(codecLayout)

        # Target file size option
        targetLayout = QtWidgets.QHBoxLayout()
        self.useTargetSizeCheck = QtWidgets.QCheckBox("Use Target File Size")
        targetLabel = QtWidgets.QLabel("Target Size (MB):")
        self.targetSizeSpin = QtWidgets.QDoubleSpinBox()
        self.targetSizeSpin.setRange(0.1, 100)
        self.targetSizeSpin.setDecimals(2)
        self.targetSizeSpin.setValue(1.0)
        targetLayout.addWidget(self.useTargetSizeCheck)
        targetLayout.addWidget(targetLabel)
        targetLayout.addWidget(self.targetSizeSpin)
        layout.addLayout(targetLayout)

        # Compress button
        compressBtn = QtWidgets.QPushButton("Compress Audio")
        compressBtn.clicked.connect(self.compressAudio)
        layout.addWidget(compressBtn)

        # Reset, Help, and Close buttons
        btnLayout = QtWidgets.QHBoxLayout()
        resetBtn = QtWidgets.QPushButton("Reset")
        resetBtn.clicked.connect(self.resetFields)
        helpBtn = QtWidgets.QPushButton("Help")
        helpBtn.clicked.connect(self.showHelp)
        closeBtn = QtWidgets.QPushButton("Close")
        closeBtn.clicked.connect(QtWidgets.qApp.quit)
        btnLayout.addWidget(resetBtn)
        btnLayout.addWidget(helpBtn)
        btnLayout.addWidget(closeBtn)
        layout.addLayout(btnLayout)

        self.setLayout(layout)

    def resetFields(self):
        self.fileLabel.setText("No audio selected")
        self.audioPath = ""
        self.bitrateSpin.setValue(128)
        self.sampleSpin.setValue(44100)
        self.channelCombo.setCurrentIndex(0)
        self.codecCombo.setCurrentIndex(0)
        self.useTargetSizeCheck.setChecked(False)
        self.targetSizeSpin.setValue(1.0)

    def showHelp(self):
        QtWidgets.QMessageBox.information(self, "Audio Compressor Help",
            "Select an audio file, set bitrate, sample rate, channels, and codec.\n"
            "Optionally, enable target file size mode. Then click 'Compress Audio'.")

    def selectAudio(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Audio", "",
            "Audio Files (*.mp3 *.wav *.aac *.flac *.ogg);;All Files (*)")
        if fileName:
            self.audioPath = fileName
            self.fileLabel.setText(os.path.basename(fileName))

    def previewAudio(self):
        if not self.audioPath:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select an audio file first.")
            return
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Audio Preview")
        layout = QtWidgets.QVBoxLayout(dlg)
        label = QtWidgets.QLabel("Playing Audio. Close this window to stop.")
        layout.addWidget(label)
        player = QMediaPlayer(dlg)
        url = QtCore.QUrl.fromLocalFile(self.audioPath)
        player.setMedia(QMediaContent(url))
        player.play()
        dlg.finished.connect(player.stop)
        dlg.exec_()

    def compressAudio(self):
        if not self.audioPath:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select an audio file first.")
            return
        try:
            savePath, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save Compressed Audio", "",
                "Audio Files (*.mp3 *.aac *.m4a);;All Files (*)")
            if not savePath:
                return

            # Determine input and output extensions
            input_ext = os.path.splitext(self.audioPath)[1].lower()
            output_ext = os.path.splitext(savePath)[1].lower()
            codec = self.codecCombo.currentData()

            # If input is MP3 and codec is AAC but output is .mp3, adjust to .m4a.
            if input_ext == ".mp3" and codec == "aac" and output_ext == ".mp3":
                base = os.path.splitext(savePath)[0]
                savePath = base + ".m4a"
                output_ext = ".m4a"
                QtWidgets.QMessageBox.information(self, "Info",
                    "Input is MP3 and AAC codec selected. Changing output extension to .m4a.")

            if self.useTargetSizeCheck.isChecked():
                dur = get_audio_duration(self.audioPath)
                if not dur:
                    show_error_dialog("Warning", "Could not determine audio duration.")
                    return
                total_bits = self.targetSizeSpin.value() * 1024 * 1024 * 8
                computed_bitrate = int((total_bits / dur) / 1000)
                bitrate = computed_bitrate
            else:
                bitrate = self.bitrateSpin.value()

            sample_rate = self.sampleSpin.value()
            channels = self.channelCombo.currentData()

            command = [ffmpeg_exe, "-i", self.audioPath]
            if codec == "aac":
                command.extend(["-c:a", codec, "-strict", "experimental"])
            else:
                command.extend(["-c:a", codec])
            command.extend([
                "-b:a", f"{bitrate}k",
                "-ar", str(sample_rate),
                "-ac", str(channels),
                savePath
            ])

            proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode == 0:
                QtWidgets.QMessageBox.information(self, "Success", "Audio compressed successfully!")
            else:
                show_error_dialog("Error", f"Audio compression failed.\nError: {proc.stderr}")
        except Exception as e:
            show_error_dialog("Error", f"Failed to compress audio.\nError: {str(e)}")

#############################
# Custom Linktree Widget & Credits
#############################
class CustomLinktreeWidget(QtWidgets.QWidget):
    def __init__(self, links, parent=None):
        super().__init__(parent)
        self.links = links
        self.initUI()
    def initUI(self):
        layout = QtWidgets.QVBoxLayout(self)
        for link in self.links:
            btn = QtWidgets.QPushButton(link['text'])
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #333333;
                    border: none;
                    border-radius: 8px;
                    padding: 12px;
                    font-size: 14pt;
                }
                QPushButton:hover {
                    background-color: #dddddd;
                }
            """)
            btn.clicked.connect(lambda checked, url=link['url']: QtGui.QDesktopServices.openUrl(QtCore.QUrl(url)))
            layout.addWidget(btn)
        layout.addStretch()
        self.setLayout(layout)

class CreditsTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    def initUI(self):
        layout = QtWidgets.QVBoxLayout()
        profileLayout = QtWidgets.QHBoxLayout()
        profilePic = QtWidgets.QLabel()
        image_url = "https://files.fivemerr.com/images/d2100fe4-fade-45c6-a481-aab71e862fd3.png"
        try:
            req = Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
            data = urlopen(req).read()
            pixmap = QtGui.QPixmap()
            if not pixmap.loadFromData(data):
                raise Exception("Failed to load image from data")
        except Exception as e:
            print("Image download failed:", e)
            pixmap = QtGui.QPixmap(100, 100)
            pixmap.fill(QtGui.QColor("gray"))
        pixmap = pixmap.scaled(100, 100, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        profilePic.setPixmap(pixmap)
        profilePic.setFixedSize(100, 100)
        profileLayout.addWidget(profilePic)
        infoLayout = QtWidgets.QVBoxLayout()
        nameLabel = QtWidgets.QLabel("J_emmons_07")
        nameLabel.setStyleSheet("font-weight: bold; font-size: 16pt; color: white;")
        aboutLabel = QtWidgets.QLabel("Just a random guy on the internet")
        aboutLabel.setStyleSheet("color: white;")
        infoLayout.addWidget(nameLabel)
        infoLayout.addWidget(aboutLabel)
        profileLayout.addLayout(infoLayout)
        layout.addLayout(profileLayout)
        links = [
            {"text": "Visit my Linktree", "url": "https://linktr.ee/J_emmons_07"}
        ]
        linktreeWidget = CustomLinktreeWidget(links)
        layout.addWidget(linktreeWidget)
        layout.addStretch()
        self.setLayout(layout)

#############################
# Main Application Window
#############################
class CompressorApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multimedia Compressor")
        self.setGeometry(100, 100, 600, 500)
        self.setStyleSheet(modernStyle)

        self.tabWidget = QtWidgets.QTabWidget()
        self.tabWidget.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #5e0080; }
            QTabBar::tab { background: #282a2e; color: #c5c8c6; padding: 10px; border: 1px solid #373b41; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #5e0080; }
        """)

        self.imageTab = ImageCompressorTab()
        self.videoTab = VideoCompressorTab()
        self.audioTab = AudioCompressorTab()
        self.creditsTab = CreditsTab()

        self.tabWidget.addTab(self.imageTab, "Image Compressor")
        self.tabWidget.addTab(self.videoTab, "Video Compressor")
        self.tabWidget.addTab(self.audioTab, "Audio Compressor")
        self.tabWidget.addTab(self.creditsTab, "Credits")

        self.setCentralWidget(self.tabWidget)

def main():
    app = QtWidgets.QApplication(sys.argv)
    mainWin = CompressorApp()
    mainWin.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
