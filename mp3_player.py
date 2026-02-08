"""
mp3_player.py
Core audio playback functionality using pygame
"""

import pygame
import os

class AudioPlayer:
    def __init__(self):
        """Initialize the audio player"""
        pygame.mixer.init()
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
        
    def load_file(self, file_path):
        """Load an MP3 file"""
        if file_path and os.path.exists(file_path):
            self.current_file = file_path
            return True
        return False
    
    def play(self):
        """Play the loaded MP3 file or resume if paused"""
        if self.current_file:
            try:
                # If paused, just unpause (resume)
                if self.is_paused:
                    pygame.mixer.music.unpause()
                    self.is_paused = False
                    self.is_playing = True
                    return True
                
                # Otherwise, load and play from start
                pygame.mixer.music.load(self.current_file)
                pygame.mixer.music.play()
                self.is_playing = True
                self.is_paused = False
                return True
            except Exception as e:
                print(f"Error playing file: {e}")
                return False
        return False
    
    def pause(self):
        """Pause playback (can be resumed)"""
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.is_playing = False
            return True
        return False
    
    def stop(self):
        """Stop playback completely (resets to beginning)"""
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
    
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