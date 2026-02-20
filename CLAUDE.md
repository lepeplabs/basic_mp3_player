# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**lepeplabs_audio_thing** — a retro Windows 95-styled MP3 player built with Python. Fixed 780×640 window, green-on-black LCD aesthetic.

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
- `customtkinter` — GUI framework

## Architecture

Three modules with a clean separation of concerns:

- **`mp3_player.py`** — `AudioPlayer` class. All audio logic lives here: load, play, pause, stop, seek, volume, playlist management, metadata reading, album art extraction.
- **`ui.py`** — `PlayerUI` class. CustomTkinter GUI only. Polls `AudioPlayer` state every 100ms via `window.after()` for the time display and auto-advance.
- **`main.py`** — Entry point. Wires `AudioPlayer` + `PlayerUI` and sets the default music folder path.

### Key Design Details

- MP3/WAV/OGG play natively via `pygame.mixer.music`. All other formats (M4A, AAC, WMA, FLAC) are decoded and converted to an in-memory WAV via `pydub` before playback — this means seeking on those formats re-converts from the seek point (slow on large files).
- Playback position is tracked manually using `time.time()` deltas rather than pygame's built-in position, because pygame's position resets on format conversion.
- The menu bar ("File", "Options", "Help") labels are currently decorative — not yet wired to any actions.
- Default music folder is hardcoded in `main.py` — to be replaced with persistent config.

## Feature Backlog

### Done
- [x] Load multiple songs into a playlist (folder-based)
- [x] Next / Previous track buttons
- [x] Progress bar with seek/scrub
- [x] Album art display (MP3 APIC, M4A covr, FLAC pictures)
- [x] Highlight currently playing track in list
- [x] Metadata display (artist, album, year)

### Playlist
- [ ] Drag and drop files onto the player
- [ ] Save / load playlists (M3U or JSON)

### Playback Controls
- [ ] Shuffle mode
- [ ] Repeat mode (off / repeat-one / repeat-all)
- [ ] Keyboard shortcuts (Space, arrows)

### Visual
- [ ] Audio visualizer / waveform display

### Organization
- [ ] Functional File menu (open file, open folder)
- [ ] Search / filter track list
- [ ] Sort by artist / album / genre
- [ ] File browser / library view

### Advanced
- [ ] Remember last-used folder (replace hardcoded path)
- [ ] Equalizer
- [ ] Crossfade between tracks
- [ ] Queue management (Up Next)
- [ ] Radio / streaming (Icecast/Shoutcast URLs)
