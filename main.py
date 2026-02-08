"""
main.py
Entry point for the MP3 Player application
"""

from mp3_player import AudioPlayer
from ui import PlayerUI
import os

def main():
    """Initialize and run the MP3 player"""
    
    # ============================================
    # SET YOUR DEFAULT MUSIC FOLDER HERE
    # ============================================
    
    # Option 1: Absolute path (recommended)
    DEFAULT_MUSIC_FOLDER = "/Users/lepeplabs/lepeplabs/my_music"
    
    # Option 2: Relative to this script
    # DEFAULT_MUSIC_FOLDER = os.path.join(os.path.dirname(__file__), "music")
    
    # Option 3: User's home directory
    # DEFAULT_MUSIC_FOLDER = os.path.expanduser("~/Music")
    
    # Option 4: No default (browser opens in system default location)
    # DEFAULT_MUSIC_FOLDER = None
    
    # ============================================
    
    # Create the audio player engine
    audio_player = AudioPlayer()
    
    # Create the UI and pass the audio player and default folder to it
    player_ui = PlayerUI(audio_player, default_music_folder=DEFAULT_MUSIC_FOLDER)
    
    # Run the application
    player_ui.run()

if __name__ == "__main__":
    main()