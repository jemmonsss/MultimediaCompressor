
---

# Multimedia Compressor

A multimedia compression application built with Python and PyQt5. This tool provides a modern, user-friendly interface to compress images, videos, and audio files. With a variety of adjustable settings and helpful features like preview, reset, and built-in help, it makes multimedia compression both accessible and customizable.

## Features

- **Image Compression:**
  - Select and preview image files.
  - Adjust JPEG quality.
  - Optionally resize images.
  - Set a target file size to automatically determine the optimal quality.
  - Save output in JPEG or PNG formats.

- **Video Compression:**
  - Select and preview video files.
  - Set bitrate, resolution (Width then Height), frame rate, and codec.
  - Optionally use a target file size to recalculate video bitrate.
  - Uses a bundled ffmpeg (downloaded automatically via [imageio‑ffmpeg](https://pypi.org/project/imageio-ffmpeg/)) so no extra PATH configuration is needed.

- **Audio Compression:**
  - Select and preview audio files.
  - Adjust bitrate, sample rate, channels, and codec.
  - Optionally set a target file size.
  - Automatically adjusts the output container when converting MP3 to AAC (i.e. changes the extension to .m4a).

- **Modern UI:**
  - A sleek, dark-themed interface with modern styling.
  - Each tab includes Reset, Help, and Close buttons.
  - A custom Credits page displays your profile picture and Linktree information.
  - Copyable error dialogs for easier troubleshooting.

- **Additional Options:**
  - Automatic download and extraction of ffmpeg if not found locally.
  - Fallback mechanisms for determining video and audio durations using OpenCV and Mutagen.
  - Advanced error reporting with a custom error dialog.

## Dependencies

- Python 3.x
- [PyQt5](https://pypi.org/project/PyQt5/)
- [Pillow](https://pypi.org/project/Pillow/)
- [imageio‑ffmpeg](https://pypi.org/project/imageio-ffmpeg/)
- [opencv‑python](https://pypi.org/project/opencv-python/) (optional, for video duration fallback)
- [mutagen](https://pypi.org/project/mutagen/) (optional, for audio duration fallback)
- [requests](https://pypi.org/project/requests/)

Install these dependencies via pip:

```bash
pip install PyQt5 Pillow imageio-ffmpeg opencv-python mutagen requests
```

## Usage

Run the application by executing:

```bash
python main.py
```

Alternatively, you can download a standalone executable from the [Releases page](https://github.com/jemmonsss/MultimediaCompressor/releases/download/Compresor/Compressor.exe).

## License

This project is licensed under the [MIT License](LICENSE).

---
