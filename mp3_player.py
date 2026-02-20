"""
mp3_player.py
Core audio playback functionality using pygame with pydub conversion
Supports: MP3, AAC/M4A, WMA, WAV, FLAC
Now with playlist support and album art extraction
"""

import pygame.mixer
import os
import io
import time
import random
import json
import subprocess
import threading
import urllib.request
import urllib.parse

# 2 seconds of 44100 Hz stereo 16-bit PCM per stream chunk
_STREAM_CHUNK = 44100 * 2 * 2 * 2
from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.asf import ASF
from mutagen.wave import WAVE
from mutagen.flac import FLAC
from mutagen.aac import AAC
from mutagen.id3 import ID3, APIC
from PIL import Image

class AudioPlayer:
    def __init__(self):
        """Initialize the audio player"""
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
        self.duration = 0
        self.pause_position = 0
        self.play_start_time = 0
        self.pause_start_time = 0
        
        # Playlist management
        self.playlist = []          # flat list of all file paths (for playback)
        self.folders = []           # [{'name': str, 'path': str|None, 'tracks': [paths]}]
        self.current_track_index = -1

        # Playback modes
        self.shuffle = False
        self.repeat_mode = 0  # 0 = off, 1 = repeat-all, 2 = repeat-one
        self._shuffle_order = []
        self._shuffle_pos = -1

        # Radio stream state
        self._stream_proc = None
        self._stream_channel = None
        self._stream_playing = False
        
    def load_file(self, file_path):
        """Load an audio file and get its duration"""
        if file_path and os.path.exists(file_path):
            self.current_file = file_path
            try:
                # Get file extension
                file_ext = os.path.splitext(file_path)[1].lower()
                print(f"Loading file: {file_path}")
                print(f"Detected extension: {file_ext}")
                
                # Check for DRM-protected M4P files
                if file_ext == '.m4p':
                    print("Error: M4P files are DRM-protected and cannot be played")
                    self.duration = 0
                    return False
                
                # Read duration using mutagen
                if file_ext == '.mp3':
                    audio = MP3(file_path)
                    self.duration = int(audio.info.length)
                    print(f"MP3 duration: {self.duration}s")
                
                elif file_ext == '.aac':
                    try:
                        audio = AAC(file_path)
                        self.duration = int(audio.info.length)
                        print(f"AAC duration: {self.duration}s")
                    except Exception as e:
                        print(f"Error reading AAC with mutagen: {e}")
                        try:
                            audio_seg = AudioSegment.from_file(file_path, format='aac')
                            self.duration = int(len(audio_seg) / 1000)
                            print(f"AAC duration from pydub: {self.duration}s")
                        except Exception as e2:
                            print(f"Error reading AAC with pydub: {e2}")
                            print("File may be corrupted or not a valid AAC file")
                            return False
                    
                elif file_ext in ['.m4a', '.mp4']:
                    try:
                        audio = MP4(file_path)
                        self.duration = int(audio.info.length)
                        print(f"M4A duration: {self.duration}s")
                    except Exception as e:
                        print(f"Error reading M4A with mutagen: {e}")
                        audio_seg = AudioSegment.from_file(file_path, format='m4a')
                        self.duration = int(len(audio_seg) / 1000)
                        print(f"M4A duration from pydub: {self.duration}s")
                        
                elif file_ext == '.wma':
                    audio = ASF(file_path)
                    self.duration = int(audio.info.length)
                    print(f"WMA duration: {self.duration}s")
                    
                elif file_ext == '.wav':
                    audio = WAVE(file_path)
                    self.duration = int(audio.info.length)
                    print(f"WAV duration: {self.duration}s")
                    
                elif file_ext == '.flac':
                    audio = FLAC(file_path)
                    self.duration = int(audio.info.length)
                    print(f"FLAC duration: {self.duration}s")
                    
                else:
                    print(f"Unsupported file format: {file_ext}")
                    return False
                
                return True
                
            except Exception as e:
                print(f"Error loading file: {e}")
                import traceback
                traceback.print_exc()
                self.duration = 0
                return False
        return False
    
    def get_file_duration(self, file_path):
        """Get duration of a file without loading it for playback"""
        if not os.path.exists(file_path):
            return 0
            
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.mp3':
                audio = MP3(file_path)
                return int(audio.info.length)
            elif file_ext == '.aac':
                try:
                    audio = AAC(file_path)
                    return int(audio.info.length)
                except:
                    audio_seg = AudioSegment.from_file(file_path, format='aac')
                    return int(len(audio_seg) / 1000)
            elif file_ext in ['.m4a', '.mp4']:
                audio = MP4(file_path)
                return int(audio.info.length)
            elif file_ext == '.wma':
                audio = ASF(file_path)
                return int(audio.info.length)
            elif file_ext == '.wav':
                audio = WAVE(file_path)
                return int(audio.info.length)
            elif file_ext == '.flac':
                audio = FLAC(file_path)
                return int(audio.info.length)
        except Exception as e:
            print(f"Error getting duration for {file_path}: {e}")
            return 0
        
        return 0
    
    def get_metadata(self, file_path):
        """Return dict with artist, album, year, genre from file tags"""
        meta = {'artist': '', 'album': '', 'year': '', 'genre': ''}
        if not os.path.exists(file_path):
            return meta
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.mp3':
                tags = ID3(file_path)
                if 'TPE1' in tags:
                    meta['artist'] = str(tags['TPE1'])
                if 'TALB' in tags:
                    meta['album'] = str(tags['TALB'])
                if 'TCON' in tags:
                    meta['genre'] = str(tags['TCON'])
                for year_tag in ('TDRC', 'TYER', 'TDAT'):
                    if year_tag in tags:
                        meta['year'] = str(tags[year_tag])[:4]
                        break
            elif ext in ['.m4a', '.mp4']:
                audio = MP4(file_path)
                if audio.tags:
                    if '\xa9ART' in audio.tags:
                        meta['artist'] = str(audio.tags['\xa9ART'][0])
                    if '\xa9alb' in audio.tags:
                        meta['album'] = str(audio.tags['\xa9alb'][0])
                    if '\xa9day' in audio.tags:
                        meta['year'] = str(audio.tags['\xa9day'][0])[:4]
                    if '\xa9gen' in audio.tags:
                        meta['genre'] = str(audio.tags['\xa9gen'][0])
            elif ext == '.flac':
                audio = FLAC(file_path)
                meta['artist'] = (audio.get('artist') or [''])[0]
                meta['album']  = (audio.get('album')  or [''])[0]
                meta['genre']  = (audio.get('genre')  or [''])[0]
                year = (audio.get('date') or [''])[0]
                meta['year'] = year[:4] if year else ''
            elif ext == '.wma':
                audio = ASF(file_path)
                if 'Author' in audio:
                    meta['artist'] = str(audio['Author'][0])
                if 'WM/AlbumTitle' in audio:
                    meta['album'] = str(audio['WM/AlbumTitle'][0])
                if 'WM/Year' in audio:
                    meta['year'] = str(audio['WM/Year'][0])[:4]
                if 'WM/Genre' in audio:
                    meta['genre'] = str(audio['WM/Genre'][0])
        except Exception as e:
            print(f"Error reading metadata for {file_path}: {e}")
        return meta

    def get_album_art(self, file_path):
        """Extract album art from audio file, returns PIL Image or None"""
        if not os.path.exists(file_path):
            return None
            
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.mp3':
                audio = ID3(file_path)
                for tag in audio.values():
                    if isinstance(tag, APIC):
                        # APIC is album art
                        image_data = tag.data
                        image = Image.open(io.BytesIO(image_data))
                        return image
                        
            elif file_ext in ['.m4a', '.mp4']:
                audio = MP4(file_path)
                if 'covr' in audio:
                    image_data = audio['covr'][0]
                    image = Image.open(io.BytesIO(image_data))
                    return image
                    
            elif file_ext == '.flac':
                audio = FLAC(file_path)
                if audio.pictures:
                    image_data = audio.pictures[0].data
                    image = Image.open(io.BytesIO(image_data))
                    return image
                    
        except Exception as e:
            print(f"Error extracting album art: {e}")
            
        return None
    
    def load_folder(self, folder_path):
        """Load all supported audio files from a folder into playlist"""
        if not os.path.exists(folder_path):
            return False
            
        supported_extensions = ['.mp3', '.m4a', '.mp4', '.aac', '.wma', '.wav', '.flac']
        self.playlist = []
        
        try:
            files = os.listdir(folder_path)
            for file in sorted(files):
                file_path = os.path.join(folder_path, file)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file)[1].lower()
                    if ext in supported_extensions:
                        self.playlist.append(file_path)
            
            print(f"Loaded {len(self.playlist)} tracks from folder")
            return len(self.playlist) > 0
            
        except Exception as e:
            print(f"Error loading folder: {e}")
            return False
    
    def save_playlist_m3u(self, file_path):
        """Save current playlist to an M3U file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('#EXTM3U\n')
                for track in self.playlist:
                    f.write(track + '\n')
            print(f"Playlist saved to {file_path}")
            return True
        except Exception as e:
            print(f"Error saving playlist: {e}")
            return False

    def load_playlist_m3u(self, file_path):
        """Load an M3U playlist file as a named folder group"""
        try:
            tracks = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and os.path.exists(line):
                        tracks.append(line)
            if not tracks:
                return False
            name = os.path.splitext(os.path.basename(file_path))[0]
            self.folders.append({'name': f'📋 {name}', 'path': None, 'tracks': tracks})
            self._rebuild_playlist()
            print(f"Loaded {len(tracks)} tracks from {file_path}")
            return True
        except Exception as e:
            print(f"Error loading playlist: {e}")
            return False

    def add_folder(self, folder_path):
        """Add all audio files from a folder as a named group"""
        if not os.path.exists(folder_path):
            return False
        supported = {'.mp3', '.m4a', '.mp4', '.aac', '.wma', '.wav', '.flac'}
        tracks = [
            os.path.join(folder_path, f)
            for f in sorted(os.listdir(folder_path))
            if os.path.isfile(os.path.join(folder_path, f))
            and os.path.splitext(f)[1].lower() in supported
        ]
        if not tracks:
            return False
        # Avoid adding the same folder twice
        for existing in self.folders:
            if existing.get('path') == folder_path:
                return True
        self.folders.append({'name': os.path.basename(folder_path),
                             'path': folder_path, 'tracks': tracks})
        self._rebuild_playlist()
        return True

    def add_files_group(self, group_name, file_paths):
        """Add a named group of individual files (e.g. from drag-and-drop)"""
        valid = [p for p in file_paths if os.path.exists(p)]
        if not valid:
            return False
        # Append to existing group with the same name if it exists
        for folder in self.folders:
            if folder['name'] == group_name:
                for p in valid:
                    if p not in folder['tracks']:
                        folder['tracks'].append(p)
                self._rebuild_playlist()
                return True
        self.folders.append({'name': group_name, 'path': None, 'tracks': valid})
        self._rebuild_playlist()
        return True

    def _rebuild_playlist(self):
        """Rebuild the flat playlist from all folder groups"""
        self.playlist = []
        for folder in self.folders:
            self.playlist.extend(folder['tracks'])
        if self.current_track_index >= len(self.playlist):
            self.current_track_index = -1

    def add_files_to_playlist(self, file_paths):
        """Add multiple files to the playlist"""
        for file_path in file_paths:
            if os.path.exists(file_path) and file_path not in self.playlist:
                self.playlist.append(file_path)
        print(f"Playlist now has {len(self.playlist)} tracks")
    
    def play_track_at_index(self, index):
        """Play a specific track from the playlist"""
        if 0 <= index < len(self.playlist):
            self.current_track_index = index
            if self.load_file(self.playlist[index]):
                return self.play()
        return False
    
    def _build_shuffle_order(self):
        """Generate a shuffled play order, excluding the current track"""
        indices = list(range(len(self.playlist)))
        if self.current_track_index in indices:
            indices.remove(self.current_track_index)
        random.shuffle(indices)
        self._shuffle_order = indices
        self._shuffle_pos = 0

    def toggle_shuffle(self):
        """Toggle shuffle on/off, returns new state"""
        self.shuffle = not self.shuffle
        if self.shuffle:
            self._build_shuffle_order()
        return self.shuffle

    def cycle_repeat(self):
        """Cycle repeat mode: off → repeat-all → repeat-one → off, returns new mode"""
        self.repeat_mode = (self.repeat_mode + 1) % 3
        return self.repeat_mode

    def play_next(self):
        """Play the next track, respecting shuffle and repeat modes"""
        if not self.playlist:
            return False

        if self.repeat_mode == 2:  # repeat-one
            return self.play_track_at_index(self.current_track_index)

        if self.shuffle:
            if self._shuffle_pos < len(self._shuffle_order) - 1:
                self._shuffle_pos += 1
                return self.play_track_at_index(self._shuffle_order[self._shuffle_pos])
            elif self.repeat_mode == 1:  # repeat-all: rebuild shuffle and loop
                self._build_shuffle_order()
                if self._shuffle_order:
                    return self.play_track_at_index(self._shuffle_order[0])
            return False
        else:
            if self.current_track_index < len(self.playlist) - 1:
                return self.play_track_at_index(self.current_track_index + 1)
            elif self.repeat_mode == 1:  # repeat-all: wrap to start
                return self.play_track_at_index(0)
            return False

    def play_previous(self):
        """Play the previous track, respecting shuffle mode"""
        if not self.playlist:
            return False

        if self.shuffle:
            if self._shuffle_pos > 0:
                self._shuffle_pos -= 1
                return self.play_track_at_index(self._shuffle_order[self._shuffle_pos])
            return False
        else:
            if self.current_track_index > 0:
                return self.play_track_at_index(self.current_track_index - 1)
            return False
    
    def play(self):
        """Play the loaded audio file or resume if paused"""
        if self.current_file:
            try:
                if self.is_paused:
                    pygame.mixer.music.unpause()
                    self.is_paused = False
                    self.is_playing = True
                    paused_duration = time.time() - self.pause_start_time
                    self.play_start_time += paused_duration
                    print(f"Resumed from position: {self.pause_position}s")
                    return True
                
                file_ext = os.path.splitext(self.current_file)[1].lower()
                
                if file_ext in ['.mp3', '.wav', '.ogg']:
                    print(f"Playing {file_ext} directly with pygame")
                    pygame.mixer.music.load(self.current_file)
                else:
                    print(f"Converting {file_ext} to WAV for playback...")
                    
                    try:
                        if file_ext == '.aac':
                            audio = AudioSegment.from_file(self.current_file, format='aac')
                        elif file_ext in ['.m4a', '.mp4']:
                            audio = AudioSegment.from_file(self.current_file, format='m4a')
                        elif file_ext == '.wma':
                            audio = AudioSegment.from_file(self.current_file, format='wma')
                        elif file_ext == '.flac':
                            audio = AudioSegment.from_file(self.current_file, format='flac')
                        else:
                            audio = AudioSegment.from_file(self.current_file)
                    except Exception as e:
                        print(f"Error loading {file_ext} file: {e}")
                        if file_ext == '.aac':
                            print("Trying to load as ADTS AAC stream...")
                            audio = AudioSegment.from_file(self.current_file)
                        else:
                            raise
                    
                    print(f"Audio loaded, converting to WAV...")
                    wav_io = io.BytesIO()
                    audio.export(wav_io, format='wav')
                    wav_io.seek(0)
                    print(f"Conversion complete, loading into pygame...")
                    pygame.mixer.music.load(wav_io, 'wav')
                
                pygame.mixer.music.play()
                self.is_playing = True
                self.is_paused = False
                self.play_start_time = time.time()
                self.pause_position = 0
                print(f"Playback started at time: {self.play_start_time}")
                return True
                
            except Exception as e:
                print(f"Error playing file: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print("No file loaded")
        return False
    
    def pause(self):
        """Pause playback (can be resumed)"""
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.is_playing = False
            self.pause_position = self.get_position()
            self.pause_start_time = time.time()
            print(f"Paused at position: {self.pause_position}s")
            return True
        return False
    
    def stop(self):
        """Stop playback completely (resets to beginning)"""
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.pause_position = 0
        self.play_start_time = 0
        print("Playback stopped")
    
    def get_position(self):
        """Get current playback position in seconds"""
        if self.is_paused:
            return self.pause_position
        elif self.is_playing:
            elapsed_seconds = time.time() - self.play_start_time
            position = min(elapsed_seconds, self.duration)
            return position
        else:
            return 0
    
    def get_duration(self):
        """Get total track duration in seconds"""
        return self.duration
    
    def format_time(self, seconds):
        """Format seconds as M:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
    
    def seek(self, seconds):
        """Seek to a position in seconds. Works while playing or paused."""
        if not self.current_file:
            return False

        seconds = max(0, min(seconds, self.duration))
        was_paused = self.is_paused

        try:
            file_ext = os.path.splitext(self.current_file)[1].lower()

            if file_ext in ['.mp3', '.wav', '.ogg']:
                pygame.mixer.music.play(0, seconds)
            else:
                # Re-convert from seek position for pydub-handled formats
                if file_ext == '.aac':
                    audio = AudioSegment.from_file(self.current_file, format='aac')
                elif file_ext in ['.m4a', '.mp4']:
                    audio = AudioSegment.from_file(self.current_file, format='m4a')
                elif file_ext == '.wma':
                    audio = AudioSegment.from_file(self.current_file, format='wma')
                elif file_ext == '.flac':
                    audio = AudioSegment.from_file(self.current_file, format='flac')
                else:
                    audio = AudioSegment.from_file(self.current_file)

                audio_slice = audio[int(seconds * 1000):]
                wav_io = io.BytesIO()
                audio_slice.export(wav_io, format='wav')
                wav_io.seek(0)
                pygame.mixer.music.load(wav_io, 'wav')
                pygame.mixer.music.play()

            self.play_start_time = time.time() - seconds
            self.is_playing = True
            self.is_paused = False
            self.pause_position = 0

            if was_paused:
                pygame.mixer.music.pause()
                self.is_playing = False
                self.is_paused = True
                self.pause_position = seconds
                self.pause_start_time = time.time()

            print(f"Seeked to {seconds:.1f}s")
            return True

        except Exception as e:
            print(f"Error seeking: {e}")
            import traceback
            traceback.print_exc()
            return False

    def set_volume(self, volume):
        """Set volume level (0.0 to 1.0)"""
        pygame.mixer.music.set_volume(volume)
        if self._stream_channel:
            self._stream_channel.set_volume(volume)
    
    def fetch_album_art_online(self, artist='', album='', title=''):
        """Search iTunes for album art. Returns a PIL Image or None."""
        query = ' '.join(filter(None, [artist, album, title]))
        if not query.strip():
            return None
        url = 'https://itunes.apple.com/search?' + urllib.parse.urlencode({
            'term': query, 'entity': 'album', 'limit': 5, 'media': 'music'
        })
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                data = json.loads(r.read())
            for result in data.get('results', []):
                art_url = result.get('artworkUrl100', '')
                if art_url:
                    art_url = art_url.replace('100x100bb', '600x600bb')
                    with urllib.request.urlopen(art_url, timeout=8) as r:
                        return Image.open(io.BytesIO(r.read())).copy()
        except Exception as e:
            print(f"Error fetching online art: {e}")
        return None

    def embed_album_art(self, file_path, image_bytes, mime='image/jpeg'):
        """Embed image bytes as album art into the audio file's tags."""
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == '.mp3':
                tags = ID3(file_path)
                tags.delall('APIC')
                tags['APIC'] = APIC(encoding=3, mime=mime, type=3,
                                    desc='Cover', data=image_bytes)
                tags.save()
            elif ext in ['.m4a', '.mp4']:
                from mutagen.mp4 import MP4Cover
                audio = MP4(file_path)
                fmt = MP4Cover.FORMAT_PNG if 'png' in mime else MP4Cover.FORMAT_JPEG
                audio['covr'] = [MP4Cover(image_bytes, imageformat=fmt)]
                audio.save()
            elif ext == '.flac':
                from mutagen.flac import Picture
                audio = FLAC(file_path)
                pic = Picture()
                pic.type = 3
                pic.mime = mime
                pic.data = image_bytes
                audio.clear_pictures()
                audio.add_picture(pic)
                audio.save()
            else:
                print(f"Art embedding not supported for {ext}")
                return False
            print(f"Art embedded into {file_path}")
            return True
        except Exception as e:
            print(f"Error embedding art: {e}")
            import traceback
            traceback.print_exc()
            return False

    def play_stream(self, url):
        """Play an internet radio stream via ffmpeg → pygame Channel"""
        self.stop_stream()
        pygame.mixer.music.stop()
        try:
            cmd = [
                'ffmpeg',
                '-reconnect', '1',
                '-reconnect_streamed', '1',
                '-reconnect_delay_max', '5',
                '-i', url,
                '-f', 's16le', '-ar', '44100', '-ac', '2',
                '-loglevel', 'error',
                'pipe:1',
            ]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL)
            self._stream_proc = proc
            self._stream_playing = True
            self._stream_channel = pygame.mixer.Channel(0)
            current_vol = pygame.mixer.music.get_volume()
            self._stream_channel.set_volume(current_vol)
            self.is_playing = True
            self.is_paused = False
            self.current_file = url
            self.duration = 0

            channel = self._stream_channel

            def _feeder():
                buf = b''
                while self._stream_playing:
                    data = proc.stdout.read(4096)
                    if not data:
                        break
                    buf += data
                    if len(buf) >= _STREAM_CHUNK:
                        snd = pygame.mixer.Sound(buffer=buf[:_STREAM_CHUNK])
                        buf = buf[_STREAM_CHUNK:]
                        snd.set_volume(channel.get_volume())
                        # Wait for queue slot (pygame channels hold 1 queued sound)
                        while self._stream_playing and channel.get_queue() is not None:
                            time.sleep(0.05)
                        if not channel.get_busy():
                            channel.play(snd)
                        else:
                            channel.queue(snd)

            threading.Thread(target=_feeder, daemon=True).start()
            print(f"Streaming: {url}")
            return True
        except Exception as e:
            print(f"Error playing stream: {e}")
            return False

    def stop_stream(self):
        """Stop radio stream and clean up ffmpeg process"""
        self._stream_playing = False
        if self._stream_proc:
            try:
                self._stream_proc.terminate()
                self._stream_proc.wait(timeout=2)
            except Exception:
                pass
            self._stream_proc = None
        if self._stream_channel:
            try:
                self._stream_channel.stop()
            except Exception:
                pass
            self._stream_channel = None
        self.is_playing = False
        self.is_paused = False
        self.current_file = None

    def reset(self):
        """Stop playback and wipe all state back to startup defaults"""
        self.stop_stream()
        pygame.mixer.music.stop()
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
        self.duration = 0
        self.pause_position = 0
        self.play_start_time = 0
        self.pause_start_time = 0
        self.playlist = []
        self.folders = []
        self.current_track_index = -1
        self.shuffle = False
        self.repeat_mode = 0
        self._shuffle_order = []
        self._shuffle_pos = -1

    def get_current_file(self):
        """Get the current file path"""
        return self.current_file
    
    def get_current_filename(self):
        """Get just the filename without path"""
        if self.current_file:
            return os.path.basename(self.current_file)
        return None