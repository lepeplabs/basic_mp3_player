# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**lepeplabs_audio_thing** — a retro Windows 95-styled MP3 player built with Python. Fixed 780×720 window, green-on-black LCD aesthetic.

## Running the App

```bash
python main.py
```

No build step. Requires Python 3.14+.

## Dependencies

- `pygame` — audio playback (native support for MP3, WAV, OGG)
- `pydub` — converts M4A/AAC/WMA/FLAC to WAV in-memory for pygame
- `mutagen` — reads audio metadata tags and duration
- `Pillow` — album art extraction and display
- `PySide6` — GUI framework (Qt6)

## Architecture

Three modules with a clean separation of concerns:

- **`mp3_player.py`** — `AudioPlayer` class. All audio logic: load, play, pause, stop, seek, volume, playlist management, metadata reading, album art extraction, radio streaming (ffmpeg subprocess → pygame Channel), PCM decode for visualizer.
- **`ui.py`** — `PlayerUI(QMainWindow)` class. PySide6 GUI. Polls `AudioPlayer` state every 100ms via `QTimer` for time display and auto-advance. Also contains `VisualizerWidget(QWidget)` and `_TrackRow(QWidget)`.
- **`main.py`** — Entry point. Creates `QApplication`, wires `AudioPlayer` + `PlayerUI`, calls `app.exec()`.

### Key Design Details

- MP3/WAV/OGG play natively via `pygame.mixer.music`. All other formats (M4A, AAC, WMA, FLAC) are decoded to in-memory WAV via `pydub` before playback — seeking on those formats re-converts from the seek point.
- Playback position is tracked manually with `time.time()` deltas (not pygame's built-in position, which resets on format conversion).
- Radio streaming uses an `ffmpeg` subprocess piping raw PCM to `pygame.mixer.Channel(0)` via a daemon feeder thread. Requires `ffmpeg` on PATH.
- The reactive visualizer pre-decodes audio to raw s16le PCM bytes (`preload_pcm()`), then `get_viz_frame(pos_seconds)` extracts an 80ms window at the current playback position. Capped at 5 minutes to limit RAM (~50MB max).
- Config persisted to `~/.lepeplabs_player.json` — stores `last_folder` and `radio_favourites`.
- Radio and Search panels are inserted/removed from the right-panel `QVBoxLayout` dynamically using `insertWidget()` / `removeWidget()`. The sort bar index is tracked in `_sort_bar_idx`.
- Win95 styling applied via a single QSS stylesheet on `QMainWindow`. LCD panels styled per-widget (`setStyleSheet`).
- Drag and drop uses native Qt (`dragEnterEvent` / `dropEvent` on `QMainWindow`).

## Feature Backlog

### Done
- [x] Load multiple songs into a playlist (folder-based)
- [x] Next / Previous track buttons
- [x] Progress bar with seek/scrub
- [x] Album art display (MP3 APIC, M4A covr, FLAC pictures)
- [x] Highlight currently playing track in list
- [x] Metadata display (artist, album, year)
- [x] Shuffle mode
- [x] Repeat mode (off / repeat-one / repeat-all)
- [x] Keyboard shortcuts (Space, arrows, S/Esc)
- [x] Drag and drop files/folders onto the player
- [x] Save / load playlists (M3U)
- [x] Functional File menu (open file, open folder, album art, exit)
- [x] Search / filter track list (real-time)
- [x] Group by artist / album / genre / folder (collapsible tree)
- [x] Remember last-used folder (persistent config)
- [x] Album art: load from file, fetch from iTunes API, embed to tags
- [x] Radio / streaming (Icecast/Shoutcast via ffmpeg)
- [x] Saved radio station favourites (persistent)
- [x] Reactive audio visualizer (real-time amplitude bars with peak-hold)
- [x] Migrated UI from CustomTkinter to PySide6

### Pending
- [ ] Equalizer
- [ ] Crossfade between tracks
- [ ] Queue management (Up Next)
