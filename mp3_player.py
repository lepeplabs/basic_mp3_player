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
        self.playlist = []  # List of file paths
        self.current_track_index = -1
        
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
    
    def play_next(self):
        """Play the next track in playlist"""
        if self.playlist and self.current_track_index < len(self.playlist) - 1:
            return self.play_track_at_index(self.current_track_index + 1)
        return False
    
    def play_previous(self):
        """Play the previous track in playlist"""
        if self.playlist and self.current_track_index > 0:
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
    
    def set_volume(self, volume):
        """Set volume level (0.0 to 1.0)"""
        pygame.mixer.music.set_volume(volume)
    
    def get_current_file(self):
        """Get the current file path"""
        return self.current_file
    
    def get_current_filename(self):
        """Get just the filename without path"""
        if self.current_file:
            return os.path.basename(self.current_file)
        return None