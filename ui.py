"""
ui.py
User interface for the MP3 player using CustomTkinter
"""

import customtkinter as ctk
from tkinter import filedialog
import os

class PlayerUI:
    def __init__(self, audio_player, default_music_folder=None):
        """
        Initialize the UI
        Args:
            audio_player: Instance of AudioPlayer class
            default_music_folder: Default folder path for MP3 files
        """
        self.audio_player = audio_player
        self.default_music_folder = default_music_folder
        
        # Create main window
        self.window = ctk.CTk()
        self.window.title("Simple MP3 Player")
        self.window.geometry("500x350")  # Increased height for pause button
        
        # Build the interface
        self.create_widgets()
        
    def create_widgets(self):
        """Create all UI elements"""
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.window,
            text="MP3 Player",
            font=("Arial", 24, "bold")
        )
        self.title_label.pack(pady=20)
        
        # Song display
        self.song_label = ctk.CTkLabel(
            self.window,
            text="No song selected",
            font=("Arial", 14)
        )
        self.song_label.pack(pady=10)
        
        # Button container
        button_frame = ctk.CTkFrame(self.window)
        button_frame.pack(pady=20)
        
        # Browse button
        self.browse_button = ctk.CTkButton(
            button_frame,
            text="Browse",
            command=self.browse_file,
            width=100
        )
        self.browse_button.grid(row=0, column=0, padx=10, pady=5)
        
        # Play button
        self.play_button = ctk.CTkButton(
            button_frame,
            text="Play",
            command=self.play_music,
            width=100
        )
        self.play_button.grid(row=0, column=1, padx=10, pady=5)
        
        # Pause button
        self.pause_button = ctk.CTkButton(
            button_frame,
            text="Pause",
            command=self.pause_music,
            width=100
        )
        self.pause_button.grid(row=1, column=0, padx=10, pady=5)
        
        # Stop button
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="Stop",
            command=self.stop_music,
            width=100
        )
        self.stop_button.grid(row=1, column=1, padx=10, pady=5)
        
        # Volume label
        volume_label = ctk.CTkLabel(
            self.window,
            text="Volume",
            font=("Arial", 12)
        )
        volume_label.pack(pady=(20, 5))
        
        # Volume slider
        self.volume_slider = ctk.CTkSlider(
            self.window,
            from_=0,
            to=100,
            command=self.change_volume,
            width=300
        )
        self.volume_slider.set(70)
        self.volume_slider.pack()
        
    def browse_file(self):
        """Open file dialog to select MP3"""
        # Determine which folder to open
        initial_dir = self.default_music_folder if self.default_music_folder else "/"
        
        # Check if the default folder exists
        if self.default_music_folder and not os.path.exists(self.default_music_folder):
            print(f"Warning: Default folder '{self.default_music_folder}' not found. Using system default.")
            initial_dir = "/"
        
        file_path = filedialog.askopenfilename(
            title="Select MP3 File",
            initialdir=initial_dir,
            filetypes=[("MP3 Files", "*.mp3"), ("All Files", "*.*")]
        )
        
        if file_path:
            if self.audio_player.load_file(file_path):
                filename = self.audio_player.get_current_filename()
                self.song_label.configure(text=filename)
    
    def play_music(self):
        """Play button handler - plays or resumes"""
        if self.audio_player.play():
            filename = self.audio_player.get_current_filename()
            if self.audio_player.is_paused:
                # This won't execute because play() sets is_paused to False
                # But keeping the logic clear
                self.song_label.configure(text=f"Resumed: {filename}")
            else:
                self.song_label.configure(text=f"Playing: {filename}")
        else:
            self.song_label.configure(text="Please select a file first!")
    
    def pause_music(self):
        """Pause button handler"""
        if self.audio_player.pause():
            filename = self.audio_player.get_current_filename()
            self.song_label.configure(text=f"Paused: {filename}")
    
    def stop_music(self):
        """Stop button handler"""
        self.audio_player.stop()
        filename = self.audio_player.get_current_filename()
        if filename:
            self.song_label.configure(text=f"Stopped: {filename}")
    
    def change_volume(self, value):
        """Volume slider handler"""
        volume = float(value) / 100  # Convert 0-100 to 0.0-1.0
        self.audio_player.set_volume(volume)
    
    def run(self):
        """Start the application"""
        self.window.mainloop()