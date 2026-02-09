"""
ui.py
User interface for the MP3 player using CustomTkinter
WinPlay3 / Windows 95 retro style with track list and album art
"""

import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageTk
import os

class PlayerUI:
    def __init__(self, audio_player, default_music_folder=None):
        """Initialize the UI"""
        self.audio_player = audio_player
        self.default_music_folder = default_music_folder
        
        # Create main window
        self.window = ctk.CTk()
        self.window.title("WinPlay3")
        self.window.geometry("710x500")
        self.window.resizable(False, False)
        
        # Windows 95 color scheme
        self.win95_gray = "#C0C0C0"
        self.win95_dark_gray = "#808080"
        self.win95_light_gray = "#DFDFDF"
        self.lcd_green = "#00FF00"
        self.lcd_bg = "#000000"
        self.tracklist_bg = "#A8A8A8"  # Slightly darker grey for tracklist
        
        # Album art
        self.current_album_art = None
        self.album_art_label = None
        
        # Build the interface
        self.create_widgets()
        
        # Start the update loop
        self.update_time_display()
        
    def create_widgets(self):
        """Create all UI elements"""
        
        # Main container
        main_frame = ctk.CTkFrame(self.window, fg_color=self.win95_gray, corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Menu bar
        menu_bar = ctk.CTkFrame(main_frame, fg_color=self.win95_gray, height=25, corner_radius=0)
        menu_bar.pack(fill="x")
        
        file_label = ctk.CTkLabel(menu_bar, text="File", text_color="black", font=("Arial", 11), padx=10)
        file_label.pack(side="left")
        
        options_label = ctk.CTkLabel(menu_bar, text="Options", text_color="black", font=("Arial", 11), padx=10)
        options_label.pack(side="left")
        
        help_label = ctk.CTkLabel(menu_bar, text="Help", text_color="black", font=("Arial", 11), padx=10)
        help_label.pack(side="right")
        
        # Content area (split into left and right)
        content_frame = ctk.CTkFrame(main_frame, fg_color=self.win95_gray, corner_radius=0)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # LEFT SIDE: Album art + Controls
        left_frame = ctk.CTkFrame(content_frame, fg_color=self.win95_gray, corner_radius=0, width=350)
        left_frame.pack(side="left", fill="both", padx=(0, 10))
        left_frame.pack_propagate(False)
        
        # Album Art - INCREASED SIZE
        art_frame = ctk.CTkFrame(left_frame, fg_color=self.lcd_bg, corner_radius=0, height=285, 
                                  border_width=2, border_color=self.win95_dark_gray)
        art_frame.pack(fill="x", pady=(0, 10))
        art_frame.pack_propagate(False)
        
        self.album_art_label = ctk.CTkLabel(art_frame, text="No Album Art", text_color=self.lcd_green,
                                             font=("Courier", 12, "bold"), fg_color=self.lcd_bg)
        self.album_art_label.pack(expand=True)
        
        # LCD Display
        lcd_frame = ctk.CTkFrame(left_frame, fg_color=self.lcd_bg, corner_radius=0, height=90,
                                  border_width=2, border_color=self.win95_dark_gray)
        lcd_frame.pack(fill="x", pady=(0, 10))
        lcd_frame.pack_propagate(False)
        
        # Top row - Track info
        top_row = ctk.CTkFrame(lcd_frame, fg_color=self.lcd_bg, corner_radius=0)
        top_row.pack(fill="x", padx=5, pady=(5, 2))
        
        track_label = ctk.CTkLabel(top_row, text="TRACK", text_color=self.lcd_green,
                                    font=("Courier", 10, "bold"), fg_color=self.lcd_bg)
        track_label.pack(side="left", padx=5)
        
        self.track_num = ctk.CTkLabel(top_row, text="1", text_color=self.lcd_green,
                                       font=("Courier", 16, "bold"), fg_color=self.lcd_bg)
        self.track_num.pack(side="left")
        
        # Time display
        time_frame = ctk.CTkFrame(top_row, fg_color=self.lcd_bg, corner_radius=0)
        time_frame.pack(side="left", padx=20)
        
        time_labels = ctk.CTkFrame(time_frame, fg_color=self.lcd_bg, corner_radius=0)
        time_labels.pack()
        
        min_label = ctk.CTkLabel(time_labels, text="MIN", text_color=self.lcd_green,
                                  font=("Courier", 10, "bold"), fg_color=self.lcd_bg)
        min_label.grid(row=0, column=0, padx=2)
        
        sec_label = ctk.CTkLabel(time_labels, text="SEC", text_color=self.lcd_green,
                                  font=("Courier", 10, "bold"), fg_color=self.lcd_bg)
        sec_label.grid(row=0, column=1, padx=2)
        
        self.time_display = ctk.CTkLabel(time_frame, text="0:00 / 0:00", text_color=self.lcd_green,
                                          font=("Courier", 16, "bold"), fg_color=self.lcd_bg)
        self.time_display.pack()
        
        # Mode indicator
        mode_label = ctk.CTkLabel(top_row, text="MODE", text_color=self.lcd_green,
                                   font=("Courier", 10, "bold"), fg_color=self.lcd_bg)
        mode_label.pack(side="right", padx=5)
        
        # Song name
        self.song_display = ctk.CTkLabel(lcd_frame, text="No file loaded", text_color=self.lcd_green,
                                          font=("Courier", 11, "bold"), fg_color=self.lcd_bg,
                                          anchor="w", padx=10)
        self.song_display.pack(fill="x", pady=(5, 8), padx=5)
        
        # Transport controls
        controls_frame = ctk.CTkFrame(left_frame, fg_color=self.win95_gray, corner_radius=0)
        controls_frame.pack(pady=10)
        
        button_config = {
            "width": 50,
            "height": 35,
            "corner_radius": 3,
            "fg_color": self.win95_light_gray,
            "hover_color": self.win95_gray,
            "text_color": "black",
            "border_width": 2,
            "border_color": self.win95_dark_gray,
            "font": ("Arial", 14, "bold")
        }
        
        self.play_btn = ctk.CTkButton(controls_frame, text="▶", command=self.play_music, **button_config)
        self.play_btn.grid(row=0, column=0, padx=3)
        
        self.stop_btn = ctk.CTkButton(controls_frame, text="■", command=self.stop_music, **button_config)
        self.stop_btn.grid(row=0, column=1, padx=3)
        
        self.pause_btn = ctk.CTkButton(controls_frame, text="II", command=self.pause_music, **button_config)
        self.pause_btn.grid(row=0, column=2, padx=3)
        
        self.prev_btn = ctk.CTkButton(controls_frame, text="⏮", command=self.previous_track, **button_config)
        self.prev_btn.grid(row=0, column=3, padx=3)
        
        self.next_btn = ctk.CTkButton(controls_frame, text="⏭", command=self.next_track, **button_config)
        self.next_btn.grid(row=0, column=4, padx=3)
        
        # Load Folder button
        self.folder_btn = ctk.CTkButton(controls_frame, text="📁", command=self.load_folder,
                                         width=50, height=35, corner_radius=3,
                                         fg_color=self.win95_light_gray, hover_color=self.win95_gray,
                                         text_color="black", border_width=2,
                                         border_color=self.win95_dark_gray, font=("Arial", 12, "bold"))
        self.folder_btn.grid(row=0, column=5, padx=3)
        
        # Volume control
        volume_frame = ctk.CTkFrame(left_frame, fg_color=self.win95_gray, corner_radius=0)
        volume_frame.pack(pady=5)
        
        vol_label = ctk.CTkLabel(volume_frame, text="VOL", text_color="black", font=("Arial", 10, "bold"))
        vol_label.pack(side="left", padx=5)
        
        self.volume_slider = ctk.CTkSlider(volume_frame, from_=0, to=100, command=self.change_volume,
                                            width=200, height=15, button_color=self.win95_dark_gray,
                                            button_hover_color=self.win95_gray, progress_color=self.lcd_green,
                                            fg_color=self.win95_dark_gray)
        self.volume_slider.set(70)
        self.volume_slider.pack(side="left", padx=5)
        
        self.volume_label = ctk.CTkLabel(volume_frame, text="70%", text_color="black",
                                          font=("Arial", 10, "bold"), width=40)
        self.volume_label.pack(side="left", padx=5)
        
        # RIGHT SIDE: Track List
        right_frame = ctk.CTkFrame(content_frame, fg_color=self.win95_gray, corner_radius=0)
        right_frame.pack(side="right", fill="both", expand=True)
        
        # Track list header
        tracklist_header = ctk.CTkLabel(right_frame, text="TRACK LIST", text_color="black",
                                         font=("Arial", 12, "bold"), anchor="w")
        tracklist_header.pack(fill="x", pady=(0, 5))
        
        # Scrollable track list - DARKER GREY BACKGROUND
        self.tracklist_frame = ctk.CTkScrollableFrame(right_frame, fg_color=self.tracklist_bg, corner_radius=0,
                                                       border_width=2, border_color=self.win95_dark_gray)
        self.tracklist_frame.pack(fill="both", expand=True)
        
    def load_folder(self):
        """Load a folder of music files"""
        folder_path = filedialog.askdirectory(
            title="Select Music Folder",
            initialdir=self.default_music_folder if self.default_music_folder else "/"
        )
        
        if folder_path:
            if self.audio_player.load_folder(folder_path):
                self.populate_tracklist()
                # Load first track
                if self.audio_player.playlist:
                    self.audio_player.load_file(self.audio_player.playlist[0])
                    self.audio_player.current_track_index = 0
                    self.update_current_track_display()
    
    def populate_tracklist(self):
        """Populate the track list widget with current playlist"""
        # Clear existing tracks
        for widget in self.tracklist_frame.winfo_children():
            widget.destroy()
        
        # Add each track
        for idx, file_path in enumerate(self.audio_player.playlist):
            filename = os.path.basename(file_path)
            # Remove extension
            track_name = os.path.splitext(filename)[0]
            
            # Get duration
            duration = self.audio_player.get_file_duration(file_path)
            duration_str = self.audio_player.format_time(duration)
            
            # Create track frame - MATCH TRACKLIST BACKGROUND
            track_frame = ctk.CTkFrame(self.tracklist_frame, fg_color=self.tracklist_bg, corner_radius=0)
            track_frame.pack(fill="x", pady=1)
            
            # Track number
            track_num_label = ctk.CTkLabel(track_frame, text=f"{idx + 1:02d}.", text_color="black",
                                            font=("Arial", 10), width=30, anchor="w")
            track_num_label.pack(side="left", padx=5)
            
            # Track name
            track_name_label = ctk.CTkLabel(track_frame, text=track_name, text_color="black",
                                             font=("Arial", 10), anchor="w")
            track_name_label.pack(side="left", fill="x", expand=True, padx=5)
            
            # Duration
            duration_label = ctk.CTkLabel(track_frame, text=duration_str, text_color="black",
                                           font=("Arial", 10), width=50, anchor="e")
            duration_label.pack(side="right", padx=5)
            
            # Make track clickable
            track_frame.bind("<Button-1>", lambda e, i=idx: self.play_track_from_list(i))
            track_num_label.bind("<Button-1>", lambda e, i=idx: self.play_track_from_list(i))
            track_name_label.bind("<Button-1>", lambda e, i=idx: self.play_track_from_list(i))
            duration_label.bind("<Button-1>", lambda e, i=idx: self.play_track_from_list(i))
    
    def play_track_from_list(self, index):
        """Play a track when clicked in the list"""
        if self.audio_player.play_track_at_index(index):
            self.update_current_track_display()
    
    def update_current_track_display(self):
        """Update displays when track changes"""
        if self.audio_player.current_file:
            filename = self.audio_player.get_current_filename()
            if len(filename) > 35:
                filename = filename[:32] + "..."
            self.song_display.configure(text=f"▶ {filename}")
            
            # Update track number
            if self.audio_player.current_track_index >= 0:
                self.track_num.configure(text=str(self.audio_player.current_track_index + 1))
            
            # Update album art
            self.update_album_art()
    
    def update_album_art(self):
        """Extract and display album art"""
        if self.audio_player.current_file:
            album_art = self.audio_player.get_album_art(self.audio_player.current_file)
            
            if album_art:
                # Resize to fit the larger frame (280x280 max)
                album_art.thumbnail((280, 280), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(album_art)
                self.current_album_art = photo  # Keep reference
                self.album_art_label.configure(image=photo, text="")
            else:
                self.album_art_label.configure(image=None, text="No Album Art")
    
    def update_time_display(self):
        """Update the time display every 100ms"""
        if self.audio_player.current_file:
            current_time = self.audio_player.get_position()
            total_time = self.audio_player.get_duration()
            
            current_str = self.audio_player.format_time(current_time)
            total_str = self.audio_player.format_time(total_time)
            
            self.time_display.configure(text=f"{current_str} / {total_str}")
            
            # Auto-play next track when current ends
            if self.audio_player.is_playing and current_time >= total_time and total_time > 0:
                if self.audio_player.play_next():
                    self.update_current_track_display()
                else:
                    self.stop_music()
        else:
            self.time_display.configure(text="0:00 / 0:00")
        
        self.window.after(100, self.update_time_display)
    
    def play_music(self):
        """Play button handler"""
        if self.audio_player.play():
            self.update_current_track_display()
        else:
            self.song_display.configure(text="No file loaded")
    
    def pause_music(self):
        """Pause button handler"""
        if self.audio_player.pause():
            filename = self.audio_player.get_current_filename()
            if filename:
                if len(filename) > 35:
                    filename = filename[:32] + "..."
                self.song_display.configure(text=f"II {filename}")
    
    def stop_music(self):
        """Stop button handler"""
        self.audio_player.stop()
        filename = self.audio_player.get_current_filename()
        if filename:
            if len(filename) > 35:
                filename = filename[:32] + "..."
            self.song_display.configure(text=f"■ {filename}")
    
    def previous_track(self):
        """Previous track handler"""
        if self.audio_player.play_previous():
            self.update_current_track_display()
        else:
            self.song_display.configure(text="⏮ No previous track")
    
    def next_track(self):
        """Next track handler"""
        if self.audio_player.play_next():
            self.update_current_track_display()
        else:
            self.song_display.configure(text="⏭ No next track")
    
    def change_volume(self, value):
        """Volume slider handler"""
        volume = float(value) / 100
        self.audio_player.set_volume(volume)
        self.volume_label.configure(text=f"{int(value)}%")
    
    def run(self):
        """Start the application"""
        self.window.mainloop()