# Pars Local Player (PLP) 2.1.1

Pars Local Player is a lightweight and small media player created by ParrotHat Foundation.

## Features

- Video and audio playback through QtMultimedia (FFmpeg)

- HW acceleration
  - Windows: DX11 / DXVA2
  - Linux: VAAPI (when available)
  - macOS: VideoToolbox

- Wide format support
  - MP4, MKV, AVI, MP3, FLAC, OGG, OPUS, WAV, M4A and many more

- Playlist support
  - M3U, M3U8, PLS, XSPF, CUE

- Internet radio and stream playback
  - HTTP / HTTPS / RTSP

- Playback speed control (0.25x – 4.0x)
- Shuffle and repeat modes (Off / One / All)
- A–B loop playback
- Media metadata viewer
  - Codec, resolution, bitrate, duration, etc.
- Screenshot capture from video playback
- Cinema Mode (focus on video, hide side panels)
- Drag & drop support for files and streams



## Cinema Mode Notes

Cinema Mode hides the **Playlist** and **Info** panels to focus entirely on video playback.

To restore them:
- Disable Cinema Mode, or
- Use the View menu to re-enable Playlist or Info panels

This behavior is intentional.


## System Requirements

### Windows
- Windows 10 or newer (64-bit)
- 64-bit CPU (2 cores minimum)
- DirectX 11 compatible GPU recommended
- 4 GB RAM recommended
- ~150 MB disk space
- Internet connection required for radio streams

### Linux
- Modern Linux distribution (64-bit)
- VAAPI-compatible GPU recommended
- FFmpeg-supported codecs available


## Installation (Windows)

Run the installer:

plp-2.1.1-installer-x64.exe

Follow the on-screen instructions.
Desktop and Start Menu shortcuts are optional.

PLP does **not** require Python or additional runtimes.
Everything is bundled into the executable.


## Portable Use

PLP can also be run directly without installation:

PLP2.1.1.exe


This allows fully portable usage.


## Source Code

GitHub repository:

https://github.com/parrothat/plp


## License

Pars Local Player is licensed under the **GNU General Public License v3.0 only**.

See the file `LICENSE.txt` for the full license text.


## About

Pars Local Player is developed and maintained by the  
**ParrotHat Foundation**

© 2025 ParrotHat Foundation
