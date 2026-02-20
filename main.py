"""
main.py
Entry point for the MP3 Player application
"""

from mp3_player import AudioPlayer
from ui import PlayerUI

def main():
    """Initialize and run the MP3 player"""
    audio_player = AudioPlayer()
    player_ui = PlayerUI(audio_player)
    player_ui.run()

if __name__ == "__main__":
    main()
