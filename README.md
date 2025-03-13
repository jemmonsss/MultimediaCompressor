
# Multimedia Compressor

A cross-platform multimedia compression application built with Python and PyQt5. This tool provides a modern, user-friendly interface to compress images, videos, and audio files. With a variety of adjustable settings and helpful features like preview, reset, and built-in help, it makes multimedia compression both accessible and customizable.

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
  - Uses bundled ffmpeg via [imageio-ffmpeg](https://pypi.org/project/imageio-ffmpeg/) so no extra PATH configuration is needed.

- **Audio Compression:**
  - Select and preview audio files.
  - Adjust bitrate, sample rate, channels, and codec.
  - Optionally set a target file size.

- **Modern UI:**
  - A sleek, dark-themed interface with modern styling.
  - Each tab includes Reset and Help buttons for ease of use.
  - A custom Credits page displays your profile picture and Linktree information.

- **Additional Options:**
  - Reset buttons to clear selections and revert fields to default values.
  - Help dialogs providing brief usage instructions.

## Dependencies

- Python 3.x
- PyQt5
- Pillow
- imageio‑ffmpeg
- opencv‑python (for video duration fallback)

Install these dependencies via pip:

```bash
pip install PyQt5 Pillow imageio-ffmpeg opencv-python


## Usage

Run the application by executing:

```bash
python main.py
```

Alternatively, you can download a standalone executable from the [Releases page](https://github.com/jemmonsss/MultimediaCompressor/releases/download/Compresor/Compressor.exe).

## License

This project is licensed under the [MIT License](LICENSE).

