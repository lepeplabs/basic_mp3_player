"""
mp3_player.py
Core audio playback functionality using pygame with pydub conversion
Supports: MP3, AAC/M4A, WMA, WAV, FLAC
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

class AudioPlayer:
    def __init__(self):
        """Initialize the audio player"""
        # Initialize ONLY the mixer, not full pygame
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
        self.duration = 0
        self.pause_position = 0
        self.play_start_time = 0
        self.pause_start_time = 0
        
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
                    # Raw AAC files - use AAC parser or fallback to pydub
                    try:
                        audio = AAC(file_path)
                        self.duration = int(audio.info.length)
                        print(f"AAC duration: {self.duration}s")
                    except Exception as e:
                        print(f"Error reading AAC with mutagen: {e}")
                        # Fallback: use pydub to get duration
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
                        # Fallback: use pydub to get duration
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
    
    def play(self):
        """Play the loaded audio file or resume if paused"""
        if self.current_file:
            try:
                # If paused, just unpause
                if self.is_paused:
                    pygame.mixer.music.unpause()
                    self.is_paused = False
                    self.is_playing = True
                    # Adjust start time to account for paused duration
                    paused_duration = time.time() - self.pause_start_time
                    self.play_start_time += paused_duration
                    print(f"Resumed from position: {self.pause_position}s")
                    return True
                
                # Get file extension
                file_ext = os.path.splitext(self.current_file)[1].lower()
                
                # For formats pygame supports natively (MP3, WAV, OGG)
                if file_ext in ['.mp3', '.wav', '.ogg']:
                    print(f"Playing {file_ext} directly with pygame")
                    pygame.mixer.music.load(self.current_file)
                else:
                    # For other formats, convert to WAV in memory
                    print(f"Converting {file_ext} to WAV for playback...")
                    
                    # Load audio file with pydub - specify format explicitly
                    try:
                        if file_ext == '.aac':
                            # Try AAC format first
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
                        # For AAC, try alternative format detection
                        if file_ext == '.aac':
                            print("Trying to load as ADTS AAC stream...")
                            audio = AudioSegment.from_file(self.current_file)
                        else:
                            raise
                    
                    print(f"Audio loaded, converting to WAV...")
                    
                    # Export to bytes in WAV format
                    wav_io = io.BytesIO()
                    audio.export(wav_io, format='wav')
                    wav_io.seek(0)
                    
                    print(f"Conversion complete, loading into pygame...")
                    
                    # Load from bytes
                    pygame.mixer.music.load(wav_io, 'wav')
                
                pygame.mixer.music.play()
                self.is_playing = True
                self.is_paused = False
                self.play_start_time = time.time()  # Use time.time() for position tracking
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
            # Calculate elapsed time using time.time()
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
        """
        Set volume level
        Args:
            volume: float between 0.0 and 1.0
        """
        pygame.mixer.music.set_volume(volume)
    
    def get_current_file(self):
        """Get the current file path"""
        return self.current_file
    
    def get_current_filename(self):
        """Get just the filename without path"""
        if self.current_file:
            return os.path.basename(self.current_file)
        return None