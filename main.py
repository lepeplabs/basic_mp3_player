"""
main.py
Entry point for the MP3 Player application
"""

import sys
from PySide6.QtWidgets import QApplication
from mp3_player import AudioPlayer
from ui import PlayerUI


def main():
    """Initialize and run the MP3 player"""
    app = QApplication(sys.argv)
    audio_player = AudioPlayer()
    player_ui = PlayerUI(audio_player)
    player_ui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
