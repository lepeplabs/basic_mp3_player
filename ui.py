"""
ui.py
User interface for the MP3 player using CustomTkinter
WinPlay3 / Windows 95 retro style
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
        self.window.title("WinPlay3")
        self.window.geometry("400x280")
        self.window.resizable(False, False)
        
        # Windows 95 color scheme
        self.win95_gray = "#C0C0C0"
        self.win95_dark_gray = "#808080"
        self.win95_light_gray = "#DFDFDF"
        self.lcd_green = "#00FF00"
        self.lcd_bg = "#000000"
        
        # Build the interface
        self.create_widgets()
        
        # Start the update loop for time display
        self.update_time_display()
        
    def create_widgets(self):
        """Create all UI elements in WinPlay3 style"""
        
        # Main container with Windows 95 gray background
        main_frame = ctk.CTkFrame(self.window, fg_color=self.win95_gray, corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Menu bar (simulated)
        menu_bar = ctk.CTkFrame(main_frame, fg_color=self.win95_gray, height=25, corner_radius=0)
        menu_bar.pack(fill="x", padx=0, pady=0)
        
        file_label = ctk.CTkLabel(menu_bar, text="File", text_color="black", 
                                   font=("Arial", 11), anchor="w", padx=10)
        file_label.pack(side="left")
        
        options_label = ctk.CTkLabel(menu_bar, text="Options", text_color="black", 
                                      font=("Arial", 11), anchor="w", padx=10)
        options_label.pack(side="left")
        
        help_label = ctk.CTkLabel(menu_bar, text="Help", text_color="black", 
                                   font=("Arial", 11), anchor="w", padx=10)
        help_label.pack(side="right")
        
        # LCD Display area
        lcd_frame = ctk.CTkFrame(main_frame, fg_color=self.lcd_bg, 
                                  corner_radius=0, height=90, border_width=2,
                                  border_color=self.win95_dark_gray)
        lcd_frame.pack(fill="x", padx=10, pady=10)
        lcd_frame.pack_propagate(False)
        
        # Top row of LCD - Track info
        top_row = ctk.CTkFrame(lcd_frame, fg_color=self.lcd_bg, corner_radius=0)
        top_row.pack(fill="x", padx=5, pady=(5, 2))
        
        track_label = ctk.CTkLabel(top_row, text="TRACK", text_color=self.lcd_green,
                                    font=("Courier", 10, "bold"), fg_color=self.lcd_bg)
        track_label.pack(side="left", padx=5)
        
        self.track_num = ctk.CTkLabel(top_row, text="1", text_color=self.lcd_green,
                                       font=("Courier", 16, "bold"), fg_color=self.lcd_bg)
        self.track_num.pack(side="left")
        
        # Time display - showing current / total
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
        
        # Current time / Total time display
        self.time_display = ctk.CTkLabel(time_frame, text="0:00 / 0:00", text_color=self.lcd_green,
                                          font=("Courier", 16, "bold"), fg_color=self.lcd_bg)
        self.time_display.pack()
        
        # Mode indicator
        mode_label = ctk.CTkLabel(top_row, text="MODE", text_color=self.lcd_green,
                                   font=("Courier", 10, "bold"), fg_color=self.lcd_bg)
        mode_label.pack(side="right", padx=5)
        
        # Bottom row - Song name with proper spacing
        self.song_display = ctk.CTkLabel(lcd_frame, text="No file loaded", 
                                          text_color=self.lcd_green,
                                          font=("Courier", 11, "bold"), 
                                          fg_color=self.lcd_bg,
                                          anchor="w",
                                          padx=10)
        self.song_display.pack(fill="x", pady=(5, 8), padx=5)
        
        # Transport controls container
        controls_frame = ctk.CTkFrame(main_frame, fg_color=self.win95_gray, corner_radius=0)
        controls_frame.pack(pady=10)
        
        # Button style configuration
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
        
        # Transport buttons
        self.play_btn = ctk.CTkButton(controls_frame, text="▶", 
                                       command=self.play_music, **button_config)
        self.play_btn.grid(row=0, column=0, padx=3)
        
        self.stop_btn = ctk.CTkButton(controls_frame, text="■", 
                                       command=self.stop_music, **button_config)
        self.stop_btn.grid(row=0, column=1, padx=3)
        
        self.pause_btn = ctk.CTkButton(controls_frame, text="II", 
                                        command=self.pause_music, **button_config)
        self.pause_btn.grid(row=0, column=2, padx=3)
        
        self.prev_btn = ctk.CTkButton(controls_frame, text="⏮", 
                                       command=self.previous_track, **button_config)
        self.prev_btn.grid(row=0, column=3, padx=3)
        
        self.next_btn = ctk.CTkButton(controls_frame, text="⏭", 
                                       command=self.next_track, **button_config)
        self.next_btn.grid(row=0, column=4, padx=3)
        
        # Browse button
        self.browse_btn = ctk.CTkButton(controls_frame, text="...", 
                                         command=self.browse_file,
                                         width=50, height=35, corner_radius=3,
                                         fg_color=self.win95_light_gray,
                                         hover_color=self.win95_gray,
                                         text_color="black", border_width=2,
                                         border_color=self.win95_dark_gray,
                                         font=("Arial", 12, "bold"))
        self.browse_btn.grid(row=0, column=5, padx=3)
        
        # Volume control
        volume_frame = ctk.CTkFrame(main_frame, fg_color=self.win95_gray, corner_radius=0)
        volume_frame.pack(pady=5)
        
        vol_label = ctk.CTkLabel(volume_frame, text="VOL", text_color="black",
                                  font=("Arial", 10, "bold"))
        vol_label.pack(side="left", padx=5)
        
        self.volume_slider = ctk.CTkSlider(
            volume_frame,
            from_=0,
            to=100,
            command=self.change_volume,
            width=200,
            height=15,
            button_color=self.win95_dark_gray,
            button_hover_color=self.win95_gray,
            progress_color=self.lcd_green,
            fg_color=self.win95_dark_gray
        )
        self.volume_slider.set(70)
        self.volume_slider.pack(side="left", padx=5)
        
        self.volume_label = ctk.CTkLabel(volume_frame, text="70%", text_color="black",
                                          font=("Arial", 10, "bold"), width=40)
        self.volume_label.pack(side="left", padx=5)
    
    def update_time_display(self):
        """Update the time display every 100ms"""
        if self.audio_player.current_file:
            # Get current position and total duration
            current_time = self.audio_player.get_position()
            total_time = self.audio_player.get_duration()
            
            # Format times
            current_str = self.audio_player.format_time(current_time)
            total_str = self.audio_player.format_time(total_time)
            
            # Update display with "current / total" format
            self.time_display.configure(text=f"{current_str} / {total_str}")
            
            # Check if song has ended
            if self.audio_player.is_playing and current_time >= total_time and total_time > 0:
                self.stop_music()
        else:
            # No file loaded
            self.time_display.configure(text="0:00 / 0:00")
        
        # Schedule next update (100ms = 0.1 seconds)
        self.window.after(100, self.update_time_display)
        
    def browse_file(self):
        """Open file dialog to select audio file"""
        initial_dir = self.default_music_folder if self.default_music_folder else "/"
        
        if self.default_music_folder and not os.path.exists(self.default_music_folder):
            print(f"Warning: Default folder '{self.default_music_folder}' not found.")
            initial_dir = "/"
        
        file_path = filedialog.askopenfilename(
            title="Select Audio File",
            initialdir=initial_dir,
            filetypes=[
                ("Audio Files", "*.mp3 *.m4a *.aac *.wma *.wav *.flac"),
                ("MP3 Files", "*.mp3"),
                ("AAC Files", "*.m4a *.aac"),
                ("WMA Files", "*.wma"),
                ("WAV Files", "*.wav"),
                ("FLAC Files", "*.flac"),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            # Check for M4P before trying to load
            if file_path.lower().endswith('.m4p'):
                self.song_display.configure(text="M4P files are DRM-protected")
                return
                
            if self.audio_player.load_file(file_path):
                filename = self.audio_player.get_current_filename()
                if len(filename) > 35:
                    filename = filename[:32] + "..."
                self.song_display.configure(text=filename)
                # Time display will update automatically via update_time_display()
            else:
                self.song_display.configure(text="Error loading file")
    
    def play_music(self):
        """Play button handler"""
        if self.audio_player.play():
            filename = self.audio_player.get_current_filename()
            if filename:
                if len(filename) > 35:
                    filename = filename[:32] + "..."
                self.song_display.configure(text=f"▶ {filename}")
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
        """Previous track - placeholder for future playlist feature"""
        self.song_display.configure(text="⏮ No playlist")
    
    def next_track(self):
        """Next track - placeholder for future playlist feature"""
        self.song_display.configure(text="⏭ No playlist")
    
    def change_volume(self, value):
        """Volume slider handler"""
        volume = float(value) / 100
        self.audio_player.set_volume(volume)
        self.volume_label.configure(text=f"{int(value)}%")
    
    def run(self):
        """Start the application"""
        self.window.mainloop()