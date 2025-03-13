import sys
import os
import subprocess
from io import BytesIO
from PyQt5 import QtWidgets, QtGui, QtCore
from PIL import Image
from urllib.request import urlopen, Request  # Import Request along with urlopen

# Set the OpenGL context attribute for Qt WebEngine before creating the QApplication
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)

# Multimedia imports for video/audio preview
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

# Use imageio-ffmpeg to get bundled ffmpeg executable.
import imageio_ffmpeg as iio_ffmpeg
ffmpeg_exe = iio_ffmpeg.get_ffmpeg_exe()
if sys.platform.startswith("win"):
    ffprobe_exe = os.path.join(os.path.dirname(ffmpeg_exe), "ffprobe.exe")
else:
    ffprobe_exe = os.path.join(os.path.dirname(ffmpeg_exe), "ffprobe")

# -------------------------------
# Helper functions
# -------------------------------
def get_duration(filepath):
    try:
        result = subprocess.run(
            [
                ffprobe_exe, "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                filepath
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )
        duration_str = result.stdout.strip()
        duration = float(duration_str)
        if duration <= 0:
            raise Exception("Non-positive duration")
        return duration
    except Exception as e:
        print("ffprobe failed:", e)
        # Fallback using OpenCV
        try:
            import cv2
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                print("OpenCV failed to open file.")
                return None
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            if fps > 0:
                duration = frame_count / fps
                return duration
            else:
                return None
        except Exception as e2:
            print("OpenCV fallback failed:", e2)
            return None

def get_audio_duration(filepath):
    try:
        result = subprocess.run(
            [
                ffprobe_exe, "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                filepath
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )
        duration_str = result.stdout.strip()
        return float(duration_str)
    except Exception:
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
# Modern Style Sheet (for the entire UI)
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

# -------------------------------
# Image Compressor Tab
# -------------------------------
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
        # Reset and Help buttons.
        btnLayout = QtWidgets.QHBoxLayout()
        resetBtn = QtWidgets.QPushButton("Reset")
        resetBtn.clicked.connect(self.resetFields)
        helpBtn = QtWidgets.QPushButton("Help")
        helpBtn.clicked.connect(self.showHelp)
        btnLayout.addWidget(resetBtn)
        btnLayout.addWidget(helpBtn)
        # Also add a Close button under compress button.
        closeBtn = QtWidgets.QPushButton("Close")
        closeBtn.clicked.connect(QtWidgets.qApp.quit)
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
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Image", "",
                                                              "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)")
        if fileName:
            self.imagePath = fileName
            self.fileLabel.setText(os.path.basename(fileName))

    def previewImage(self):
        if not self.imagePath:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select an image first.")
            return
        previewWindow = QtWidgets.QDialog(self)
        previewWindow.setWindowTitle("Image Preview")
        layout = QtWidgets.QVBoxLayout(previewWindow)
        label = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap(self.imagePath)
        scaled_pixmap = pixmap.scaled(800, 600, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        label.setPixmap(scaled_pixmap)
        layout.addWidget(label)
        previewWindow.exec_()

    def compressImage(self):
        if not self.imagePath:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select an image file first.")
            return
        try:
            img = Image.open(self.imagePath)
            if self.resizeCheck.isChecked():
                new_width = self.widthSpin.value()
                new_height = self.heightSpin.value()
                img = img.resize((new_width, new_height), Image.ANTIALIAS)
            savePath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Compressed Image", "",
                                                                  "JPEG Files (*.jpg);;PNG Files (*.png);;All Files (*)")
            if savePath:
                ext = os.path.splitext(savePath)[1].lower()
                if self.useTargetSizeCheck.isChecked() and ext in ['.jpg', '.jpeg']:
                    target_size_bytes = self.targetSizeSpin.value() * 1024 * 1024
                    quality, buffer = find_quality_for_target_size(img, target_size_bytes)
                    if quality is not None:
                        with open(savePath, "wb") as f:
                            f.write(buffer)
                        QtWidgets.QMessageBox.information(self, "Success", f"Image compressed using quality={quality}!")
                    else:
                        QtWidgets.QMessageBox.warning(self, "Warning", "Could not determine an optimal quality setting.")
                else:
                    quality = self.qualitySpin.value()
                    if ext in ['.jpg', '.jpeg']:
                        img = img.convert("RGB")
                        img.save(savePath, "JPEG", quality=quality)
                    elif ext == '.png':
                        img.save(savePath, "PNG", optimize=True)
                    else:
                        img = img.convert("RGB")
                        img.save(savePath, "JPEG", quality=quality)
                    QtWidgets.QMessageBox.information(self, "Success", "Image compressed successfully!")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to compress image.\nError: {str(e)}")

# -------------------------------
# Video Compressor Tab
# -------------------------------
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
        # Reflip resolution order back to "Width then Height"
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
        # Add Reset, Help, and Close buttons under the compress button.
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
            "Select a video file, set bitrate, resolution (Width then Height), frame rate, and choose codec. Optionally, enable target file size mode. Then click 'Compress Video'.")

    def selectVideo(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Video", "",
                                                              "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*)")
        if fileName:
            self.videoPath = fileName
            self.fileLabel.setText(os.path.basename(fileName))

    def previewVideo(self):
        if not self.videoPath:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select a video file first.")
            return
        previewDialog = QtWidgets.QDialog(self)
        previewDialog.setWindowTitle("Video Preview")
        previewDialog.resize(800, 600)
        layout = QtWidgets.QVBoxLayout(previewDialog)
        videoWidget = QVideoWidget()
        layout.addWidget(videoWidget)
        player = QMediaPlayer(previewDialog)
        player.setVideoOutput(videoWidget)
        url = QtCore.QUrl.fromLocalFile(self.videoPath)
        player.setMedia(QMediaContent(url))
        player.play()
        previewDialog.exec_()

    def compressVideo(self):
        if not self.videoPath:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select a video file first.")
            return
        try:
            savePath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Compressed Video", "",
                                                                  "MP4 Files (*.mp4);;All Files (*)")
            if savePath:
                width = self.videoWidthSpin.value()
                height = self.videoHeightSpin.value()
                fps = self.frameRateSpin.value()
                codec = self.codecCombo.currentData()
                if self.useTargetSizeCheck.isChecked():
                    duration = get_duration(self.videoPath)
                    if not duration:
                        QtWidgets.QMessageBox.warning(self, "Warning", "Could not determine video duration.")
                        return
                    total_target_bits = self.targetSizeSpin.value() * 1024 * 1024 * 8
                    audio_bitrate = 128000
                    audio_bits = audio_bitrate * duration
                    video_bits = total_target_bits - audio_bits
                    if video_bits <= 0:
                        QtWidgets.QMessageBox.warning(self, "Warning", "Target size too small for the audio track.")
                        return
                    computed_video_bitrate = int((video_bits / duration) / 1000)
                    bitrate = computed_video_bitrate
                else:
                    bitrate = self.bitrateSpin.value()
                command = [
                    ffmpeg_exe,
                    "-i", self.videoPath,
                    "-c:v", codec,
                    "-b:v", f"{bitrate}k",
                    "-vf", f"scale={width}:{height}",
                    "-r", str(fps),
                    "-c:a", "aac" if self.useTargetSizeCheck.isChecked() else "copy",
                    ("-b:a", "128k") if self.useTargetSizeCheck.isChecked() else (),
                    savePath
                ]
                command = [item for sub in command for item in (sub if isinstance(sub, tuple) else (sub,)) if sub != ""]
                process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
                if process.returncode == 0:
                    QtWidgets.QMessageBox.information(self, "Success", "Video compressed successfully!")
                else:
                    QtWidgets.QMessageBox.critical(self, "Error", f"Video compression failed.\nError: {process.stderr}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to compress video.\nError: {str(e)}")

# -------------------------------
# Audio Compressor Tab
# -------------------------------
class AudioCompressorTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.audioPath = ""
        self.initUI()

    def initUI(self):
        layout = QtWidgets.QVBoxLayout()
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
        bitrateLayout = QtWidgets.QHBoxLayout()
        bitrateLabel = QtWidgets.QLabel("Bitrate (kbps):")
        self.bitrateSpin = QtWidgets.QSpinBox()
        self.bitrateSpin.setRange(64, 320)
        self.bitrateSpin.setValue(128)
        bitrateLayout.addWidget(bitrateLabel)
        bitrateLayout.addWidget(self.bitrateSpin)
        layout.addLayout(bitrateLayout)
        sampleLayout = QtWidgets.QHBoxLayout()
        sampleLabel = QtWidgets.QLabel("Sample Rate (Hz):")
        self.sampleSpin = QtWidgets.QSpinBox()
        self.sampleSpin.setRange(8000, 96000)
        self.sampleSpin.setValue(44100)
        sampleLayout.addWidget(sampleLabel)
        sampleLayout.addWidget(self.sampleSpin)
        layout.addLayout(sampleLayout)
        channelLayout = QtWidgets.QHBoxLayout()
        channelLabel = QtWidgets.QLabel("Channels:")
        self.channelCombo = QtWidgets.QComboBox()
        self.channelCombo.addItem("Mono (1)", 1)
        self.channelCombo.addItem("Stereo (2)", 2)
        channelLayout.addWidget(channelLabel)
        channelLayout.addWidget(self.channelCombo)
        layout.addLayout(channelLayout)
        codecLayout = QtWidgets.QHBoxLayout()
        codecLabel = QtWidgets.QLabel("Codec:")
        self.codecCombo = QtWidgets.QComboBox()
        self.codecCombo.addItem("AAC (aac)", "aac")
        self.codecCombo.addItem("MP3 (libmp3lame)", "libmp3lame")
        codecLayout.addWidget(codecLabel)
        codecLayout.addWidget(self.codecCombo)
        layout.addLayout(codecLayout)
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
        compressBtn = QtWidgets.QPushButton("Compress Audio")
        compressBtn.clicked.connect(self.compressAudio)
        layout.addWidget(compressBtn)
        # Add Reset, Help, and Close buttons.
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
            "Select an audio file, set bitrate, sample rate, channels, and codec. Optionally, enable target file size mode. Then click 'Compress Audio'.")

    def selectAudio(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Audio", "",
                                                              "Audio Files (*.mp3 *.wav *.aac *.flac *.ogg);;All Files (*)")
        if fileName:
            self.audioPath = fileName
            self.fileLabel.setText(os.path.basename(fileName))

    def previewAudio(self):
        if not self.audioPath:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select an audio file first.")
            return
        previewDialog = QtWidgets.QDialog(self)
        previewDialog.setWindowTitle("Audio Preview")
        layout = QtWidgets.QVBoxLayout(previewDialog)
        label = QtWidgets.QLabel("Playing Audio. Close this window to stop.")
        layout.addWidget(label)
        player = QMediaPlayer(previewDialog)
        url = QtCore.QUrl.fromLocalFile(self.audioPath)
        player.setMedia(QMediaContent(url))
        player.play()
        previewDialog.finished.connect(player.stop)
        previewDialog.exec_()

    def compressAudio(self):
        if not self.audioPath:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select an audio file first.")
            return
        try:
            savePath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Compressed Audio", "",
                                                                  "Audio Files (*.mp3 *.aac *.m4a);;All Files (*)")
            if savePath:
                if self.useTargetSizeCheck.isChecked():
                    duration = get_audio_duration(self.audioPath)
                    if not duration:
                        QtWidgets.QMessageBox.warning(self, "Warning", "Could not determine audio duration.")
                        return
                    total_target_bits = self.targetSizeSpin.value() * 1024 * 1024 * 8
                    computed_bitrate = int((total_target_bits / duration) / 1000)
                    bitrate = computed_bitrate
                else:
                    bitrate = self.bitrateSpin.value()
                sample_rate = self.sampleSpin.value()
                channels = self.channelCombo.currentData()
                codec = self.codecCombo.currentData()
                command = [
                    "ffmpeg",
                    "-i", self.audioPath,
                    "-c:a", codec,
                    "-b:a", f"{bitrate}k",
                    "-ar", str(sample_rate),
                    "-ac", str(channels),
                    savePath
                ]
                process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if process.returncode == 0:
                    QtWidgets.QMessageBox.information(self, "Success", "Audio compressed successfully!")
                else:
                    QtWidgets.QMessageBox.critical(self, "Error", f"Audio compression failed.\nError: {process.stderr}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to compress audio.\nError: {str(e)}")

# -------------------------------
# Custom Linktree Widget
# -------------------------------
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

# -------------------------------
# Credits Tab (using CustomLinktreeWidget)
# -------------------------------
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

# -------------------------------
# Main Application Window
# -------------------------------
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
