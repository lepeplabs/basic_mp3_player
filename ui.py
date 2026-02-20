"""
ui.py
User interface for the MP3 player using PySide6
lepeplabs_audio_thing / Windows 95 retro style with track list and album art
"""

import os
import io
import json
import threading

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QSlider, QLineEdit,
    QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QFileDialog, QInputDialog, QSizePolicy, QApplication,
)
from PySide6.QtGui import (
    QAction, QPixmap, QImage, QPainter, QColor, QFont,
    QKeySequence, QShortcut,
)
from PySide6.QtCore import Qt, QTimer

from PIL import Image

CONFIG_PATH = os.path.expanduser("~/.lepeplabs_player.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pil_to_qpixmap(img: Image.Image) -> QPixmap:
    """Convert a PIL Image to QPixmap via PNG bytes."""
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    qimg = QImage()
    qimg.loadFromData(buf.read())
    return QPixmap.fromImage(qimg)


def _lcd_label(parent, text, font_size=10, bold=True) -> QLabel:
    """Create a green-on-black monospaced label for the LCD area."""
    lbl = QLabel(text, parent)
    weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
    lbl.setFont(QFont("Courier", font_size, weight))
    lbl.setStyleSheet("color: #00FF00; background: #000000;")
    return lbl


def _win95_btn(text, parent=None, width=50, height=35, font_size=14) -> QPushButton:
    """Create a Win95-style push button."""
    btn = QPushButton(text, parent)
    btn.setFixedSize(width, height)
    btn.setFont(QFont("Arial", font_size, QFont.Weight.Bold))
    return btn


# ---------------------------------------------------------------------------
# Visualizer widget
# ---------------------------------------------------------------------------

class VisualizerWidget(QWidget):
    """Real-time amplitude bar visualizer drawn with QPainter."""

    _VIZ_BARS  = 30
    _VIZ_DECAY = 0.80
    _CLR_BG    = QColor("#000000")
    _CLR_BAR   = QColor("#006600")
    _CLR_PEAK  = QColor("#00FF00")
    _CLR_IDLE  = QColor("#002200")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self._bars: list[float] = []
        self._peaks: list[float] = []
        self._decoding = False

    def update_viz(self, bars: list[float], peaks: list[float]):
        self._bars = bars
        self._peaks = peaks
        self.update()

    def set_decoding(self, state: bool):
        self._decoding = state
        if not state:
            self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        w = self.width()
        h = self.height()

        painter.fillRect(0, 0, w, h, self._CLR_BG)

        if not self._bars:
            mid = h // 2
            painter.setPen(self._CLR_IDLE)
            painter.drawLine(0, mid, w, mid)
            if self._decoding:
                painter.setFont(QFont("Courier", 7))
                painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "decoding…")
            return

        N = len(self._bars)
        bar_w = max(1, (w - N) // N)
        step   = bar_w + 1
        offset = (w - N * step) // 2
        max_h  = h - 2

        for i, (amp, pk) in enumerate(zip(self._bars, self._peaks)):
            x0 = offset + i * step
            x1 = x0 + bar_w
            bh = max(1, int(amp * max_h))
            ph = max(1, int(pk  * max_h))
            painter.fillRect(x0, h - bh, bar_w, bh, self._CLR_BAR)
            painter.setPen(self._CLR_PEAK)
            painter.drawLine(x0, h - ph - 1, x1, h - ph - 1)


# ---------------------------------------------------------------------------
# Track row helper — stores playlist index for click handling
# ---------------------------------------------------------------------------

class _TrackRow(QWidget):
    def __init__(self, playlist_idx: int, num: str, name: str, duration: str,
                 on_click, bg: str, parent=None):
        super().__init__(parent)
        self._playlist_idx = playlist_idx
        self._on_click = on_click
        self._bg_normal = bg
        self._active = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(0)

        self._num_lbl  = QLabel(num)
        self._name_lbl = QLabel(name)
        self._dur_lbl  = QLabel(duration)

        for lbl in (self._num_lbl, self._name_lbl, self._dur_lbl):
            lbl.setFont(QFont("Arial", 10))

        self._num_lbl.setFixedWidth(34)
        self._num_lbl.setContentsMargins(18, 0, 0, 0)
        self._dur_lbl.setFixedWidth(52)
        self._dur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._dur_lbl.setContentsMargins(0, 0, 5, 0)
        self._name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout.addWidget(self._num_lbl)
        layout.addWidget(self._name_lbl)
        layout.addWidget(self._dur_lbl)

        self._apply_colors(False)

    def _apply_colors(self, active: bool):
        bg = "#000080" if active else self._bg_normal
        fg = "white"   if active else "black"
        for lbl in (self._num_lbl, self._name_lbl, self._dur_lbl, self):
            lbl.setStyleSheet(f"background: {bg}; color: {fg};")

    def set_active(self, active: bool):
        if self._active != active:
            self._active = active
            self._apply_colors(active)

    def mousePressEvent(self, _event):
        self._on_click(self._playlist_idx)


# ---------------------------------------------------------------------------
# Main UI class
# ---------------------------------------------------------------------------

class PlayerUI(QMainWindow):
    """PySide6 player UI with Win95 retro styling."""

    _VIZ_BARS  = VisualizerWidget._VIZ_BARS
    _VIZ_DECAY = VisualizerWidget._VIZ_DECAY

    # Win95 palette
    WIN95_GRAY       = "#C0C0C0"
    WIN95_DARK_GRAY  = "#808080"
    WIN95_LIGHT_GRAY = "#DFDFDF"
    LCD_GREEN        = "#00FF00"
    LCD_BG           = "#000000"
    TRACKLIST_BG     = "#A8A8A8"
    ACTIVE_BLUE      = "#000080"

    def __init__(self, audio_player):
        super().__init__()
        self.audio_player = audio_player
        self.default_music_folder = self._load_config().get('last_folder')

        self.setWindowTitle("lepeplabs_audio_thing")
        self.setFixedSize(780, 720)

        # State
        self.seeking            = False
        self._seek_pending      = 0.0
        self._pending_art_image = None
        self.current_album_art  = None
        self.folder_states: dict = {}
        self.sort_mode          = 'folder'
        self._meta_cache: dict  = {}
        self._sort_buttons: dict = {}
        self._search_text       = ''
        self._track_rows: list[_TrackRow] = []

        # Radio state
        self._radio_playing      = False
        self._radio_favourites   = self._load_config().get('radio_favourites', [])
        self._radio_frame        = None
        self._radio_url_entry    = None
        self._radio_play_btn     = None
        self._radio_favs_inner   = None

        # Search state
        self._search_frame  = None
        self._search_entry  = None
        self._search_btn    = None

        # Visualizer state
        self._viz_widget:  VisualizerWidget | None = None
        self._viz_peaks:   list[float] = []
        self._viz_decoding = False

        # Right panel layout reference (for dynamic panel insertion)
        self._right_layout: QVBoxLayout | None = None
        self._sort_bar_idx = 2  # default index of sort_bar in right_layout

        # Apply Win95 stylesheet
        self._apply_win95_stylesheet()

        # Build menu bar
        self._build_menu_bar()

        # Build central widget
        central = QWidget()
        self.setCentralWidget(central)
        self.create_widgets(central)

        # Keyboard shortcuts
        self._bind_keyboard_shortcuts()

        # Native drag-and-drop
        self.setAcceptDrops(True)

        # Auto-load last folder
        if self.default_music_folder and os.path.exists(self.default_music_folder):
            if self.audio_player.add_folder(self.default_music_folder):
                self.populate_tracklist()

        # 100ms update timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_tick)
        self._timer.start(100)

    # ------------------------------------------------------------------
    # Stylesheet
    # ------------------------------------------------------------------

    def _apply_win95_stylesheet(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {self.WIN95_GRAY};
                color: black;
                font-family: Arial;
            }}
            QPushButton {{
                background: {self.WIN95_LIGHT_GRAY};
                border: 2px solid {self.WIN95_DARK_GRAY};
                border-radius: 3px;
                color: black;
            }}
            QPushButton:hover  {{ background: {self.WIN95_GRAY}; }}
            QPushButton:pressed {{ border-style: inset; background: #B0B0B0; }}
            QPushButton[active="true"] {{
                background: {self.ACTIVE_BLUE};
                color: white;
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                background: {self.WIN95_DARK_GRAY};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                width: 14px;
                height: 18px;
                background: {self.WIN95_DARK_GRAY};
                border: 1px solid #404040;
                margin: -6px 0;
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{ background: {self.LCD_GREEN}; border-radius: 2px; }}
            QLineEdit {{
                background: white;
                color: black;
                border: 1px solid {self.WIN95_DARK_GRAY};
                font-size: 9pt;
                padding: 1px 3px;
            }}
            QScrollArea  {{ border: 2px solid {self.WIN95_DARK_GRAY}; background: {self.TRACKLIST_BG}; }}
            QScrollBar:vertical {{ background: {self.WIN95_GRAY}; width: 14px; }}
            QScrollBar::handle:vertical {{ background: {self.WIN95_DARK_GRAY}; min-height: 20px; }}
            QMenuBar  {{ background: {self.WIN95_GRAY}; color: black; }}
            QMenuBar::item:selected {{ background: {self.ACTIVE_BLUE}; color: white; }}
            QMenu {{
                background: {self.WIN95_GRAY};
                color: black;
                border: 1px solid {self.WIN95_DARK_GRAY};
            }}
            QMenu::item:selected {{ background: {self.ACTIVE_BLUE}; color: white; }}
        """)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu_bar(self):
        bar = self.menuBar()

        file_menu = bar.addMenu("File")
        file_menu.addAction("Open File...",    self._open_single_file)
        file_menu.addAction("Open Folder...", self.load_folder)
        file_menu.addAction("Clear All",      self.clear_all)
        file_menu.addSeparator()
        file_menu.addAction("Load Album Art from File...", self._art_load_from_file)
        file_menu.addAction("Find Album Art Online",       self._art_find_online)
        self._art_save_action = QAction("Save Art to Tags", self)
        self._art_save_action.triggered.connect(self._art_save_to_tags)
        self._art_save_action.setEnabled(False)
        file_menu.addAction(self._art_save_action)
        file_menu.addAction("Clear Art", self._art_clear)
        file_menu.addSeparator()
        file_menu.addAction("Save Playlist", self.save_playlist)
        file_menu.addAction("Load Playlist", self.load_playlist)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        bar.addMenu("Options")
        bar.addMenu("Help")

    # ------------------------------------------------------------------
    # Widget construction
    # ------------------------------------------------------------------

    def create_widgets(self, parent: QWidget):
        main_layout = QVBoxLayout(parent)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)
        main_layout.addWidget(content)

        left_frame = self._build_left_panel()
        left_frame.setFixedWidth(350)
        content_layout.addWidget(left_frame)

        right_frame = self._build_right_panel()
        content_layout.addWidget(right_frame, stretch=1)

    # ------------------------------------------------------------------
    # Left panel
    # ------------------------------------------------------------------

    def _build_left_panel(self) -> QWidget:
        frame = QWidget()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Album art
        art_frame = QFrame()
        art_frame.setFixedHeight(265)
        art_frame.setStyleSheet(f"background: {self.LCD_BG}; border: 2px solid {self.WIN95_DARK_GRAY};")
        art_inner = QVBoxLayout(art_frame)
        art_inner.setContentsMargins(0, 0, 0, 0)

        self.album_art_label = QLabel("No Album Art")
        self.album_art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.album_art_label.setFont(QFont("Courier", 12, QFont.Weight.Bold))
        self.album_art_label.setStyleSheet(f"color: {self.LCD_GREEN}; background: {self.LCD_BG};")
        art_inner.addWidget(self.album_art_label)
        layout.addWidget(art_frame)

        # LCD display
        lcd_frame = QFrame()
        lcd_frame.setFixedHeight(90)
        lcd_frame.setStyleSheet(f"background: {self.LCD_BG}; border: 2px solid {self.WIN95_DARK_GRAY};")
        lcd_layout = QVBoxLayout(lcd_frame)
        lcd_layout.setContentsMargins(5, 5, 5, 5)
        lcd_layout.setSpacing(2)

        top_row_w = QWidget()
        top_row_w.setStyleSheet(f"background: {self.LCD_BG};")
        top_row = QHBoxLayout(top_row_w)
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(4)

        top_row.addWidget(_lcd_label(None, "TRACK", 10))
        self.track_num = _lcd_label(None, "1", 16)
        top_row.addWidget(self.track_num)

        time_block = QWidget()
        time_block.setStyleSheet(f"background: {self.LCD_BG};")
        time_blk_lay = QVBoxLayout(time_block)
        time_blk_lay.setContentsMargins(20, 0, 0, 0)
        time_blk_lay.setSpacing(0)

        min_sec_row = QWidget()
        min_sec_row.setStyleSheet(f"background: {self.LCD_BG};")
        msr = QHBoxLayout(min_sec_row)
        msr.setContentsMargins(0, 0, 0, 0)
        msr.setSpacing(4)
        msr.addWidget(_lcd_label(None, "MIN", 10))
        msr.addWidget(_lcd_label(None, "SEC", 10))
        time_blk_lay.addWidget(min_sec_row)

        self.time_display = _lcd_label(None, "0:00 / 0:00", 16)
        time_blk_lay.addWidget(self.time_display)
        top_row.addWidget(time_block)

        top_row.addStretch()
        top_row.addWidget(_lcd_label(None, "MODE", 10))
        lcd_layout.addWidget(top_row_w)

        self.song_display = QLabel("No file loaded")
        self.song_display.setFont(QFont("Courier", 11, QFont.Weight.Bold))
        self.song_display.setStyleSheet(f"color: {self.LCD_GREEN}; background: {self.LCD_BG};")
        self.song_display.setContentsMargins(10, 5, 10, 8)
        lcd_layout.addWidget(self.song_display)
        layout.addWidget(lcd_frame)

        # Metadata display
        meta_frame = QFrame()
        meta_frame.setFixedHeight(48)
        meta_frame.setStyleSheet(f"background: {self.LCD_BG}; border: 2px solid {self.WIN95_DARK_GRAY};")
        meta_layout = QVBoxLayout(meta_frame)
        meta_layout.setContentsMargins(10, 4, 10, 4)
        meta_layout.setSpacing(0)

        self.artist_display = QLabel("")
        self.artist_display.setFont(QFont("Courier", 10, QFont.Weight.Bold))
        self.artist_display.setStyleSheet(f"color: {self.LCD_GREEN}; background: {self.LCD_BG};")
        meta_layout.addWidget(self.artist_display)

        self.album_display = QLabel("")
        self.album_display.setFont(QFont("Courier", 10, QFont.Weight.Bold))
        self.album_display.setStyleSheet(f"color: {self.LCD_GREEN}; background: {self.LCD_BG};")
        meta_layout.addWidget(self.album_display)
        layout.addWidget(meta_frame)

        # Transport controls
        controls_w = QWidget()
        controls_grid = QGridLayout(controls_w)
        controls_grid.setContentsMargins(0, 10, 0, 0)
        controls_grid.setSpacing(3)

        btn_cfg = dict(width=50, height=35, font_size=14)
        self.play_btn  = _win95_btn("▶",  **btn_cfg)
        self.stop_btn  = _win95_btn("■",  **btn_cfg)
        self.pause_btn = _win95_btn("II", **btn_cfg)
        self.prev_btn  = _win95_btn("⏮", **btn_cfg)
        self.next_btn  = _win95_btn("⏭", **btn_cfg)
        self.folder_btn = _win95_btn("📁", width=50, height=35, font_size=12)

        self.play_btn.clicked.connect(self.play_music)
        self.stop_btn.clicked.connect(self.stop_music)
        self.pause_btn.clicked.connect(self.pause_music)
        self.prev_btn.clicked.connect(self.previous_track)
        self.next_btn.clicked.connect(self.next_track)
        self.folder_btn.clicked.connect(self.load_folder)

        for col, btn in enumerate([self.play_btn, self.stop_btn, self.pause_btn,
                                    self.prev_btn, self.next_btn, self.folder_btn]):
            controls_grid.addWidget(btn, 0, col)

        self.shuffle_btn = QPushButton("🔀")
        self.shuffle_btn.setFixedSize(80, 28)
        self.shuffle_btn.setFont(QFont("Arial", 11))
        self.shuffle_btn.clicked.connect(self.toggle_shuffle)
        controls_grid.addWidget(self.shuffle_btn, 1, 0, 1, 3)

        self.repeat_btn = QPushButton("🔁 Off")
        self.repeat_btn.setFixedSize(110, 28)
        self.repeat_btn.setFont(QFont("Arial", 11))
        self.repeat_btn.clicked.connect(self.cycle_repeat)
        controls_grid.addWidget(self.repeat_btn, 1, 3, 1, 3)

        clear_btn = QPushButton("🗑 Clear All")
        clear_btn.setFixedHeight(24)
        clear_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        clear_btn.setStyleSheet(f"""
            QPushButton {{ background: {self.WIN95_LIGHT_GRAY}; border: 2px solid {self.WIN95_DARK_GRAY}; }}
            QPushButton:hover {{ background: #CC4444; color: white; }}
        """)
        clear_btn.clicked.connect(self.clear_all)
        controls_grid.addWidget(clear_btn, 2, 0, 1, 6)

        layout.addWidget(controls_w, 0, Qt.AlignmentFlag.AlignHCenter)

        # Seek bar
        seek_w = QWidget()
        seek_lay = QHBoxLayout(seek_w)
        seek_lay.setContentsMargins(10, 0, 10, 5)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 100)
        self.seek_slider.sliderPressed.connect(self._seek_start)
        self.seek_slider.sliderReleased.connect(self._seek_end)
        self.seek_slider.valueChanged.connect(self._on_seek_drag)
        seek_lay.addWidget(self.seek_slider)
        layout.addWidget(seek_w)

        # Visualizer
        viz_frame = QFrame()
        viz_frame.setFixedHeight(64)
        viz_frame.setStyleSheet(f"background: {self.LCD_BG}; border: 2px solid {self.WIN95_DARK_GRAY};")
        viz_inner = QVBoxLayout(viz_frame)
        viz_inner.setContentsMargins(1, 1, 1, 1)

        self._viz_widget = VisualizerWidget()
        viz_inner.addWidget(self._viz_widget)
        layout.addWidget(viz_frame)

        # Volume
        vol_w = QWidget()
        vol_lay = QHBoxLayout(vol_w)
        vol_lay.setContentsMargins(0, 5, 0, 5)

        vol_label = QLabel("VOL")
        vol_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        vol_lay.addWidget(vol_label)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setFixedWidth(200)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.valueChanged.connect(self.change_volume)
        vol_lay.addWidget(self.volume_slider)

        self.volume_label = QLabel("70%")
        self.volume_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.volume_label.setFixedWidth(40)
        vol_lay.addWidget(self.volume_label)

        layout.addWidget(vol_w, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

        return frame

    # ------------------------------------------------------------------
    # Right panel
    # ------------------------------------------------------------------

    def _build_right_panel(self) -> QWidget:
        frame = QWidget()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._right_layout = layout

        # Header row
        header_row = QWidget()
        header_lay = QHBoxLayout(header_row)
        header_lay.setContentsMargins(0, 0, 0, 5)

        tl_label = QLabel("TRACK LIST")
        tl_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header_lay.addWidget(tl_label)
        header_lay.addStretch()

        pl_btn_style = (
            f"QPushButton {{ width: 60px; height: 22px; font-size: 9pt; font-weight: bold; }}"
        )

        def _pl_btn(text, slot, width=60):
            b = QPushButton(text)
            b.setFixedSize(width, 22)
            b.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            b.clicked.connect(slot)
            return b

        self._search_btn = _pl_btn("🔍", self._toggle_search, 32)
        header_lay.addWidget(self._search_btn)

        header_lay.addWidget(_pl_btn("📂 Load", self.load_playlist))

        self._radio_btn = _pl_btn("📻", self._toggle_radio, 32)
        header_lay.addWidget(self._radio_btn)

        header_lay.addWidget(_pl_btn("💾 Save", self.save_playlist))

        layout.addWidget(header_row)  # idx 0

        # Radio panel — parented to frame but NOT added to layout yet (inserted on demand)
        self._radio_frame = self._build_radio_panel()
        self._radio_frame.setParent(frame)
        self._radio_frame.hide()

        # Search bar — same pattern
        self._search_frame = QWidget(frame)
        search_inner = QHBoxLayout(self._search_frame)
        search_inner.setContentsMargins(4, 2, 4, 2)
        self._search_entry = QLineEdit()
        self._search_entry.setPlaceholderText("Search tracks...")
        self._search_entry.setFixedHeight(24)
        self._search_entry.textChanged.connect(self._on_search_change)
        search_inner.addWidget(self._search_entry)
        self._search_frame.hide()

        # Sort bar
        sort_bar = QWidget()
        sort_lay = QHBoxLayout(sort_bar)
        sort_lay.setContentsMargins(2, 0, 2, 4)
        sort_lay.setSpacing(4)

        sort_lbl = QLabel("Group by:")
        sort_lbl.setFont(QFont("Arial", 9))
        sort_lay.addWidget(sort_lbl)

        for mode, label in [("folder", "📁 Folder"), ("artist", "👤 Artist"),
                             ("album",  "💿 Album"),  ("genre",  "🎵 Genre")]:
            btn = QPushButton(label)
            btn.setFixedSize(68, 20)
            btn.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            if mode == 'folder':
                btn.setStyleSheet(f"background: {self.ACTIVE_BLUE}; color: white; border: 1px solid {self.WIN95_DARK_GRAY};")
            else:
                btn.setStyleSheet(f"background: {self.WIN95_LIGHT_GRAY}; color: black; border: 1px solid {self.WIN95_DARK_GRAY};")
            btn.clicked.connect(lambda checked=False, m=mode: self._set_sort_mode(m))
            sort_lay.addWidget(btn)
            self._sort_buttons[mode] = btn

        sort_lay.addStretch()
        layout.addWidget(sort_bar)  # idx 1
        self._sort_bar_idx = 1      # sort_bar is at index 1 (nothing inserted above yet)

        # Scrollable track list
        self._tracklist_scroll = QScrollArea()
        self._tracklist_scroll.setWidgetResizable(True)
        self._tracklist_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._tracklist_scroll.setStyleSheet(
            f"QScrollArea {{ background: {self.TRACKLIST_BG}; border: 2px solid {self.WIN95_DARK_GRAY}; }}"
        )

        self._tracklist_inner = QWidget()
        self._tracklist_inner.setStyleSheet(f"background: {self.TRACKLIST_BG};")
        self._tracklist_layout = QVBoxLayout(self._tracklist_inner)
        self._tracklist_layout.setContentsMargins(0, 0, 0, 0)
        self._tracklist_layout.setSpacing(0)
        self._tracklist_layout.addStretch()

        self._tracklist_scroll.setWidget(self._tracklist_inner)
        layout.addWidget(self._tracklist_scroll, stretch=1)  # idx 2

        return frame

    # ------------------------------------------------------------------
    # Radio panel
    # ------------------------------------------------------------------

    def _build_radio_panel(self) -> QFrame:
        PRESETS = [
            ("BBC Radio 1",   "http://stream.live.vc.bbcmedia.co.uk/bbc_radio_one"),
            ("BBC Radio 2",   "http://stream.live.vc.bbcmedia.co.uk/bbc_radio_two"),
            ("Jazz FM",       "http://edge-bauerse03.sharp-stream.com/jazzfmuk_mp3_128"),
            ("SomaFM Groove", "http://ice2.somafm.com/groovesalad-128-mp3"),
            ("SomaFM Drone",  "http://ice2.somafm.com/dronezone-128-mp3"),
        ]

        frame = QFrame()
        frame.setStyleSheet(f"background: {self.WIN95_GRAY}; border: 1px solid {self.WIN95_DARK_GRAY};")
        flayout = QVBoxLayout(frame)
        flayout.setContentsMargins(4, 4, 4, 4)
        flayout.setSpacing(2)

        # URL entry row
        url_row = QWidget()
        url_row.setStyleSheet(f"background: {self.WIN95_GRAY};")
        url_lay = QHBoxLayout(url_row)
        url_lay.setContentsMargins(0, 0, 0, 0)
        url_lay.setSpacing(4)

        self._radio_url_entry = QLineEdit()
        self._radio_url_entry.setPlaceholderText("Stream URL...")
        self._radio_url_entry.setFixedHeight(24)
        url_lay.addWidget(self._radio_url_entry, stretch=1)

        self._radio_play_btn = QPushButton("▶ Play")
        self._radio_play_btn.setFixedSize(58, 24)
        self._radio_play_btn.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self._radio_play_btn.clicked.connect(self._radio_play_url)
        url_lay.addWidget(self._radio_play_btn)

        save_fav_btn = QPushButton("★ Save")
        save_fav_btn.setFixedSize(58, 24)
        save_fav_btn.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        save_fav_btn.setStyleSheet(
            f"QPushButton {{ background: {self.WIN95_LIGHT_GRAY}; }}"
            f"QPushButton:hover {{ background: #DAA520; }}"
        )
        save_fav_btn.clicked.connect(self._radio_save_favourite)
        url_lay.addWidget(save_fav_btn)
        flayout.addWidget(url_row)

        # Preset row
        presets_row = QWidget()
        presets_row.setStyleSheet(f"background: {self.WIN95_GRAY};")
        presets_lay = QHBoxLayout(presets_row)
        presets_lay.setContentsMargins(0, 0, 0, 0)
        presets_lay.setSpacing(2)

        for name, url in PRESETS:
            btn = QPushButton(name)
            btn.setFixedHeight(20)
            btn.setFont(QFont("Arial", 8))
            btn.setStyleSheet(
                f"QPushButton {{ background: {self.WIN95_LIGHT_GRAY}; border: 1px solid {self.WIN95_DARK_GRAY}; }}"
                f"QPushButton:hover {{ background: {self.ACTIVE_BLUE}; color: white; }}"
            )
            btn.clicked.connect(lambda checked=False, n=name, u=url: self._radio_play_preset(n, u))
            presets_lay.addWidget(btn)

        presets_lay.addStretch()
        flayout.addWidget(presets_row)

        # Saved stations header
        hdr = QLabel("── Saved Stations ──")
        hdr.setFont(QFont("Arial", 8))
        hdr.setStyleSheet(f"color: {self.WIN95_DARK_GRAY}; background: {self.WIN95_GRAY};")
        flayout.addWidget(hdr)

        # Inner container for saved stations
        self._radio_favs_inner = QWidget()
        self._radio_favs_inner.setStyleSheet(f"background: {self.WIN95_GRAY};")
        self._radio_favs_layout = QVBoxLayout(self._radio_favs_inner)
        self._radio_favs_layout.setContentsMargins(0, 0, 0, 0)
        self._radio_favs_layout.setSpacing(1)
        flayout.addWidget(self._radio_favs_inner)

        self._radio_refresh_favourites()
        return frame

    def _radio_refresh_favourites(self):
        if self._radio_favs_inner is None:
            return
        # Clear existing children
        while self._radio_favs_layout.count():
            item = self._radio_favs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._radio_favourites:
            lbl = QLabel("No saved stations — play a stream and click ★ Save")
            lbl.setFont(QFont("Arial", 8))
            lbl.setStyleSheet(f"color: {self.WIN95_DARK_GRAY}; background: {self.WIN95_GRAY};")
            self._radio_favs_layout.addWidget(lbl)
            return

        for i, fav in enumerate(self._radio_favourites):
            row = QWidget()
            row.setStyleSheet(f"background: {self.WIN95_GRAY};")
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(4)

            play_btn = QPushButton(f"▶  {fav['name']}")
            play_btn.setFixedHeight(20)
            play_btn.setFont(QFont("Arial", 8))
            play_btn.setStyleSheet(
                f"QPushButton {{ background: {self.WIN95_LIGHT_GRAY}; border: 1px solid {self.WIN95_DARK_GRAY}; text-align: left; padding-left: 4px; }}"
                f"QPushButton:hover {{ background: {self.ACTIVE_BLUE}; color: white; }}"
            )
            play_btn.clicked.connect(
                lambda checked=False, n=fav['name'], u=fav['url']: self._radio_play_preset(n, u)
            )
            row_lay.addWidget(play_btn, stretch=1)

            rm_btn = QPushButton("✕")
            rm_btn.setFixedSize(24, 20)
            rm_btn.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            rm_btn.setStyleSheet(
                f"QPushButton {{ background: {self.WIN95_LIGHT_GRAY}; border: 1px solid {self.WIN95_DARK_GRAY}; }}"
                f"QPushButton:hover {{ background: #CC4444; color: white; }}"
            )
            rm_btn.clicked.connect(lambda checked=False, idx=i: self._radio_remove_favourite(idx))
            row_lay.addWidget(rm_btn)

            self._radio_favs_layout.addWidget(row)

    def _radio_save_favourite(self):
        url = self._radio_url_entry.text().strip()
        if not url:
            return
        name, ok = QInputDialog.getText(self, "Save Station", "Name this station:")
        if ok and name.strip():
            self._radio_favourites.append({'name': name.strip(), 'url': url})
            self._save_config({'radio_favourites': self._radio_favourites})
            self._radio_refresh_favourites()

    def _radio_remove_favourite(self, idx: int):
        if 0 <= idx < len(self._radio_favourites):
            self._radio_favourites.pop(idx)
            self._save_config({'radio_favourites': self._radio_favourites})
            self._radio_refresh_favourites()

    def _toggle_radio(self):
        if self._radio_frame.isVisible():
            if self._radio_playing:
                self._stop_radio()
            self._right_layout.removeWidget(self._radio_frame)
            self._radio_frame.hide()
            self._radio_btn.setStyleSheet(
                f"background: {self.WIN95_LIGHT_GRAY}; color: black;"
            )
            self._sort_bar_idx -= 1
        else:
            insert_idx = self._sort_bar_idx
            self._right_layout.insertWidget(insert_idx, self._radio_frame)
            self._radio_frame.show()
            self._radio_btn.setStyleSheet(
                f"background: {self.ACTIVE_BLUE}; color: white;"
            )
            self._sort_bar_idx += 1

    def _radio_play_url(self):
        url = self._radio_url_entry.text().strip()
        if url:
            self._start_radio(url, url)

    def _radio_play_preset(self, name, url):
        self._radio_url_entry.setText(url)
        self._start_radio(name, url)

    def _start_radio(self, name, url):
        self.audio_player.stop()
        if self.audio_player.play_stream(url):
            self._radio_playing = True
            self._radio_play_btn.setText("■ Stop")
            self._radio_play_btn.clicked.disconnect()
            self._radio_play_btn.clicked.connect(self._stop_radio)
            self.song_display.setText(f"📻 {name[:30]}")
            self.time_display.setText("LIVE")
            self.artist_display.setText("")
            self.album_display.setText("")
            self.album_art_label.setPixmap(QPixmap())
            self.album_art_label.setText("📻 LIVE")
        else:
            self.song_display.setText("Stream error — check URL")

    def _stop_radio(self):
        self.audio_player.stop_stream()
        self._radio_playing = False
        self._radio_play_btn.setText("▶ Play")
        self._radio_play_btn.clicked.disconnect()
        self._radio_play_btn.clicked.connect(self._radio_play_url)
        self.song_display.setText("No file loaded")
        self.time_display.setText("0:00 / 0:00")
        self.album_art_label.setPixmap(QPixmap())
        self.album_art_label.setText("No Album Art")

    # ------------------------------------------------------------------
    # Search bar
    # ------------------------------------------------------------------

    def _toggle_search(self):
        if self._search_frame.isVisible():
            self._right_layout.removeWidget(self._search_frame)
            self._search_frame.hide()
            self._search_btn.setStyleSheet(
                f"background: {self.WIN95_LIGHT_GRAY}; color: black;"
            )
            self._search_text = ''
            self._search_entry.clear()
            self.populate_tracklist()
            self._sort_bar_idx -= 1
        else:
            insert_idx = self._sort_bar_idx
            self._right_layout.insertWidget(insert_idx, self._search_frame)
            self._search_frame.show()
            self._search_btn.setStyleSheet(
                f"background: {self.ACTIVE_BLUE}; color: white;"
            )
            self._search_entry.setFocus()
            self._sort_bar_idx += 1

    def _on_search_change(self, text: str):
        self._search_text = text.strip().lower()
        self.populate_tracklist()

    # ------------------------------------------------------------------
    # Visualizer
    # ------------------------------------------------------------------

    def _draw_waveform(self, pos_seconds: float = 0.0):
        if self._viz_widget is None:
            return
        bars = self.audio_player.get_viz_frame(pos_seconds, self._VIZ_BARS)
        if not bars:
            self._viz_widget.set_decoding(self._viz_decoding)
            self._viz_widget.update_viz([], [])
            return

        N = len(bars)
        if len(self._viz_peaks) != N:
            self._viz_peaks = [0.0] * N

        for i, amp in enumerate(bars):
            if amp >= self._viz_peaks[i]:
                self._viz_peaks[i] = amp
            else:
                self._viz_peaks[i] = max(amp, self._viz_peaks[i] * self._VIZ_DECAY)

        self._viz_widget.update_viz(bars, list(self._viz_peaks))

    def _start_waveform_compute(self, file_path: str):
        self._viz_peaks = []
        self._viz_decoding = True
        self.audio_player._pcm_data = None
        self.audio_player._pcm_file = None
        if self._viz_widget:
            self._viz_widget.set_decoding(True)

        def _decode():
            self.audio_player.preload_pcm(file_path)
            self._viz_decoding = False
            if self._viz_widget:
                self._viz_widget.set_decoding(False)

        threading.Thread(target=_decode, daemon=True).start()

    # ------------------------------------------------------------------
    # Track list population
    # ------------------------------------------------------------------

    def _get_cached_meta(self, file_path: str) -> dict:
        if file_path not in self._meta_cache:
            self._meta_cache[file_path] = self.audio_player.get_metadata(file_path)
        return self._meta_cache[file_path]

    def _set_sort_mode(self, mode: str):
        self.sort_mode = mode
        for m, btn in self._sort_buttons.items():
            if m == mode:
                btn.setStyleSheet(f"background: {self.ACTIVE_BLUE}; color: white; border: 1px solid {self.WIN95_DARK_GRAY};")
            else:
                btn.setStyleSheet(f"background: {self.WIN95_LIGHT_GRAY}; color: black; border: 1px solid {self.WIN95_DARK_GRAY};")
        self.populate_tracklist()

    def populate_tracklist(self):
        # Clear existing track rows
        self._track_rows.clear()
        while self._tracklist_layout.count() > 1:  # keep the trailing stretch
            item = self._tracklist_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.sort_mode == 'folder':
            self._populate_by_folder()
        else:
            self._populate_by_metadata(self.sort_mode)

    def _build_group_section(self, group_key, label_text: str, icon: str,
                              tracks_with_idx: list, t_num_offset: int = 0):
        """Render one collapsible group. Adds widgets directly to _tracklist_layout."""
        # Apply search filter
        if self._search_text:
            tracks_with_idx = [
                (pi, fp) for pi, fp in tracks_with_idx
                if self._search_text in os.path.splitext(os.path.basename(fp))[0].lower()
                or self._search_text in self._get_cached_meta(fp).get('artist', '').lower()
                or self._search_text in self._get_cached_meta(fp).get('album', '').lower()
            ]
            if not tracks_with_idx:
                return

        header_bg = "#909090"
        is_expanded = self.folder_states.get(group_key, True) if not self._search_text else True

        # Header
        header = QWidget()
        header.setFixedHeight(24)
        header.setStyleSheet(f"background: {header_bg};")
        hdr_lay = QHBoxLayout(header)
        hdr_lay.setContentsMargins(6, 0, 5, 0)
        hdr_lay.setSpacing(4)

        chevron = QLabel("▼" if is_expanded else "▶")
        chevron.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        chevron.setStyleSheet(f"background: {header_bg}; color: black;")
        chevron.setFixedWidth(18)
        hdr_lay.addWidget(chevron)

        folder_lbl = QLabel(f"{icon}  {label_text}")
        folder_lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        folder_lbl.setStyleSheet(f"background: {header_bg}; color: black;")
        hdr_lay.addWidget(folder_lbl, stretch=1)

        count_lbl = QLabel(f"{len(tracks_with_idx)} tracks")
        count_lbl.setFont(QFont("Arial", 9))
        count_lbl.setStyleSheet(f"background: {header_bg}; color: #303030;")
        count_lbl.setFixedWidth(58)
        count_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        hdr_lay.addWidget(count_lbl)

        # Insert header before the stretch (last item)
        insert_pos = self._tracklist_layout.count() - 1
        self._tracklist_layout.insertWidget(insert_pos, header)
        insert_pos += 1

        # Tracks container
        container = QWidget()
        container.setStyleSheet(f"background: {self.TRACKLIST_BG};")
        cont_lay = QVBoxLayout(container)
        cont_lay.setContentsMargins(0, 0, 0, 0)
        cont_lay.setSpacing(0)

        for t_idx, (pi, file_path) in enumerate(tracks_with_idx):
            track_name = os.path.splitext(os.path.basename(file_path))[0]
            duration_str = self.audio_player.format_time(
                self.audio_player.get_file_duration(file_path))
            row = _TrackRow(pi,
                            f"{t_num_offset + t_idx + 1:02d}.",
                            track_name,
                            duration_str,
                            self.play_track_from_list,
                            self.TRACKLIST_BG)
            cont_lay.addWidget(row)
            self._track_rows.append(row)

        container.setVisible(is_expanded)
        self._tracklist_layout.insertWidget(insert_pos, container)

        # Click on header to collapse/expand
        gk, tc, ch = group_key, container, chevron
        header.mousePressEvent = lambda _e, k=gk, c=tc, v=ch: self._toggle_folder(k, c, v)
        for child in header.findChildren(QLabel):
            child.mousePressEvent = lambda _e, k=gk, c=tc, v=ch: self._toggle_folder(k, c, v)

    def _populate_by_folder(self):
        playlist_idx = 0
        for f_idx, folder in enumerate(self.audio_player.folders):
            tracks_with_idx = [(playlist_idx + i, p)
                               for i, p in enumerate(folder['tracks'])]
            self._build_group_section(f_idx, folder['name'], "📁", tracks_with_idx)
            playlist_idx += len(folder['tracks'])

    def _populate_by_metadata(self, field: str):
        field_labels = {'artist': ('👤', 'Unknown Artist'),
                        'album':  ('💿', 'Unknown Album'),
                        'genre':  ('🎵', 'Unknown Genre')}
        icon, unknown = field_labels.get(field, ('📁', 'Unknown'))

        groups: dict = {}
        for idx, file_path in enumerate(self.audio_player.playlist):
            key = self._get_cached_meta(file_path).get(field, '').strip() or unknown
            groups.setdefault(key, []).append((idx, file_path))

        t_offset = 0
        for group_name in sorted(groups.keys(), key=lambda s: s.lower()):
            group_key = f"{field}_{group_name}"
            self._build_group_section(group_key, group_name, icon,
                                      groups[group_name], t_num_offset=t_offset)
            t_offset += len(groups[group_name])

    def _toggle_folder(self, folder_idx, tracks_container: QWidget, chevron: QLabel):
        expanded = self.folder_states.get(folder_idx, True)
        if expanded:
            tracks_container.hide()
            chevron.setText("▶")
            self.folder_states[folder_idx] = False
        else:
            self.folder_states[folder_idx] = True
            self.populate_tracklist()

    def highlight_track(self, index: int):
        for row in self._track_rows:
            row.set_active(row._playlist_idx == index)

    # ------------------------------------------------------------------
    # Playback controls
    # ------------------------------------------------------------------

    def play_track_from_list(self, index: int):
        if self.audio_player.play_track_at_index(index):
            self.update_current_track_display()

    def update_current_track_display(self):
        if self.audio_player.current_file:
            filename = self.audio_player.get_current_filename()
            if len(filename) > 35:
                filename = filename[:32] + "..."
            self.song_display.setText(f"▶ {filename}")

            if self.audio_player.current_track_index >= 0:
                self.track_num.setText(str(self.audio_player.current_track_index + 1))
                self.highlight_track(self.audio_player.current_track_index)

            self.update_metadata_display()
            self.update_album_art()
            self._start_waveform_compute(self.audio_player.current_file)

    def update_metadata_display(self):
        if not self.audio_player.current_file:
            self.artist_display.setText("")
            self.album_display.setText("")
            return
        meta = self.audio_player.get_metadata(self.audio_player.current_file)
        artist = meta['artist'] or 'Unknown Artist'
        self.artist_display.setText(f"\u266a {artist[:34]}")
        album = meta['album']
        year  = meta['year']
        if album and year:
            album_text = f"{album[:24]}  ({year})"
        elif album:
            album_text = album[:34]
        elif year:
            album_text = year
        else:
            album_text = ''
        self.album_display.setText(f"  {album_text}")

    def update_album_art(self):
        if self.audio_player.current_file:
            album_art = self.audio_player.get_album_art(self.audio_player.current_file)
            if album_art:
                album_art.thumbnail((280, 280), Image.Resampling.LANCZOS)
                px = _pil_to_qpixmap(album_art)
                self.current_album_art = px
                self.album_art_label.setPixmap(px)
                self.album_art_label.setText("")
            else:
                self.album_art_label.setPixmap(QPixmap())
                self.album_art_label.setText("No Album Art")

    def play_music(self):
        if self.audio_player.play():
            self.update_current_track_display()
        else:
            self.song_display.setText("No file loaded")

    def pause_music(self):
        if self.audio_player.pause():
            filename = self.audio_player.get_current_filename()
            if filename:
                if len(filename) > 35:
                    filename = filename[:32] + "..."
                self.song_display.setText(f"II {filename}")

    def stop_music(self):
        if self._radio_playing:
            self._stop_radio()
            return
        self.audio_player.stop()
        filename = self.audio_player.get_current_filename()
        if filename:
            if len(filename) > 35:
                filename = filename[:32] + "..."
            self.song_display.setText(f"■ {filename}")

    def previous_track(self):
        if self.audio_player.play_previous():
            self.update_current_track_display()
        else:
            self.song_display.setText("⏮ No previous track")

    def next_track(self):
        if self.audio_player.play_next():
            self.update_current_track_display()
        else:
            self.song_display.setText("⏭ No next track")

    def toggle_shuffle(self):
        active = self.audio_player.toggle_shuffle()
        if active:
            self.shuffle_btn.setStyleSheet(f"background: {self.ACTIVE_BLUE}; color: white;")
            self.shuffle_btn.setText("🔀 On")
        else:
            self.shuffle_btn.setStyleSheet("")
            self.shuffle_btn.setText("🔀")

    def cycle_repeat(self):
        mode = self.audio_player.cycle_repeat()
        labels = {
            0: ("🔁 Off", ""),
            1: ("🔁 All", f"background: {self.ACTIVE_BLUE}; color: white;"),
            2: ("🔂 One", f"background: {self.ACTIVE_BLUE}; color: white;"),
        }
        text, style = labels[mode]
        self.repeat_btn.setText(text)
        self.repeat_btn.setStyleSheet(style)

    # ------------------------------------------------------------------
    # Seek
    # ------------------------------------------------------------------

    def _seek_start(self):
        self.seeking = True

    def _on_seek_drag(self, value: int):
        if self.seeking:
            self._seek_pending = float(value)

    def _seek_end(self):
        total = self.audio_player.get_duration()
        if total > 0:
            target_seconds = (self._seek_pending / 100.0) * total
            self.audio_player.seek(target_seconds)
        self.seeking = False

    def change_volume(self, value: int):
        self.audio_player.set_volume(value / 100)
        self.volume_label.setText(f"{value}%")

    # ------------------------------------------------------------------
    # 100ms timer tick
    # ------------------------------------------------------------------

    def _update_tick(self):
        if self._radio_playing:
            self._draw_waveform(0.0)
            return

        if self.audio_player.current_file:
            current_time = self.audio_player.get_position()
            total_time   = self.audio_player.get_duration()

            self.time_display.setText(
                f"{self.audio_player.format_time(current_time)} / "
                f"{self.audio_player.format_time(total_time)}"
            )

            if not self.seeking:
                progress = int(current_time / total_time * 100) if total_time > 0 else 0
                self.seek_slider.blockSignals(True)
                self.seek_slider.setValue(progress)
                self.seek_slider.blockSignals(False)

            self._draw_waveform(current_time)

            if self.audio_player.is_playing and current_time >= total_time and total_time > 0:
                if self.audio_player.play_next():
                    self.update_current_track_display()
                else:
                    self.stop_music()

            # Update Save Art to Tags menu item enabled state
            can_save = (self._pending_art_image is not None and
                        self.audio_player.current_file is not None)
            self._art_save_action.setEnabled(can_save)
        else:
            self.time_display.setText("0:00 / 0:00")
            if not self.seeking:
                self.seek_slider.blockSignals(True)
                self.seek_slider.setValue(0)
                self.seek_slider.blockSignals(False)
            self._draw_waveform(0.0)

    # Kept for API compatibility with main.py
    def run(self):
        pass

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _bind_keyboard_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Space),  self).activated.connect(self._kb_play_pause)
        QShortcut(QKeySequence(Qt.Key.Key_S),      self).activated.connect(self.stop_music)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self).activated.connect(self.stop_music)
        QShortcut(QKeySequence(Qt.Key.Key_Left),   self).activated.connect(self.previous_track)
        QShortcut(QKeySequence(Qt.Key.Key_Right),  self).activated.connect(self.next_track)
        QShortcut(QKeySequence(Qt.Key.Key_Up),     self).activated.connect(self._kb_volume_up)
        QShortcut(QKeySequence(Qt.Key.Key_Down),   self).activated.connect(self._kb_volume_down)

    def _kb_play_pause(self):
        if self.audio_player.is_playing:
            self.pause_music()
        else:
            self.play_music()

    def _kb_volume_up(self):
        new_val = min(100, self.volume_slider.value() + 5)
        self.volume_slider.setValue(new_val)

    def _kb_volume_down(self):
        new_val = max(0, self.volume_slider.value() - 5)
        self.volume_slider.setValue(new_val)

    # ------------------------------------------------------------------
    # Drag and drop (native Qt)
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        supported = {'.mp3', '.m4a', '.mp4', '.aac', '.wma', '.wav', '.flac'}
        changed = False
        groups: dict = {}

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

    # ------------------------------------------------------------------
    # Playlist
    # ------------------------------------------------------------------

    def load_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Music Folder",
            self.default_music_folder if self.default_music_folder else "/"
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

    def save_playlist(self):
        if not self.audio_player.playlist:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Playlist", "",
            "M3U Playlist (*.m3u);;All Files (*.*)"
        )
        if file_path:
            self.audio_player.save_playlist_m3u(file_path)

    def load_playlist(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Playlist", "",
            "M3U Playlist (*.m3u);;All Files (*.*)"
        )
        if file_path:
            if self.audio_player.load_playlist_m3u(file_path):
                self.populate_tracklist()
                if self.audio_player.playlist:
                    self.audio_player.load_file(self.audio_player.playlist[0])
                    self.audio_player.current_track_index = 0
                    self.update_current_track_display()

    def clear_all(self):
        if self._radio_playing:
            self._stop_radio()
        self.audio_player.reset()

        self._track_rows.clear()
        while self._tracklist_layout.count() > 1:
            item = self._tracklist_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.song_display.setText("No file loaded")
        self.track_num.setText("1")
        self.time_display.setText("0:00 / 0:00")
        self.artist_display.setText("")
        self.album_display.setText("")

        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(0)
        self.seek_slider.blockSignals(False)

        self._pending_art_image = None
        self.current_album_art  = None
        self.album_art_label.setPixmap(QPixmap())
        self.album_art_label.setText("No Album Art")

        self.shuffle_btn.setStyleSheet("")
        self.shuffle_btn.setText("🔀")
        self.repeat_btn.setStyleSheet("")
        self.repeat_btn.setText("🔁 Off")

        self._search_text = ''
        if self._search_entry:
            self._search_entry.clear()
        if self._search_frame and self._search_frame.isVisible():
            self._toggle_search()

        self._viz_peaks    = []
        self._viz_decoding = False
        if self._viz_widget:
            self._viz_widget.update_viz([], [])

        self.folder_states = {}
        self._meta_cache   = {}
        self.sort_mode     = 'folder'
        for m, btn in self._sort_buttons.items():
            if m == 'folder':
                btn.setStyleSheet(f"background: {self.ACTIVE_BLUE}; color: white; border: 1px solid {self.WIN95_DARK_GRAY};")
            else:
                btn.setStyleSheet(f"background: {self.WIN95_LIGHT_GRAY}; color: black; border: 1px solid {self.WIN95_DARK_GRAY};")

    # ------------------------------------------------------------------
    # File menu actions
    # ------------------------------------------------------------------

    def _open_single_file(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Audio File", "",
            "Audio Files (*.mp3 *.m4a *.aac *.wma *.wav *.flac);;All Files (*.*)"
        )
        if paths:
            self.audio_player.add_files_to_playlist(list(paths))
            self.populate_tracklist()
            if self.audio_player.current_track_index < 0:
                self.audio_player.load_file(self.audio_player.playlist[0])
                self.audio_player.current_track_index = 0
                self.update_current_track_display()

    # ------------------------------------------------------------------
    # Album art
    # ------------------------------------------------------------------

    def _art_load_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Album Art", "",
            "Image Files (*.jpg *.jpeg *.png *.bmp *.webp);;All Files (*.*)"
        )
        if path:
            try:
                img = Image.open(path)
                self._pending_art_image = img.copy()
                self._display_art(img)
            except Exception as e:
                print(f"Error loading image: {e}")

    def _art_find_online(self):
        if not self.audio_player.current_file:
            return
        meta  = self.audio_player.get_metadata(self.audio_player.current_file)
        title = os.path.splitext(self.audio_player.get_current_filename())[0]
        self.song_display.setText("Searching for art...")
        QApplication.processEvents()
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
            self.song_display.setText("Art found — use File > Save Art to Tags")
        else:
            self.song_display.setText("No art found online")

    def _display_art(self, img: Image.Image):
        img.thumbnail((280, 280), Image.Resampling.LANCZOS)
        px = _pil_to_qpixmap(img)
        self.current_album_art = px
        self.album_art_label.setPixmap(px)
        self.album_art_label.setText("")

    def _art_save_to_tags(self):
        if not self._pending_art_image or not self.audio_player.current_file:
            return
        buf = io.BytesIO()
        self._pending_art_image.convert('RGB').save(buf, format='JPEG', quality=90)
        if self.audio_player.embed_album_art(self.audio_player.current_file, buf.getvalue()):
            self._pending_art_image = None
            self.song_display.setText("Art saved to tags")

    def _art_clear(self):
        self._pending_art_image = None
        self.current_album_art  = None
        self.album_art_label.setPixmap(QPixmap())
        self.album_art_label.setText("No Album Art")

    # ------------------------------------------------------------------
    # Config persistence
    # ------------------------------------------------------------------

    def _load_config(self) -> dict:
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_config(self, data: dict):
        try:
            existing = self._load_config()
            existing.update(data)
            with open(CONFIG_PATH, 'w') as f:
                json.dump(existing, f, indent=2)
        except Exception as e:
            print(f"Config save error: {e}")
