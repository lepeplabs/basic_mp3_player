"""
ui.py
User interface for the MP3 player using CustomTkinter
lepeplabs_audio_thing / Windows 95 retro style with track list and album art
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import io
import os
import json

CONFIG_PATH = os.path.expanduser("~/.lepeplabs_player.json")

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES

    class _DnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
        """CustomTkinter window with drag-and-drop support (degrades gracefully)"""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            try:
                self.TkdndVersion = TkinterDnD._require(self)
                self._dnd_working = True
            except RuntimeError:
                self.TkdndVersion = None
                self._dnd_working = False

    _DND_AVAILABLE = True
except ImportError:
    _DND_AVAILABLE = False

class PlayerUI:
    def __init__(self, audio_player):
        """Initialize the UI"""
        self.audio_player = audio_player
        self.default_music_folder = self._load_config().get('last_folder')
        
        # Create main window — always one Tk instance; DnD activates only if the
        # native tkdnd library loaded successfully inside _DnDCTk.__init__
        if _DND_AVAILABLE:
            self.window = _DnDCTk()
            self._dnd_active = self.window._dnd_working
        else:
            self.window = ctk.CTk()
            self._dnd_active = False
        self.window.title("lepeplabs_audio_thing")
        self.window.geometry("780x660")
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

        # Track list row references for highlighting
        self.track_frames = []  # list of (frame, [child_labels])

        # Seek/scrub state
        self.seeking = False
        self._seek_pending = 0.0

        # Album art pending save
        self._pending_art_image = None

        # Folder expand/collapse state: {key: bool}
        self.folder_states = {}

        # Sort / group mode and metadata cache
        self.sort_mode = 'folder'
        self._meta_cache = {}
        self._sort_buttons = {}
        self._sort_bar = None

        # Search state
        self._search_text = ''
        self._search_frame = None
        self._search_btn = None

        # Radio state
        self._radio_frame = None
        self._radio_btn = None
        self._radio_playing = False
        self._radio_favs_inner = None
        self._radio_favourites = self._load_config().get('radio_favourites', [])
        
        # Build the interface
        self.create_widgets()
        self._bind_keyboard_shortcuts()
        if self._dnd_active:
            self.window.drop_target_register(DND_FILES)
            self.window.dnd_bind('<<Drop>>', self._on_drop)

        # Auto-load last used folder
        if self.default_music_folder and os.path.exists(self.default_music_folder):
            if self.audio_player.add_folder(self.default_music_folder):
                self.populate_tracklist()

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
        
        file_label = ctk.CTkLabel(menu_bar, text="File", text_color="black", font=("Arial", 11), padx=10,
                                   cursor="hand2")
        file_label.pack(side="left")
        file_label.bind("<Button-1>", self._show_file_menu)
        
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
        art_frame = ctk.CTkFrame(left_frame, fg_color=self.lcd_bg, corner_radius=0, height=265,
                                  border_width=2, border_color=self.win95_dark_gray)
        art_frame.pack(fill="x", pady=(0, 2))
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
        
        # Metadata display (artist / album · year)
        meta_frame = ctk.CTkFrame(left_frame, fg_color=self.lcd_bg, corner_radius=0, height=48,
                                   border_width=2, border_color=self.win95_dark_gray)
        meta_frame.pack(fill="x", pady=(0, 10))
        meta_frame.pack_propagate(False)

        self.artist_display = ctk.CTkLabel(meta_frame, text="", text_color=self.lcd_green,
                                            font=("Courier", 10, "bold"), fg_color=self.lcd_bg,
                                            anchor="w", padx=10)
        self.artist_display.pack(fill="x", pady=(4, 0))

        self.album_display = ctk.CTkLabel(meta_frame, text="", text_color=self.lcd_green,
                                           font=("Courier", 10, "bold"), fg_color=self.lcd_bg,
                                           anchor="w", padx=10)
        self.album_display.pack(fill="x", pady=(0, 4))

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

        # Shuffle and Repeat buttons (second row)
        self.shuffle_btn = ctk.CTkButton(controls_frame, text="🔀", command=self.toggle_shuffle,
                                          width=80, height=28, corner_radius=3,
                                          fg_color=self.win95_light_gray, hover_color=self.win95_gray,
                                          text_color="black", border_width=2,
                                          border_color=self.win95_dark_gray, font=("Arial", 11))
        self.shuffle_btn.grid(row=1, column=0, columnspan=3, padx=3, pady=(5, 0))

        self.repeat_btn = ctk.CTkButton(controls_frame, text="🔁 Off", command=self.cycle_repeat,
                                         width=110, height=28, corner_radius=3,
                                         fg_color=self.win95_light_gray, hover_color=self.win95_gray,
                                         text_color="black", border_width=2,
                                         border_color=self.win95_dark_gray, font=("Arial", 11))
        self.repeat_btn.grid(row=1, column=3, columnspan=3, padx=3, pady=(5, 0))

        # Clear All button (third row)
        ctk.CTkButton(controls_frame, text="🗑 Clear All", command=self.clear_all,
                      width=200, height=24, corner_radius=3,
                      fg_color=self.win95_light_gray, hover_color="#CC4444",
                      text_color="black", border_width=2,
                      border_color=self.win95_dark_gray, font=("Arial", 10, "bold")
                      ).grid(row=2, column=0, columnspan=6, padx=3, pady=(5, 0))

        # Progress / seek bar
        seek_frame = ctk.CTkFrame(left_frame, fg_color=self.win95_gray, corner_radius=0)
        seek_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.seek_slider = ctk.CTkSlider(seek_frame, from_=0, to=100, command=self._on_seek_drag,
                                          height=14, button_color=self.win95_dark_gray,
                                          button_hover_color="#505050",
                                          progress_color=self.lcd_green,
                                          fg_color=self.win95_dark_gray)
        self.seek_slider.set(0)
        self.seek_slider.pack(fill="x")
        # Bind press/release on the internal canvas so we know when dragging starts/ends
        self.seek_slider._canvas.bind("<ButtonPress-1>", self._seek_start)
        self.seek_slider._canvas.bind("<ButtonRelease-1>", self._seek_end)

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
        
        # Track list header row
        header_row = ctk.CTkFrame(right_frame, fg_color=self.win95_gray, corner_radius=0)
        header_row.pack(fill="x", pady=(0, 5))

        tracklist_header = ctk.CTkLabel(header_row, text="TRACK LIST", text_color="black",
                                         font=("Arial", 12, "bold"), anchor="w")
        tracklist_header.pack(side="left")

        playlist_btn_cfg = {
            "width": 60, "height": 22, "corner_radius": 3,
            "fg_color": self.win95_light_gray, "hover_color": self.win95_gray,
            "text_color": "black", "border_width": 2,
            "border_color": self.win95_dark_gray, "font": ("Arial", 9, "bold")
        }
        ctk.CTkButton(header_row, text="💾 Save", command=self.save_playlist,
                      **playlist_btn_cfg).pack(side="right", padx=(3, 0))

        self._radio_btn = ctk.CTkButton(header_row, text="📻", command=self._toggle_radio,
                                         **{**playlist_btn_cfg, "width": 32})
        self._radio_btn.pack(side="right", padx=(3, 0))

        ctk.CTkButton(header_row, text="📂 Load", command=self.load_playlist,
                      **playlist_btn_cfg).pack(side="right", padx=(3, 0))

        self._search_btn = ctk.CTkButton(header_row, text="🔍", command=self._toggle_search,
                                          **{**playlist_btn_cfg, "width": 32})
        self._search_btn.pack(side="right", padx=(3, 0))

        # ── Radio panel (hidden by default, built by helper) ─────────
        self._radio_frame = self._build_radio_panel(right_frame)

        # Collapsible search bar (hidden by default)
        self._search_frame = ctk.CTkFrame(right_frame, fg_color=self.win95_gray, corner_radius=0)
        search_entry = ctk.CTkEntry(self._search_frame, placeholder_text="Search tracks...",
                                    height=24, corner_radius=2,
                                    fg_color="white", text_color="black",
                                    border_color=self.win95_dark_gray, border_width=1,
                                    font=("Arial", 10))
        search_entry.pack(fill="x", padx=4, pady=2)
        search_entry.bind("<KeyRelease>", self._on_search_change)
        self._search_entry = search_entry

        # Sort / group bar
        sort_bar = ctk.CTkFrame(right_frame, fg_color=self.win95_gray, corner_radius=0)
        sort_bar.pack(fill="x", pady=(0, 4))
        self._sort_bar = sort_bar

        ctk.CTkLabel(sort_bar, text="Group by:", text_color="black",
                     font=("Arial", 9), fg_color=self.win95_gray).pack(side="left", padx=(2, 4))

        sort_btn_cfg = {
            "height": 20, "corner_radius": 2, "border_width": 1,
            "border_color": self.win95_dark_gray, "font": ("Arial", 9, "bold")
        }
        for mode, label in [("folder", "📁 Folder"), ("artist", "👤 Artist"),
                             ("album", "💿 Album"),  ("genre",  "🎵 Genre")]:
            btn = ctk.CTkButton(sort_bar, text=label, width=68,
                                fg_color="#000080" if mode == "folder" else self.win95_light_gray,
                                hover_color=self.win95_gray,
                                text_color="white" if mode == "folder" else "black",
                                command=lambda m=mode: self._set_sort_mode(m),
                                **sort_btn_cfg)
            btn.pack(side="left", padx=2)
            self._sort_buttons[mode] = btn

        # Scrollable track list - DARKER GREY BACKGROUND
        self.tracklist_frame = ctk.CTkScrollableFrame(right_frame, fg_color=self.tracklist_bg, corner_radius=0,
                                                       border_width=2, border_color=self.win95_dark_gray)
        self.tracklist_frame.pack(fill="both", expand=True)
        
    def load_folder(self):
        """Add a music folder to the library (additive)"""
        folder_path = filedialog.askdirectory(
            title="Select Music Folder",
            initialdir=self.default_music_folder if self.default_music_folder else "/"
        )
        if folder_path:
            if self.audio_player.add_folder(folder_path):
                self._save_config({'last_folder': folder_path})
                self.default_music_folder = folder_path
                self.populate_tracklist()
                if self.audio_player.current_track_index < 0 and self.audio_player.playlist:
                    self.audio_player.load_file(self.audio_player.playlist[0])
                    self.audio_player.current_track_index = 0
                    self.update_current_track_display()
    
    def _toggle_radio(self):
        """Show or hide the radio panel; stops stream when closing"""
        if self._radio_frame.winfo_ismapped():
            if self._radio_playing:
                self._stop_radio()
            self._radio_frame.pack_forget()
            self._radio_btn.configure(fg_color=self.win95_light_gray, text_color="black")
        else:
            self._radio_frame.pack(fill="x", pady=(0, 4), before=self._sort_bar)
            self._radio_btn.configure(fg_color="#000080", text_color="white")

    def _radio_play_url(self):
        """Play the URL typed into the entry"""
        url = self._radio_url_entry.get().strip()
        if url:
            self._start_radio(url, url)

    def _radio_play_preset(self, name, url):
        """Play a preset station"""
        self._radio_url_entry.delete(0, 'end')
        self._radio_url_entry.insert(0, url)
        self._start_radio(name, url)

    def _start_radio(self, name, url):
        """Stop any local playback and start streaming"""
        self.audio_player.stop()
        if self.audio_player.play_stream(url):
            self._radio_playing = True
            self._radio_play_btn.configure(text="■ Stop", command=self._stop_radio)
            self.song_display.configure(text=f"📻 {name[:30]}")
            self.time_display.configure(text="LIVE")
            self.artist_display.configure(text="")
            self.album_display.configure(text="")
            self.album_art_label.configure(image=None, text="📻 LIVE")
        else:
            self.song_display.configure(text="Stream error — check URL")

    def _stop_radio(self):
        """Stop the radio stream"""
        self.audio_player.stop_stream()
        self._radio_playing = False
        self._radio_play_btn.configure(text="▶ Play", command=self._radio_play_url)
        self.song_display.configure(text="No file loaded")
        self.time_display.configure(text="0:00 / 0:00")
        self.album_art_label.configure(image=None, text="No Album Art")

    # ------------------------------------------------------------------ #
    #  Radio panel builder + favourites                                   #
    # ------------------------------------------------------------------ #

    def _build_radio_panel(self, parent):
        """Build the full radio panel widget and return it (hidden by default)"""
        PRESETS = [
            ("BBC Radio 1",   "http://stream.live.vc.bbcmedia.co.uk/bbc_radio_one"),
            ("BBC Radio 2",   "http://stream.live.vc.bbcmedia.co.uk/bbc_radio_two"),
            ("Jazz FM",       "http://edge-bauerse03.sharp-stream.com/jazzfmuk_mp3_128"),
            ("SomaFM Groove", "http://ice2.somafm.com/groovesalad-128-mp3"),
            ("SomaFM Drone",  "http://ice2.somafm.com/dronezone-128-mp3"),
        ]

        frame = ctk.CTkFrame(parent, fg_color=self.win95_gray, corner_radius=0,
                              border_width=1, border_color=self.win95_dark_gray)

        # URL entry + play + save-favourite row
        url_row = ctk.CTkFrame(frame, fg_color=self.win95_gray, corner_radius=0)
        url_row.pack(fill="x", padx=4, pady=(4, 2))

        self._radio_url_entry = ctk.CTkEntry(
            url_row, placeholder_text="Stream URL...",
            height=24, corner_radius=2,
            fg_color="white", text_color="black",
            border_color=self.win95_dark_gray, border_width=1,
            font=("Arial", 9))
        self._radio_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._radio_play_btn = ctk.CTkButton(
            url_row, text="▶ Play", width=58, height=24,
            corner_radius=2, font=("Arial", 9, "bold"),
            fg_color=self.win95_light_gray, hover_color=self.win95_gray,
            text_color="black", border_width=1,
            border_color=self.win95_dark_gray,
            command=self._radio_play_url)
        self._radio_play_btn.pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            url_row, text="★ Save", width=58, height=24,
            corner_radius=2, font=("Arial", 9, "bold"),
            fg_color=self.win95_light_gray, hover_color="#DAA520",
            text_color="black", border_width=1,
            border_color=self.win95_dark_gray,
            command=self._radio_save_favourite).pack(side="left")

        # Built-in preset station buttons
        presets_row = ctk.CTkFrame(frame, fg_color=self.win95_gray, corner_radius=0)
        presets_row.pack(fill="x", padx=4, pady=(0, 2))

        for name, url in PRESETS:
            ctk.CTkButton(
                presets_row, text=name, height=20, corner_radius=2,
                fg_color=self.win95_light_gray, hover_color="#000080",
                text_color="black", border_width=1,
                border_color=self.win95_dark_gray, font=("Arial", 8),
                command=lambda u=url, n=name: self._radio_play_preset(n, u)
            ).pack(side="left", padx=2, pady=1)

        # Saved stations header
        ctk.CTkLabel(frame, text="── Saved Stations ──",
                     text_color=self.win95_dark_gray, font=("Arial", 8),
                     fg_color=self.win95_gray, anchor="w"
                     ).pack(fill="x", padx=6, pady=(3, 0))

        # Inner frame that gets cleared/repopulated on add/remove
        self._radio_favs_inner = ctk.CTkFrame(frame, fg_color=self.win95_gray, corner_radius=0)
        self._radio_favs_inner.pack(fill="x", padx=4, pady=(0, 4))

        self._radio_refresh_favourites()
        return frame

    def _radio_refresh_favourites(self):
        """Clear and repopulate the saved stations inner frame"""
        if self._radio_favs_inner is None:
            return
        for w in self._radio_favs_inner.winfo_children():
            w.destroy()

        if not self._radio_favourites:
            ctk.CTkLabel(
                self._radio_favs_inner,
                text="No saved stations — play a stream and click ★ Save",
                text_color=self.win95_dark_gray, font=("Arial", 8),
                fg_color=self.win95_gray
            ).pack(anchor="w", padx=4, pady=2)
            return

        for i, fav in enumerate(self._radio_favourites):
            row = ctk.CTkFrame(self._radio_favs_inner, fg_color=self.win95_gray, corner_radius=0)
            row.pack(fill="x", pady=1)
            ctk.CTkButton(
                row, text=f"▶  {fav['name']}", height=20, corner_radius=2,
                anchor="w", font=("Arial", 8),
                fg_color=self.win95_light_gray, hover_color="#000080",
                text_color="black", border_width=1,
                border_color=self.win95_dark_gray,
                command=lambda n=fav['name'], u=fav['url']: self._radio_play_preset(n, u)
            ).pack(side="left", fill="x", expand=True, padx=(0, 4))
            ctk.CTkButton(
                row, text="✕", width=24, height=20, corner_radius=2,
                fg_color=self.win95_light_gray, hover_color="#CC4444",
                text_color="black", border_width=1,
                border_color=self.win95_dark_gray, font=("Arial", 9, "bold"),
                command=lambda idx=i: self._radio_remove_favourite(idx)
            ).pack(side="right")

    def _radio_save_favourite(self):
        """Prompt for a name and save the current URL as a favourite station"""
        url = self._radio_url_entry.get().strip()
        if not url:
            return
        dialog = ctk.CTkInputDialog(text="Name this station:", title="Save Station")
        name = dialog.get_input()
        if name and name.strip():
            self._radio_favourites.append({'name': name.strip(), 'url': url})
            self._save_config({'radio_favourites': self._radio_favourites})
            self._radio_refresh_favourites()

    def _radio_remove_favourite(self, idx):
        """Remove a saved station by list index"""
        if 0 <= idx < len(self._radio_favourites):
            self._radio_favourites.pop(idx)
            self._save_config({'radio_favourites': self._radio_favourites})
            self._radio_refresh_favourites()

    def _toggle_search(self):
        """Show or hide the search bar"""
        if self._search_frame.winfo_ismapped():
            self._search_frame.pack_forget()
            self._search_btn.configure(fg_color=self.win95_light_gray, text_color="black")
            self._search_text = ''
            self._search_entry.delete(0, 'end')
            self.populate_tracklist()
        else:
            self._search_frame.pack(fill="x", pady=(0, 2), before=self._sort_bar)
            self._search_btn.configure(fg_color="#000080", text_color="white")
            self._search_entry.focus()

    def _on_search_change(self, event=None):
        self._search_text = self._search_entry.get().strip().lower()
        self.populate_tracklist()

    def _get_cached_meta(self, file_path):
        if file_path not in self._meta_cache:
            self._meta_cache[file_path] = self.audio_player.get_metadata(file_path)
        return self._meta_cache[file_path]

    def _set_sort_mode(self, mode):
        self.sort_mode = mode
        for m, btn in self._sort_buttons.items():
            if m == mode:
                btn.configure(fg_color="#000080", text_color="white")
            else:
                btn.configure(fg_color=self.win95_light_gray, text_color="black")
        self.populate_tracklist()

    def populate_tracklist(self):
        """Dispatch to folder tree or metadata grouping based on sort_mode"""
        for widget in self.tracklist_frame.winfo_children():
            widget.destroy()
        self.track_frames = []

        if self.sort_mode == 'folder':
            self._populate_by_folder()
        else:
            self._populate_by_metadata(self.sort_mode)

    def _build_group_section(self, parent, group_key, label_text, icon,
                             tracks_with_idx, t_num_offset=0):
        """Render one collapsible group header + track rows. Returns tracks_container."""
        # Apply search filter
        if self._search_text:
            tracks_with_idx = [
                (pi, fp) for pi, fp in tracks_with_idx
                if self._search_text in os.path.splitext(os.path.basename(fp))[0].lower()
                or self._search_text in self._get_cached_meta(fp).get('artist', '').lower()
                or self._search_text in self._get_cached_meta(fp).get('album', '').lower()
            ]
            if not tracks_with_idx:
                return None  # Skip entire group if no matches

        header_bg = "#909090"
        is_expanded = self.folder_states.get(group_key, True) if not self._search_text else True

        header = ctk.CTkFrame(parent, fg_color=header_bg, corner_radius=0)
        header.pack(fill="x", pady=(3, 0))

        chevron = ctk.CTkLabel(header, text="▼" if is_expanded else "▶",
                               text_color="black", font=("Arial", 10, "bold"),
                               fg_color=header_bg, width=18)
        chevron.pack(side="left", padx=(6, 0))

        ctk.CTkLabel(header, text=f"{icon}  {label_text}",
                     text_color="black", font=("Arial", 10, "bold"),
                     fg_color=header_bg, anchor="w").pack(side="left", padx=4, fill="x", expand=True)

        ctk.CTkLabel(header, text=f"{len(tracks_with_idx)} tracks",
                     text_color="#303030", font=("Arial", 9),
                     fg_color=header_bg, width=58, anchor="e").pack(side="right", padx=5)

        tracks_container = ctk.CTkFrame(parent, fg_color=self.tracklist_bg, corner_radius=0)

        for t_idx, (pi, file_path) in enumerate(tracks_with_idx):
            track_name = os.path.splitext(os.path.basename(file_path))[0]
            duration_str = self.audio_player.format_time(
                self.audio_player.get_file_duration(file_path))

            row = ctk.CTkFrame(tracks_container, fg_color=self.tracklist_bg, corner_radius=0)
            row.pack(fill="x", pady=1)

            num_lbl  = ctk.CTkLabel(row, text=f"{t_num_offset + t_idx + 1:02d}.",
                                    text_color="black", font=("Arial", 10), width=32, anchor="w")
            name_lbl = ctk.CTkLabel(row, text=track_name,
                                    text_color="black", font=("Arial", 10), anchor="w")
            dur_lbl  = ctk.CTkLabel(row, text=duration_str,
                                    text_color="black", font=("Arial", 10), width=50, anchor="e")

            num_lbl.pack(side="left", padx=(18, 0))
            name_lbl.pack(side="left", fill="x", expand=True, padx=4)
            dur_lbl.pack(side="right", padx=5)

            self.track_frames.append((row, [num_lbl, name_lbl, dur_lbl], pi))

            for w in [row, num_lbl, name_lbl, dur_lbl]:
                w.bind("<Button-1>", lambda e, i=pi: self.play_track_from_list(i))

        if is_expanded:
            tracks_container.pack(fill="x")

        gk, tc, ch = group_key, tracks_container, chevron
        for w in header.winfo_children() + [header]:
            w.bind("<Button-1>", lambda e, k=gk, c=tc, v=ch: self._toggle_folder(k, c, v))

        return tracks_container

    def _populate_by_folder(self):
        playlist_idx = 0
        for f_idx, folder in enumerate(self.audio_player.folders):
            tracks_with_idx = [(playlist_idx + i, p)
                               for i, p in enumerate(folder['tracks'])]
            self._build_group_section(self.tracklist_frame, f_idx,
                                      folder['name'], "📁", tracks_with_idx)
            playlist_idx += len(folder['tracks'])

    def _populate_by_metadata(self, field):
        field_labels = {'artist': ('👤', 'Unknown Artist'),
                        'album':  ('💿', 'Unknown Album'),
                        'genre':  ('🎵', 'Unknown Genre')}
        icon, unknown = field_labels.get(field, ('📁', 'Unknown'))

        groups = {}
        for idx, file_path in enumerate(self.audio_player.playlist):
            key = self._get_cached_meta(file_path).get(field, '').strip() or unknown
            groups.setdefault(key, []).append((idx, file_path))

        t_offset = 0
        for group_name in sorted(groups.keys(), key=lambda s: s.lower()):
            group_key = f"{field}_{group_name}"
            self._build_group_section(self.tracklist_frame, group_key,
                                      group_name, icon, groups[group_name],
                                      t_num_offset=t_offset)
            t_offset += len(groups[group_name])

    def _toggle_folder(self, folder_idx, tracks_container, chevron):
        """Expand or collapse a folder in the tree"""
        expanded = self.folder_states.get(folder_idx, True)
        if expanded:
            tracks_container.pack_forget()
            chevron.configure(text="▶")
            self.folder_states[folder_idx] = False
        else:
            # Re-pack by rebuilding so order is preserved across multiple folders
            self.folder_states[folder_idx] = True
            self.populate_tracklist()

    def highlight_track(self, index):
        """Highlight the active track row by playlist index, reset all others"""
        for (frame, labels, pi) in self.track_frames:
            if pi == index:
                frame.configure(fg_color="#000080")
                for label in labels:
                    label.configure(fg_color="#000080", text_color="white")
            else:
                frame.configure(fg_color=self.tracklist_bg)
                for label in labels:
                    label.configure(fg_color=self.tracklist_bg, text_color="black")
    
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
                self.highlight_track(self.audio_player.current_track_index)

            # Update metadata and album art
            self.update_metadata_display()
            self.update_album_art()
    
    def update_metadata_display(self):
        """Update artist / album / year labels from file tags"""
        if not self.audio_player.current_file:
            self.artist_display.configure(text="")
            self.album_display.configure(text="")
            return

        meta = self.audio_player.get_metadata(self.audio_player.current_file)

        artist = meta['artist'] or 'Unknown Artist'
        self.artist_display.configure(text=f"\u266a {artist[:34]}")

        album = meta['album']
        year = meta['year']
        if album and year:
            album_text = f"{album[:24]}  ({year})"
        elif album:
            album_text = album[:34]
        elif year:
            album_text = year
        else:
            album_text = ''
        self.album_display.configure(text=f"  {album_text}")

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
        if self._radio_playing:
            self.window.after(100, self.update_time_display)
            return
        if self.audio_player.current_file:
            current_time = self.audio_player.get_position()
            total_time = self.audio_player.get_duration()

            current_str = self.audio_player.format_time(current_time)
            total_str = self.audio_player.format_time(total_time)

            self.time_display.configure(text=f"{current_str} / {total_str}")

            # Advance seek bar only when user is not dragging
            if not self.seeking:
                progress = (current_time / total_time * 100) if total_time > 0 else 0
                self.seek_slider.set(progress)

            # Auto-play next track when current ends
            if self.audio_player.is_playing and current_time >= total_time and total_time > 0:
                if self.audio_player.play_next():
                    self.update_current_track_display()
                else:
                    self.stop_music()
        else:
            self.time_display.configure(text="0:00 / 0:00")
            if not self.seeking:
                self.seek_slider.set(0)
        
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
        if self._radio_playing:
            self._stop_radio()
            return
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
    
    def _seek_start(self, _event):
        """User started dragging the seek bar"""
        self.seeking = True

    def _on_seek_drag(self, value):
        """Called on every slider movement — store pending value"""
        self._seek_pending = float(value)

    def _seek_end(self, event):
        """User released the seek bar — perform the seek"""
        total = self.audio_player.get_duration()
        if total > 0:
            target_seconds = (self._seek_pending / 100.0) * total
            self.audio_player.seek(target_seconds)
        self.seeking = False

    def change_volume(self, value):
        """Volume slider handler"""
        volume = float(value) / 100
        self.audio_player.set_volume(volume)
        self.volume_label.configure(text=f"{int(value)}%")
    
    def _parse_drop_data(self, data):
        """Parse tkinterdnd2 drop string into a list of file paths"""
        paths = []
        i = 0
        while i < len(data):
            if data[i] == '{':
                end = data.index('}', i)
                paths.append(data[i + 1:end])
                i = end + 2
            else:
                end = data.find(' ', i)
                if end == -1:
                    paths.append(data[i:])
                    break
                paths.append(data[i:end])
                i = end + 1
        return [p for p in paths if p]

    def _on_drop(self, event):
        """Handle files/folders dropped onto the window"""
        paths = self._parse_drop_data(event.data)
        supported = {'.mp3', '.m4a', '.mp4', '.aac', '.wma', '.wav', '.flac'}
        changed = False
        groups = {}  # parent folder name → [file paths]

        for path in paths:
            if os.path.isdir(path):
                if self.audio_player.add_folder(path):
                    changed = True
            elif os.path.isfile(path) and os.path.splitext(path)[1].lower() in supported:
                parent = os.path.basename(os.path.dirname(path))
                groups.setdefault(parent, []).append(path)

        for group_name, files in groups.items():
            if self.audio_player.add_files_group(group_name, files):
                changed = True

        if changed:
            self.populate_tracklist()

    def save_playlist(self):
        """Save the current playlist as an M3U file"""
        if not self.audio_player.playlist:
            return
        file_path = filedialog.asksaveasfilename(
            title="Save Playlist",
            defaultextension=".m3u",
            filetypes=[("M3U Playlist", "*.m3u"), ("All Files", "*.*")]
        )
        if file_path:
            self.audio_player.save_playlist_m3u(file_path)

    def load_playlist(self):
        """Load an M3U playlist file"""
        file_path = filedialog.askopenfilename(
            title="Load Playlist",
            filetypes=[("M3U Playlist", "*.m3u"), ("All Files", "*.*")]
        )
        if file_path:
            if self.audio_player.load_playlist_m3u(file_path):
                self.populate_tracklist()
                if self.audio_player.playlist:
                    self.audio_player.load_file(self.audio_player.playlist[0])
                    self.audio_player.current_track_index = 0
                    self.update_current_track_display()

    def _load_config(self):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_config(self, data):
        try:
            existing = self._load_config()
            existing.update(data)
            with open(CONFIG_PATH, 'w') as f:
                json.dump(existing, f, indent=2)
        except Exception as e:
            print(f"Config save error: {e}")

    def clear_all(self):
        """Reset the player to its startup state"""
        if self._radio_playing:
            self._stop_radio()
        self.audio_player.reset()

        # Clear track list
        for widget in self.tracklist_frame.winfo_children():
            widget.destroy()
        self.track_frames = []

        # Reset LCD and displays
        self.song_display.configure(text="No file loaded")
        self.track_num.configure(text="1")
        self.time_display.configure(text="0:00 / 0:00")
        self.artist_display.configure(text="")
        self.album_display.configure(text="")

        # Reset seek bar and volume label
        self.seek_slider.set(0)

        # Reset album art
        self._pending_art_image = None
        self.current_album_art = None
        self.album_art_label.configure(image=None, text="No Album Art")

        # Reset shuffle and repeat buttons
        self.shuffle_btn.configure(fg_color=self.win95_light_gray, text_color="black", text="🔀")
        self.repeat_btn.configure(fg_color=self.win95_light_gray, text_color="black", text="🔁 Off")

        # Reset search
        self._search_text = ''
        if self._search_entry:
            self._search_entry.delete(0, 'end')
        if self._search_frame and self._search_frame.winfo_ismapped():
            self._search_frame.pack_forget()
            self._search_btn.configure(fg_color=self.win95_light_gray, text_color="black")

        # Reset folder tree and sort state
        self.folder_states = {}
        self._meta_cache = {}
        self.sort_mode = 'folder'
        if self._sort_buttons:
            for m, btn in self._sort_buttons.items():
                btn.configure(fg_color="#000080" if m == 'folder' else self.win95_light_gray,
                              text_color="white" if m == 'folder' else "black")

    # ------------------------------------------------------------------ #
    #  File menu                                                          #
    # ------------------------------------------------------------------ #

    def _show_file_menu(self, event):
        """Show the File dropdown menu"""
        menu = tk.Menu(self.window, tearoff=0, font=("Arial", 10))
        menu.add_command(label="Open File...",   command=self._open_single_file)
        menu.add_command(label="Open Folder...", command=self.load_folder)
        menu.add_command(label="Clear All",      command=self.clear_all)
        menu.add_separator()
        menu.add_command(label="Load Album Art from File...", command=self._art_load_from_file)
        menu.add_command(label="Find Album Art Online",       command=self._art_find_online)
        can_save = self._pending_art_image is not None and self.audio_player.current_file is not None
        menu.add_command(label="Save Art to Tags", command=self._art_save_to_tags,
                         state="normal" if can_save else "disabled")
        menu.add_command(label="Clear Art", command=self._art_clear)
        menu.add_separator()
        menu.add_command(label="Save Playlist", command=self.save_playlist)
        menu.add_command(label="Load Playlist", command=self.load_playlist)
        menu.add_separator()
        menu.add_command(label="Exit", command=self.window.quit)
        menu.tk_popup(event.x_root, event.y_root)

    def _open_single_file(self):
        """Open one or more individual audio files"""
        paths = filedialog.askopenfilenames(
            title="Open Audio File",
            filetypes=[("Audio Files", "*.mp3 *.m4a *.aac *.wma *.wav *.flac"),
                       ("All Files", "*.*")]
        )
        if paths:
            self.audio_player.add_files_to_playlist(list(paths))
            self.populate_tracklist()
            # If nothing was playing, load the first new file
            if self.audio_player.current_track_index < 0:
                self.audio_player.load_file(self.audio_player.playlist[0])
                self.audio_player.current_track_index = 0
                self.update_current_track_display()

    # ------------------------------------------------------------------ #
    #  Album art                                                          #
    # ------------------------------------------------------------------ #

    def _art_load_from_file(self):
        """Load album art from a local image file"""
        path = filedialog.askopenfilename(
            title="Select Album Art",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp *.webp"),
                       ("All Files", "*.*")]
        )
        if path:
            try:
                img = Image.open(path)
                self._pending_art_image = img.copy()
                self._display_art(img)
            except Exception as e:
                print(f"Error loading image: {e}")

    def _art_find_online(self):
        """Fetch album art from the iTunes API using current track metadata"""
        if not self.audio_player.current_file:
            return
        meta = self.audio_player.get_metadata(self.audio_player.current_file)
        title = os.path.splitext(self.audio_player.get_current_filename())[0]
        self.song_display.configure(text="Searching for art...")
        self.window.update()
        img = self.audio_player.fetch_album_art_online(
            artist=meta.get('artist', ''),
            album=meta.get('album', ''),
            title=title
        )
        filename = self.audio_player.get_current_filename() or ''
        if len(filename) > 35:
            filename = filename[:32] + '...'
        if img:
            self._pending_art_image = img.copy()
            self._display_art(img)
            self.song_display.configure(text=f"Art found — use File > Save Art to Tags")
        else:
            self.song_display.configure(text="No art found online")

    def _display_art(self, img):
        """Resize and display a PIL image in the album art area"""
        img.thumbnail((280, 280), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self.current_album_art = photo
        self.album_art_label.configure(image=photo, text="")

    def _art_save_to_tags(self):
        """Embed the pending art image into the current track's tags"""
        if not self._pending_art_image or not self.audio_player.current_file:
            return
        buf = io.BytesIO()
        self._pending_art_image.convert('RGB').save(buf, format='JPEG', quality=90)
        if self.audio_player.embed_album_art(self.audio_player.current_file, buf.getvalue()):
            self._pending_art_image = None
            self.song_display.configure(text="Art saved to tags")

    def _art_clear(self):
        """Clear the displayed album art"""
        self._pending_art_image = None
        self.current_album_art = None
        self.album_art_label.configure(image=None, text="No Album Art")

    def toggle_shuffle(self):
        """Toggle shuffle mode and update button appearance"""
        active = self.audio_player.toggle_shuffle()
        if active:
            self.shuffle_btn.configure(fg_color="#000080", text_color="white", text="🔀 On")
        else:
            self.shuffle_btn.configure(fg_color=self.win95_light_gray, text_color="black", text="🔀")

    def cycle_repeat(self):
        """Cycle repeat mode and update button appearance"""
        mode = self.audio_player.cycle_repeat()
        labels = {0: ("🔁 Off", self.win95_light_gray, "black"),
                  1: ("🔁 All", "#000080", "white"),
                  2: ("🔂 One", "#000080", "white")}
        text, color, tcolor = labels[mode]
        self.repeat_btn.configure(text=text, fg_color=color, text_color=tcolor)

    def _bind_keyboard_shortcuts(self):
        """Bind keyboard shortcuts to the main window"""
        self.window.bind("<space>", lambda e: self._kb_play_pause())
        self.window.bind("<s>", lambda e: self.stop_music())
        self.window.bind("<Escape>", lambda e: self.stop_music())
        self.window.bind("<Left>", lambda e: self.previous_track())
        self.window.bind("<Right>", lambda e: self.next_track())
        self.window.bind("<Up>", lambda e: self._kb_volume_up())
        self.window.bind("<Down>", lambda e: self._kb_volume_down())

    def _kb_play_pause(self):
        """Toggle between play and pause"""
        if self.audio_player.is_playing:
            self.pause_music()
        else:
            self.play_music()

    def _kb_volume_up(self):
        """Increase volume by 5%"""
        new_val = min(100, self.volume_slider.get() + 5)
        self.volume_slider.set(new_val)
        self.change_volume(new_val)

    def _kb_volume_down(self):
        """Decrease volume by 5%"""
        new_val = max(0, self.volume_slider.get() - 5)
        self.volume_slider.set(new_val)
        self.change_volume(new_val)

    def run(self):
        """Start the application"""
        self.window.mainloop()