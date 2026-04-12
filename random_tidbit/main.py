#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Qt application for showing random historical tidbit using an LLM.
#
# note:
# - based orignally on
#   https://www.qt.io/blog/2018/05/04/hello-qt-for-python
#   https://kivy.org/doc/stable/api-kivy.app.html
# - includes ideas from following:
#   https://www.qt.io/blog/taking-qt-for-python-to-android
#   https://github.com/EchterAlsFake/PySide6-to-Android
#
# TODO2: have the form shown initially (in case delay in tidbit retrieval)
#

"""Displays random historical tidbit"""

# Standard packages
import base64
import datetime
import glob
import importlib.util
import json
import os
import sys

# Installed packages
from PySide6.QtCore import QDate, QEvent, QObject, QSize, Qt, QThread, QTimer, QRect
from PySide6.QtGui import QFont, QIcon, QKeySequence, QPainter, QColor, QPen, QPixmap, QShortcut, QTextCharFormat
from PySide6.QtWidgets import (
    QApplication, QBoxLayout, QCalendarWidget, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
    QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QTextEdit,
    QVBoxLayout, QWidget)
from PySide6.QtCore import Signal

# Local modules
## NOTE: setdefault provides desktop fallback; on Android, p4a_env_vars.txt sets DEBUG_LEVEL=6
os.environ.setdefault("DEBUG_LEVEL", "5")
## DEBUG: verify __debug__ and DEBUG_LEVEL reach Python (output via start.c LogFile → logcat)
sys.stderr.write(f"{__debug__=} {os.environ.get('DEBUG_LEVEL')=}\n")

from mezcla import debug, system
# Note: poe_client is imported lazily inside each function (not at module level)
# to avoid triggering mezcla's Main argument-parsing machinery at import time.

DEFAULT_PROMPT = "Give some random bit of history for {date}--one entry"
AGE_GROUPS = ["18+", "14-18", "9-14", "6-9", "3-5"]

# Core palette
COLOR_PARCHMENT_BG = "#ece1cf"          # parchment beige
COLOR_INK_BROWN = "#2d2416"             # dark roast brown
COLOR_INPUT_TAN = "#f6ebd8"             # light tan
COLOR_BORDER_KHAKI = "#ccb690"          # sand khaki
COLOR_SELECTION_SAGE = "#b9d0a8"        # soft sage green
COLOR_FOCUS_BROWN = "#9a8559"           # caramel brown
COLOR_INPUT_CREAM = "#fbf4e8"           # warm cream
COLOR_BUTTON_STEEL = "#7088a3"          # dusty steel blue
COLOR_BUTTON_TEXT = "#fffdf8"           # porcelain white
COLOR_BUTTON_DISABLED = "#b9c8d6"       # pale slate blue
COLOR_BUTTON_STEEL_HOVER = "#5f7995"    # stormy steel blue
COLOR_FETCH_SAGE = "#78926a"            # muted sage
COLOR_FETCH_TEXT = "#fffaf1"            # ivory cream
COLOR_FETCH_SAGE_HOVER = "#667f58"      # shaded sage
COLOR_QUIT_BG = "#f7ecdf"               # blush linen
COLOR_QUIT_TEXT = "#7b433b"             # brick rose
COLOR_QUIT_BORDER = "#b48075"           # dusty rose
COLOR_QUIT_BG_HOVER = "#f1dfcf"         # peach linen
COLOR_QUIT_TEXT_HOVER = "#652b24"       # mahogany brown
COLOR_CAL_BUTTON_BG = "#f7efe2"         # oat cream
COLOR_CAL_BUTTON_HOVER = "#fbf5eb"      # pale vanilla
COLOR_TOGGLE_BLUE = "#537392"           # weathered denim
COLOR_TOGGLE_BLUE_HOVER = "#355774"     # twilight blue
COLOR_RESULT_CARD_BG = "#fffdf8"        # milk white
COLOR_IMAGE_CARD_BG = "#fffef9"         # soft ivory
COLOR_CAPTION_TAUPE = "#7d725b"         # warm taupe
COLOR_DEBUG_BG = "#1a1b2e"              # midnight navy
COLOR_DEBUG_TEXT = "#8a9bb0"            # misty blue-gray
COLOR_CAL_ALT_BG = "#f5ead8"            # almond cream
COLOR_CAL_TOOL_TEXT = "#3d4f66"         # slate blue-gray
COLOR_CAL_MENU_BG = "#fff9ef"           # eggshell
COLOR_CAL_SELECTION_BG = "#c8ddb5"      # pale moss
COLOR_CAL_DAY_BG = "#fffaf1"            # butter cream
COLOR_CAL_DAY_SELECTION = "#7c9870"     # moss green
COLOR_WHITE = "#ffffff"                 # white

# Age-group palette
COLOR_KIDS_TEXT = "#55351a"             # dark saddle brown
COLOR_KIDS_CAPTION = "#946c30"          # warm golden brown
COLOR_KIDS_CARD_BG = "#fff6d8"          # pale butter yellow
COLOR_KIDS_CARD_BORDER = "#d5b56c"      # honey gold
COLOR_CHILD_TEXT = "#4a3218"            # chestnut brown
COLOR_CHILD_CAPTION = "#866338"         # bronze brown
COLOR_CHILD_CARD_BG = "#fff8e6"         # vanilla cream
COLOR_CHILD_CARD_BORDER = "#d2bc86"     # antique gold
COLOR_TWEEN_TEXT = "#3a2b18"            # dark walnut
COLOR_TWEEN_CAPTION = "#6e6754"         # taupe gray
COLOR_TWEEN_CARD_BG = "#fffbf1"         # linen white
COLOR_TWEEN_CARD_BORDER = "#cab795"     # sandstone tan
COLOR_TEEN_TEXT = "#30271b"             # deep espresso brown
COLOR_TEEN_CAPTION = "#6a6254"          # muted olive taupe
COLOR_TEEN_CARD_BG = "#fff8ea"          # warm ivory parchment
COLOR_TEEN_CARD_BORDER = "#cfb68e"      # honey beige
COLOR_ADULT_CARD_BG = "#fff9eb"         # parchment cream
COLOR_ADULT_CAPTION = "#6b6151"         # earthy mushroom taupe
COLOR_ADULT_CARD_BORDER = "#d0b88f"     # warm mushroom beige

# Calendar icon palette
COLOR_CAL_ICON_HEADER = "#c56c58"       # terracotta rose
COLOR_CAL_ICON_OUTLINE = "#8e7654"      # bronze taupe
COLOR_CAL_ICON_GRID = "#c8b79a"         # parchment grid tan
COLOR_CAL_ICON_ACCENT = "#7d9a68"       # olive sage
COLOR_CAL_ICON_RING = "#f4e0d8"         # pale blush
COLOR_CAL_DIALOG_BG = "#fff8ed"         # light parchment
COLOR_REFRESH_ICON = "#5f7995"          # stormy steel blue


def _build_app_stylesheet() -> str:
    """Return the shared application stylesheet."""
    return f"""
        QWidget {{
            background-color: {COLOR_PARCHMENT_BG};
            color: {COLOR_INK_BROWN};
            font-family: "Trebuchet MS", "Verdana", sans-serif;
            font-size: 13px;
        }}
        QLineEdit, QDateEdit, QComboBox, QTextEdit {{
            background-color: {COLOR_INPUT_TAN};
            border: 1px solid {COLOR_BORDER_KHAKI};
            border-radius: 8px;
            padding: 5px 8px;
            selection-background-color: {COLOR_SELECTION_SAGE};
        }}
        QLineEdit:focus, QDateEdit:focus, QComboBox:focus, QTextEdit:focus {{
            border: 1px solid {COLOR_FOCUS_BROWN};
            background-color: {COLOR_INPUT_CREAM};
        }}
        QComboBox::drop-down {{ border: none; }}
        QPushButton {{
            background-color: {COLOR_BUTTON_STEEL};
            color: {COLOR_BUTTON_TEXT};
            border: none;
            border-radius: 8px;
            padding: 6px 18px;
            font-weight: bold;
            font-size: 13px;
        }}
        QPushButton:disabled {{
            background-color: {COLOR_BUTTON_DISABLED};
        }}
        QPushButton:hover:!disabled {{
            background-color: {COLOR_BUTTON_STEEL_HOVER};
        }}
        #fetch_button {{
            background-color: {COLOR_FETCH_SAGE};
            color: {COLOR_FETCH_TEXT};
            padding: 6px 18px;
        }}
        #fetch_button:hover {{
            background-color: {COLOR_FETCH_SAGE_HOVER};
        }}
        #quit_button {{
            background-color: {COLOR_QUIT_BG};
            color: {COLOR_QUIT_TEXT};
            border: 1px solid {COLOR_QUIT_BORDER};
            border-radius: 8px;
            padding: 0px;
            font-size: 15px;
            font-weight: 700;
        }}
        #quit_button:hover {{
            background-color: {COLOR_QUIT_BG_HOVER};
            color: {COLOR_QUIT_TEXT_HOVER};
        }}
        #cal_button {{
            background-color: {COLOR_CAL_BUTTON_BG};
            border: 1px solid {COLOR_BORDER_KHAKI};
            border-radius: 8px;
            padding: 3px;
        }}
        #cal_button:hover {{
            background-color: {COLOR_CAL_BUTTON_HOVER};
        }}
        #image_refresh_button {{
            background-color: {COLOR_CAL_BUTTON_BG};
            border: 1px solid {COLOR_BORDER_KHAKI};
            border-radius: 8px;
            padding: 3px;
        }}
        #image_refresh_button:hover {{
            background-color: {COLOR_CAL_BUTTON_HOVER};
        }}
        #toggle_button {{
            background-color: transparent;
            color: {COLOR_TOGGLE_BLUE};
            border: none;
            text-align: left;
            padding: 1px 2px;
            font-size: 11px;
            font-weight: normal;
        }}
        #toggle_button:hover {{
            color: {COLOR_TOGGLE_BLUE_HOVER};
        }}
        QDateEdit::up-button, QDateEdit::down-button {{
            width: 0px;
            height: 0px;
            border: none;
        }}
        #result_card {{
            background-color: {COLOR_ADULT_CARD_BG};
            border: 1px solid {COLOR_BORDER_KHAKI};
            border-radius: 12px;
        }}
        #image_card {{
            background-color: {COLOR_ADULT_CARD_BG};
            border: 1px solid {COLOR_BORDER_KHAKI};
            border-radius: 12px;
        }}
        #image_caption {{
            color: {COLOR_CAPTION_TAUPE};
            font-size: 10px;
            font-style: italic;
            padding: 4px 6px;
        }}
        #debug_pane {{
            background-color: {COLOR_DEBUG_BG};
            color: {COLOR_DEBUG_TEXT};
            border: none;
            border-radius: 0px;
            padding: 4px;
            font-family: monospace;
            font-size: 9px;
        }}
        QCalendarWidget QWidget {{
            alternate-background-color: {COLOR_CAL_ALT_BG};
        }}
        QCalendarWidget QToolButton {{
            color: {COLOR_CAL_TOOL_TEXT};
            background-color: {COLOR_CAL_BUTTON_BG};
            border: 1px solid {COLOR_BORDER_KHAKI};
            border-radius: 6px;
            padding: 4px 8px;
            min-width: 22px;
        }}
        QCalendarWidget QToolButton:hover {{
            background-color: {COLOR_CAL_BUTTON_HOVER};
        }}
        QCalendarWidget QMenu {{
            background-color: {COLOR_CAL_MENU_BG};
            color: {COLOR_INK_BROWN};
        }}
        QCalendarWidget QSpinBox {{
            background-color: {COLOR_CAL_MENU_BG};
            color: {COLOR_INK_BROWN};
            selection-background-color: {COLOR_CAL_SELECTION_BG};
        }}
        QCalendarWidget QAbstractItemView:enabled {{
            background-color: {COLOR_CAL_DAY_BG};
            color: {COLOR_INK_BROWN};
            selection-background-color: {COLOR_CAL_DAY_SELECTION};
            selection-color: {COLOR_WHITE};
        }}
    """


def _age_group_ui_profile(age_group):
    """Return display settings tailored to AGE_GROUP."""
    profiles = {
        "3-5": {
            "font_family": "Comic Sans MS",
            "result_point_size": 20,
            "label_point_size": 15,
            "caption_point_size": 12,
            "text_color": COLOR_KIDS_TEXT,
            "caption_color": COLOR_KIDS_CAPTION,
            "card_bg": COLOR_KIDS_CARD_BG,
            "card_border": COLOR_KIDS_CARD_BORDER,
        },
        "6-9": {
            "font_family": "Trebuchet MS",
            "result_point_size": 18,
            "label_point_size": 14,
            "caption_point_size": 11,
            "text_color": COLOR_CHILD_TEXT,
            "caption_color": COLOR_CHILD_CAPTION,
            "card_bg": COLOR_CHILD_CARD_BG,
            "card_border": COLOR_CHILD_CARD_BORDER,
        },
        "9-14": {
            "font_family": "Verdana",
            "result_point_size": 16,
            "label_point_size": 13,
            "caption_point_size": 11,
            "text_color": COLOR_TWEEN_TEXT,
            "caption_color": COLOR_TWEEN_CAPTION,
            "card_bg": COLOR_TWEEN_CARD_BG,
            "card_border": COLOR_TWEEN_CARD_BORDER,
        },
        "14-18": {
            "font_family": "Avenir Next",
            "result_point_size": 15,
            "label_point_size": 12,
            "caption_point_size": 10,
            "text_color": COLOR_TEEN_TEXT,
            "caption_color": COLOR_TEEN_CAPTION,
            "card_bg": COLOR_TEEN_CARD_BG,
            "card_border": COLOR_TEEN_CARD_BORDER,
        },
        "18+": {
            "font_family": "Palatino Linotype",
            "result_point_size": 14,
            "label_point_size": 12,
            "caption_point_size": 10,
            "text_color": COLOR_INK_BROWN,
            "caption_color": COLOR_ADULT_CAPTION,
            "card_bg": COLOR_ADULT_CARD_BG,
            "card_border": COLOR_ADULT_CARD_BORDER,
        },
    }
    return profiles.get(age_group, profiles["18+"])


def _make_calendar_icon(size: int = 40) -> QIcon:
    """Draw a larger, more recognisable paper-calendar icon."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    outer_rect = QRect(2, 3, size - 4, size - 5)
    body = QColor(COLOR_FETCH_TEXT)
    header = QColor(COLOR_CAL_ICON_HEADER)
    outline = QColor(COLOR_CAL_ICON_OUTLINE)
    grid_line = QColor(COLOR_CAL_ICON_GRID)
    accent = QColor(COLOR_CAL_ICON_ACCENT)

    p.setPen(QPen(outline, 1.2))
    p.setBrush(body)
    p.drawRoundedRect(outer_rect, 4, 4)

    header_h = max(9, size // 4)
    p.setPen(Qt.NoPen)
    p.setBrush(header)
    p.drawRoundedRect(2, 3, size - 4, header_h, 4, 4)
    p.drawRect(2, header_h // 2 + 3, size - 4, header_h // 2)

    ring_y = 5
    ring_w = max(4, size // 9)
    ring_h = max(5, size // 7)
    for x_offset in (size // 4, size - size // 4 - ring_w):
        p.setBrush(QColor(COLOR_CAL_ICON_RING))
        p.drawRoundedRect(x_offset, ring_y, ring_w, ring_h, 2, 2)

    p.setPen(QPen(grid_line, 1))
    grid_left = 6
    grid_top = header_h + 7
    grid_w = size - 12
    grid_h = size - grid_top - 6
    cols, rows = 7, 5
    cell_w = grid_w / cols
    cell_h = grid_h / rows
    for row in range(rows):
        for col in range(cols):
            cx = int(grid_left + col * cell_w)
            cy = int(grid_top + row * cell_h)
            cw = max(2, int(cell_w) - 1)
            ch = max(2, int(cell_h) - 1)
            if row == 1 and col == 3:
                p.fillRect(cx + 1, cy + 1, max(1, cw - 2), max(1, ch - 2), accent)
            p.drawRect(cx, cy, cw, ch)

    p.end()
    return QIcon(pix)


def _make_refresh_icon(size: int = 28) -> QIcon:
    """Draw a circular refresh arrow used for image regeneration."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    pen = QPen(QColor(COLOR_REFRESH_ICON), 2.2)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    arc_rect = QRect(4, 4, size - 8, size - 8)
    p.drawArc(arc_rect, 40 * 16, 280 * 16)

    arrow_x = size - 7
    arrow_y = size // 2 - 5
    p.drawLine(arrow_x, arrow_y, arrow_x - 8, arrow_y + 1)
    p.drawLine(arrow_x, arrow_y, arrow_x - 2, arrow_y + 8)

    p.end()
    return QIcon(pix)


def _center_combo_text(combo):
    """Center the current combo-box text without allowing free-form edits."""
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.NoInsert)
    line_edit = combo.lineEdit()
    line_edit.setReadOnly(True)
    line_edit.setAlignment(Qt.AlignCenter)
    line_edit.setFrame(False)
    line_edit.setCursor(Qt.ArrowCursor)
    line_edit.setStyleSheet("QLineEdit { border: none; background: transparent; padding: 0px; }")
    return line_edit


def _apply_age_group_presentation(age_group, result_text, image_label, image_caption,
                                  result_card, image_card):
    """Apply fonts and warm accent colors for the selected AGE_GROUP."""
    profile = _age_group_ui_profile(age_group)

    result_font = QFont(profile["font_family"])
    result_font.setPointSize(profile["result_point_size"])
    result_font.setStyleStrategy(QFont.PreferAntialias)
    result_text.setFont(result_font)
    result_text.setStyleSheet(
        "QTextEdit { "
        f"border: none; background-color: transparent; color: {profile['text_color']}; "
        f"selection-background-color: {COLOR_SELECTION_SAGE}; }}"
    )

    label_font = QFont(profile["font_family"])
    label_font.setPointSize(profile["label_point_size"])
    label_font.setBold(age_group in ("3-5", "6-9"))
    image_label.setFont(label_font)
    image_label.setStyleSheet(
        "QLabel { border: none; background-color: transparent; "
        f"color: {profile['caption_color']}; font-size: {profile['label_point_size']}pt; }}"
    )

    caption_font = QFont(profile["font_family"])
    caption_font.setPointSize(profile["caption_point_size"])
    image_caption.setFont(caption_font)
    image_caption.setStyleSheet(
        f"QLabel {{ color: {profile['caption_color']}; padding: 4px 6px; }}"
    )

    card_style = (
        "QWidget { "
        f"background-color: {profile['card_bg']}; "
        f"border: 1px solid {profile['card_border']}; "
        "border-radius: 12px; }"
    )
    result_card.setStyleSheet(card_style)
    image_card.setStyleSheet(card_style)


def _content_layout_direction(width: int, height: int):
    """Return the layout direction for the tidbit content area."""
    return QBoxLayout.TopToBottom if height > width else QBoxLayout.LeftToRight


def _apply_content_layout_orientation(content_layout, width: int, height: int):
    """Stack in portrait mode and place side-by-side in landscape mode."""
    direction = _content_layout_direction(width, height)
    content_layout.setDirection(direction)
    if direction == QBoxLayout.TopToBottom:
        content_layout.setStretch(0, 3)
        content_layout.setStretch(1, 2)
    else:
        content_layout.setStretch(0, 2)
        content_layout.setStretch(1, 1)
    return direction

## Note: test by Gemini to resolve stack trace issue

POE_API = system.getenv_value(
    ## TODO1: get from vault
    "POE_API", "Gek9rnD3phMdVY5xM2JCTAKaMYHWR8B6oVt70-jGnc0",
    desc="Platform for Open Exploration (POE)",
    skip_register=True)
POE_MODEL = system.getenv_text(
    "POE_MODEL", "GPT-5-mini",
    desc="LLM model for POE",
    skip_register=True)
POE_TIMEOUT = system.getenv_float(
    "POE_TIMEOUT", 30.0,
    desc="Timeout in seconds for text model calls",
    skip_register=True)
POE_IMAGE_TIMEOUT = system.getenv_float(
    "POE_IMAGE_TIMEOUT", 120.0,
    desc="Timeout in seconds for image generation calls (FLUX-schnell can take 60-90 s)",
    skip_register=True)
POE_IMAGE_MODEL = system.getenv_text(
    "POE_IMAGE_MODEL", "FLUX-schnell",
    desc="Image generation model for POE",
    skip_register=True)
SHOW_IMAGE = system.getenv_bool(
    "SHOW_IMAGE", True,
    desc="Whether to generate and show an image alongside the tidbit",
    skip_register=True)
DISABLE_CACHE_LOOKUP = system.getenv_bool(
    "DISABLE_CACHE_LOOKUP", False,
    desc="Whether to bypass tidbit/image cache lookups",
    skip_register=True)

# Result cache: (date_str, age_group) -> {"tidbit", "image_bytes", "image_prompt"}
# In-memory dict; write-through to disk via _save_cache() / loaded at startup via _load_cache().
_fetch_cache = {}

def _cache_file_path() -> str:
    """Return the path to the on-disk JSON cache file.

    Desktop: <app_dir>/tidbit_cache.json
    Android: /data/data/<package>/files/tidbit_cache.json (same dir as main.pyc)
    The directory is guaranteed writable on both platforms.
    """
    app_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(app_dir, "tidbit_cache.json")


def _load_cache():
    """Load the disk cache into _fetch_cache at startup (best-effort; silent on error)."""
    path = _cache_file_path()
    debug.trace(4, f"_load_cache: reading {path!r}")
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        for key_str, entry in raw.items():
            date_str, age_group = key_str.split("|", 1)
            # image_bytes is stored as base64 string; decode back to bytes
            img_b64 = entry.get("image_bytes", "")
            entry["image_bytes"] = base64.b64decode(img_b64) if img_b64 else b""
            _fetch_cache[(date_str, age_group)] = entry
        debug.trace(3, f"_load_cache: loaded {len(_fetch_cache)} entries from {path!r}")
    except FileNotFoundError:
        debug.trace(4, "_load_cache: no cache file yet")
    except Exception:                    # pylint: disable=broad-exception-caught
        system.print_exception_info("_load_cache")


def _save_cache():
    """Persist _fetch_cache to disk (best-effort; silent on error)."""
    path = _cache_file_path()
    debug.trace(4, f"_save_cache: writing {len(_fetch_cache)} entries to {path!r}")
    try:
        raw = {}
        for (date_str, age_group), entry in _fetch_cache.items():
            key_str = f"{date_str}|{age_group}"
            img_bytes = entry.get("image_bytes") or b""
            raw[key_str] = {
                "tidbit": entry.get("tidbit", ""),
                "image_bytes": base64.b64encode(img_bytes).decode("ascii"),
                "image_prompt": entry.get("image_prompt", ""),
            }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2)
        debug.trace(3, f"_save_cache: saved {len(raw)} entries")
    except Exception:                    # pylint: disable=broad-exception-caught
        system.print_exception_info("_save_cache")


# Load any previously saved results immediately at module import time
_load_cache()

def _load_local_poe_client():
    """Load the local poe_client ensuring the correct (non-mezcla) version is used.

    Desktop: loads poe_client.py by absolute path so the mezcla poe_client is never
    accidentally imported instead.
    Android: buildozer/p4a compiles .py → .pyc and deploys only the .pyc (no source).
    Python 3 will NOT find a bare poe_client.pyc in a directory via import_module() —
    it expects either a .py source or __pycache__/module.cpython-3XX.pyc layout.
    We therefore look for poe_client.pyc next to main.pyc and load it explicitly via
    spec_from_file_location, which accepts both .py and .pyc paths.

    Key correctness rules:
      - Only register in sys.modules AFTER exec_module succeeds (never before).
      - Validate any cached entry before returning it (hasattr POEClient guard).
      - Pop stale/broken cache entries so retry attempts can succeed.
    """
    # Return cached module only if it was fully initialized
    cached = sys.modules.get("_local_poe_client")
    if cached is not None and hasattr(cached, "POEClient"):
        return cached
    # Remove any stale/broken entry left by a previous failed load attempt
    sys.modules.pop("_local_poe_client", None)

    _app_dir = os.path.dirname(os.path.abspath(__file__))

    def _load_by_path(path):
        """Load module from path (works for both .py and .pyc)."""
        debug.trace(5, f"_load_local_poe_client: loading from {path!r}")
        _spec = importlib.util.spec_from_file_location("_local_poe_client", path)
        _m = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_m)
        sys.modules["_local_poe_client"] = _m
        return _m

    # 1. Desktop path: poe_client.py next to main.py
    _poc_py = os.path.join(_app_dir, "poe_client.py")
    if os.path.exists(_poc_py):
        return _load_by_path(_poc_py)

    # 2. Android path: buildozer deploys poe_client.pyc directly in the app dir
    #    (same directory as main.pyc).  Python 3 import_module() cannot find a
    #    bare .pyc in a directory, so we locate and load it explicitly.
    _poc_pyc = os.path.join(_app_dir, "poe_client.pyc")
    debug.trace(4, f"_load_local_poe_client: .py not found; trying {_poc_pyc!r} "
                f"(exists={os.path.exists(_poc_pyc)})")
    if os.path.exists(_poc_pyc):
        return _load_by_path(_poc_pyc)

    # 3. Last-resort: search __pycache__ for any cpython .pyc variant
    _cache_pattern = os.path.join(_app_dir, "__pycache__", "poe_client.cpython-*.pyc")
    _candidates = sorted(glob.glob(_cache_pattern))
    debug.trace(4, f"_load_local_poe_client: __pycache__ candidates={_candidates!r}")
    if _candidates:
        return _load_by_path(_candidates[-1])

    raise ImportError(
        f"Cannot find poe_client.py or poe_client.pyc in {_app_dir!r}; "
        f"checked: {_poc_py!r}, {_poc_pyc!r}, {_cache_pattern!r}"
    )


def get_random_tidbit(date_str=None, prompt_override=None,
                      prefer_topics=None, exclude_topics=None,
                      age_group=None, language=None):
    """Fetch a random historical tidbit via POE API
    DATE_STR: date like "March 01" (defaults to today)
    PROMPT_OVERRIDE: custom prompt (use {date} placeholder for the date)
    PREFER_TOPICS: comma-separated topics to prefer
    EXCLUDE_TOPICS: comma-separated topics to exclude
    AGE_GROUP: target audience age range (e.g., "3-5", "18+")
    LANGUAGE: language for the response (e.g., "Spanish"); None or "English" = no instruction
    """
    if not date_str:
        date_str = datetime.date.today().strftime("%B %d")
    if prompt_override and prompt_override.strip():
        question = prompt_override.strip()
        if "{date}" in question:
            question = question.replace("{date}", date_str)
    else:
        question = DEFAULT_PROMPT.format(date=date_str)
    if prefer_topics and prefer_topics.strip():
        question += f". Prefer topics related to: {prefer_topics.strip()}"
    if exclude_topics and exclude_topics.strip():
        question += f". Exclude the following topics: {exclude_topics.strip()}"
    if age_group and age_group != "18+":
        question += f". Tailor the content to be appropriate for ages {age_group}."
    # Language injection: ask LLM to respond in the selected language
    if language and language not in ("English", ""):
        question += f" Please respond in {language}."
    debug.trace(4, f"get_random_tidbit: question={question!r}")
    result = ""
    try:
        # Use local poe_client.py (not mezcla's version) to get image-generation support
        poc = _load_local_poe_client()
        client = poc.POEClient(api_key=POE_API, model=POE_MODEL)
        result = client.ask(question)
    except Exception as exc:      # pylint: disable=broad-exception-caught
        result = f"Error: Unable to fetch tidbit for {date_str}: {exc}"
    debug.trace(5, f"get_random_tidbit() => {result!r}")
    return result

def get_tidbit_image(tidbit, image_model=None, age_group=None):
    """Generate an image illustrating TIDBIT via POE image generation.
    Returns (image_bytes, image_prompt); image_bytes is None on failure.
    Uses an LLM call to convert the tidbit into a visual, NSFW-filtered prompt first.
    AGE_GROUP: target audience age range (e.g., "3-5", "18+") for filtering.
    Note: image generation can take 60-90 s; set POE_IMAGE_TIMEOUT env var to adjust.
    """
    image_bytes = None
    image_prompt = ""
    try:
        # Use local poe_client.py (not mezcla's version) to get image-generation support
        poc = _load_local_poe_client()
        client = poc.POEClient(api_key=POE_API, model=POE_MODEL)
        image_prompt = client.generate_image_prompt(tidbit, age_group=age_group)
        debug.trace(4, f"get_tidbit_image: image_prompt={image_prompt!r}")
        image_timeout = getattr(poc, "POE_IMAGE_TIMEOUT", 120)
        debug.trace(4, f"get_tidbit_image: calling generate_image (image_timeout={image_timeout} s)")
        image_bytes = client.generate_image(image_prompt, model=image_model or POE_IMAGE_MODEL)
        debug.trace(4, f"get_tidbit_image: got {len(image_bytes) if image_bytes else 0} bytes")
    except Exception as exc:      # pylint: disable=broad-exception-caught
        debug.trace(3, f"get_tidbit_image: failed: {exc}")
        image_prompt = image_prompt or f"(error: {exc})"
    return image_bytes, image_prompt

def main():
    """Entry point"""
    debug.trace(4, "main()")
    app = QApplication(sys.argv)

    # Create main window widget
    window = QWidget()
    window.setWindowTitle("Random Tidbit")
    window.setMinimumWidth(600)

    # Style
    app.setStyleSheet(_build_app_stylesheet())

    # --- Input fields ---
    date_edit = QDateEdit()
    # Removed setCalendarPopup(True) to fix S23 Ultra crash
    date_edit.setDate(QDate.currentDate())
    date_edit.setDisplayFormat("MMMM dd")
    date_edit.setSelectedSection(QDateEdit.NoSection)
    # Hide the spin buttons (red circle in screenshot)
    date_edit.setButtonSymbols(QDateEdit.NoButtons)
    date_edit.lineEdit().setAlignment(Qt.AlignCenter)

    cal_button = QPushButton()
    cal_button.setIcon(_make_calendar_icon(40))
    cal_button.setIconSize(QSize(34, 34))
    cal_button.setObjectName("cal_button")
    cal_button.setFixedSize(44, 40)

    def open_calendar_dialog():
        """Create calendar for selecting date of tidbit"""
        # Note: month and year can be selected independently,
        # and there is < and > controls for moving backward of forward.
        dlg = QDialog(window)
        dlg.setWindowTitle("Select Date")
        dlg.resize(440, 360)
        cal = QCalendarWidget()
        cal.setGridVisible(True)
        cal.setMinimumSize(400, 290)
        cal.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)
        cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        cal.setStyleSheet(
            f"QCalendarWidget QWidget {{ background-color: {COLOR_CAL_DIALOG_BG}; }}"
            "QCalendarWidget QAbstractItemView:enabled {"
            f" background-color: {COLOR_CAL_DAY_BG}; color: {COLOR_INK_BROWN};"
            f" selection-background-color: {COLOR_CAL_DAY_SELECTION}; selection-color: {COLOR_WHITE}; }}"
        )
        fmt = QTextCharFormat()
        fmt.setForeground(Qt.black)
        cal.setWeekdayTextFormat(Qt.Saturday, fmt)
        cal.setWeekdayTextFormat(Qt.Sunday, fmt)
        cal.setSelectedDate(date_edit.date())
        buttons = QDialogButtonBox()
        buttons.addButton("Choose date", QDialogButtonBox.AcceptRole)
        buttons.addButton("Cancel", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        vbox = QVBoxLayout()
        vbox.addWidget(cal)
        vbox.addWidget(buttons)
        dlg.setLayout(vbox)
        if dlg.exec() == QDialog.Accepted:
            date_edit.setDate(cal.selectedDate())
            date_edit.setSelectedSection(QDateEdit.NoSection)

    cal_button.clicked.connect(open_calendar_dialog)

    # --- Buttons defined here so they can be placed in the header row ---
    fetch_button = QPushButton("Fetch")
    fetch_button.setObjectName("fetch_button")

    image_refresh_button = QPushButton()
    image_refresh_button.setObjectName("image_refresh_button")
    image_refresh_button.setToolTip("Regenerate image only")
    image_refresh_button.setIcon(_make_refresh_icon(28))
    image_refresh_button.setIconSize(QSize(22, 22))
    image_refresh_button.setFixedSize(38, 34)

    quit_button = QPushButton("X")
    quit_button.setObjectName("quit_button")
    quit_button.setFixedSize(26, 26)
    quit_button.setToolTip("Quit")

    prompt_edit = QLineEdit(DEFAULT_PROMPT)

    prefer_edit = QLineEdit()
    prefer_edit.setPlaceholderText("e.g. science, art, sports")

    exclude_edit = QLineEdit()
    exclude_edit.setPlaceholderText("e.g. wars, politics, religion")

    # Age group combobox: controls content and image filtering
    age_combo = QComboBox()
    age_combo.addItems(AGE_GROUPS)
    age_combo.setCurrentIndex(0)      # default: 18+
    _center_combo_text(age_combo)

    # Language combo: injected into the prompt so the LLM responds in that language
    LANGUAGES = [
        "English", "Spanish", "French", "German", "Portuguese",
        "Italian", "Japanese", "Chinese (Simplified)", "Korean",
        "Arabic", "Russian", "Hindi", "Dutch", "Polish", "Swedish",
    ]
    lang_combo = QComboBox()
    lang_combo.addItems(LANGUAGES)
    lang_combo.setCurrentIndex(0)     # default: English
    _center_combo_text(lang_combo)

    # --- Row 1: Date + Age + Language + image refresh + Fetch + quit ---
    date_row = QHBoxLayout()
    date_row.setSpacing(6)
    date_row.addWidget(QLabel("Date:"))
    date_row.addWidget(date_edit, 2)
    date_row.addWidget(cal_button)
    date_row.addSpacing(10)
    date_row.addWidget(QLabel("Age:"))
    date_row.addWidget(age_combo)
    date_row.addSpacing(6)
    date_row.addWidget(QLabel("Lang:"))
    date_row.addWidget(lang_combo)
    date_row.addSpacing(6)
    date_row.addWidget(image_refresh_button)
    date_row.addSpacing(4)
    date_row.addWidget(fetch_button)
    date_row.addSpacing(4)
    date_row.addWidget(quit_button)

    # --- Collapsible "Advanced settings" (prompt/prefer/exclude topics) ---
    adv_widget = QWidget()
    adv_form = QFormLayout(adv_widget)
    adv_form.setContentsMargins(16, 2, 0, 2)
    adv_form.setSpacing(4)
    adv_form.addRow("Prompt:", prompt_edit)
    adv_form.addRow("Prefer topics:", prefer_edit)
    adv_form.addRow("Exclude topics:", exclude_edit)
    adv_widget.setVisible(False)

    def _toggle_section(widget, button, label):
        """Toggle a collapsible section open/closed, updating the button arrow."""
        visible = not widget.isVisible()
        widget.setVisible(visible)
        button.setText(("▼ " if visible else "▶ ") + label)

    adv_toggle = QPushButton("▶ Advanced settings")
    adv_toggle.setObjectName("toggle_button")
    adv_toggle.clicked.connect(
        lambda: _toggle_section(adv_widget, adv_toggle, "Advanced settings"))

    separator = QFrame()
    separator.setFrameShape(QFrame.HLine)
    separator.setFrameShadow(QFrame.Sunken)

    result_text = QTextEdit()
    result_text.setReadOnly(True)
    # Ensure full selectability and copy-paste support
    interaction_flags = (Qt.TextSelectableByMouse |
                         Qt.TextSelectableByKeyboard |
                         Qt.LinksAccessibleByMouse)
    result_text.setTextInteractionFlags(interaction_flags)
    result_text.setPlaceholderText("Press Fetch (or F5) to get a tidbit.")
    result_text.setStyleSheet(
        "QTextEdit { border: none; background-color: transparent; }"
    )

    # Wrap result_text in a card widget for visual consistency
    result_card = QWidget()
    result_card.setObjectName("result_card")
    result_card_layout = QVBoxLayout(result_card)
    result_card_layout.setContentsMargins(6, 6, 6, 6)
    result_card_layout.addWidget(result_text)

    # Image pane (~1/3 width): shows a generated illustration of the tidbit.
    # Wrapped in a card widget (image_card) with a caption label below.
    image_label = QLabel()
    image_label.setAlignment(Qt.AlignCenter)
    image_label.setMinimumWidth(180)
    image_label.setMinimumHeight(160)
    image_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
    image_label.setWordWrap(True)
    image_label.setText("Image will appear\nafter fetch.")
    image_label.setStyleSheet(
        "QLabel { border: none; background-color: transparent;"
        " color: #999; font-size: 12px; }"
    )

    image_caption = QLabel("")
    image_caption.setObjectName("image_caption")
    image_caption.setWordWrap(True)
    image_caption.setAlignment(Qt.AlignTop | Qt.AlignLeft)
    image_caption.setVisible(False)

    image_card = QWidget()
    image_card.setObjectName("image_card")
    image_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
    image_card_layout = QVBoxLayout(image_card)
    image_card_layout.setContentsMargins(4, 4, 4, 4)
    image_card_layout.setSpacing(3)
    image_card_layout.addWidget(image_label)
    image_card_layout.addWidget(image_caption)
    _apply_age_group_presentation("18+", result_text, image_label, image_caption,
                                  result_card, image_card)

    # Stored raw pixmap + resize-event filter so image rescales with the window
    _raw_pixmap = [None]

    def _rescale_image_label():
        """Rescale stored pixmap to current label dimensions, preserving aspect ratio."""
        pix = _raw_pixmap[0]
        if pix is None or pix.isNull():
            return
        w = image_label.width()
        h = image_label.height()
        if w <= 0 or h <= 0:
            return
        scaled = pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(scaled)

    def _set_image_caption(text):
        """Show caption only when there is meaningful text to display."""
        visible = bool(text and text.strip())
        image_caption.setVisible(visible)
        image_caption.setText(text if visible else "")

    class _ImageResizer(QObject):
        def eventFilter(self, watched, event):
            if watched is image_label and event.type() == QEvent.Type.Resize:
                _rescale_image_label()
            return False

    _img_resizer = _ImageResizer(window)
    image_label.installEventFilter(_img_resizer)

    # Debug pane: small monospace pane at the bottom with info/diagnostics
    debug_pane = QTextEdit()
    debug_pane.setObjectName("debug_pane")
    debug_pane.setReadOnly(True)
    debug_pane.setMaximumHeight(90)
    debug_font = QFont("monospace")
    debug_font.setPointSize(8)
    debug_pane.setFont(debug_font)
    debug_pane.setPlaceholderText("Debug info will appear after fetch.")
    debug_pane.setVisible(False)  # hidden by default; toggle with dbg_toggle

    dbg_toggle = QPushButton("▶ Debug")
    dbg_toggle.setObjectName("toggle_button")
    dbg_toggle.clicked.connect(
        lambda: _toggle_section(debug_pane, dbg_toggle, "Debug"))
    age_combo.currentTextChanged.connect(
        lambda value: _apply_age_group_presentation(
            value, result_text, image_label, image_caption, result_card, image_card))

    def _set_debug_info(date_str, tidbit, image_prompt, age_group, extra=""):
        """Populate the debug pane with run details."""
        api_key_display = (POE_API[:8] + "…") if POE_API else "(not set)"
        lines = [
            f"date={date_str}  age_group={age_group}  {extra}",
            f"text_model={POE_MODEL}  image_model={POE_IMAGE_MODEL}",
            f"text_timeout={POE_TIMEOUT}s  image_timeout={POE_IMAGE_TIMEOUT}s",
            f"api_key={api_key_display}",
            f"tidbit_len={len(tidbit)}",
            f"image_prompt: {image_prompt or '(none)'}",
        ]
        if debug.detailed_debugging():
            lines.append(f"{POE_API=}  {POE_MODEL=}")
        debug_pane.setPlainText("\n".join(lines))

    # Worker thread for background fetch (keeps the form visible and responsive)
    class _FetchWorker(QThread):
        """Background thread that fetches the tidbit and optional image."""
        tidbit_ready = Signal(str)
        image_ready = Signal(bytes, str)        # image_bytes, image_prompt
        fetch_done = Signal(str, str, str, str)  # date_str, age_group, image_prompt, note

        def __init__(self, date_str, prompt_text, prefer, exclude, age_group,
                     bypass_cache, language=None, parent=None):
            super().__init__(parent)
            self.date_str = date_str
            self.prompt_text = prompt_text
            self.prefer = prefer
            self.exclude = exclude
            self.age_group = age_group
            self.bypass_cache = bypass_cache
            self.language = language

        def run(self):
            """Fetch tidbit (and image) then emit signals back to the main thread."""
            cache_key = (self.date_str, self.age_group)
            if DISABLE_CACHE_LOOKUP:
                debug.trace(3, "_FetchWorker: cache lookup disabled via DISABLE_CACHE_LOOKUP")
            elif self.bypass_cache:
                debug.trace(4, f"_FetchWorker: bypassing cache for {cache_key!r}")
            elif cache_key in _fetch_cache:
                debug.trace(3, f"_FetchWorker: cache hit for {cache_key!r}")
                entry = _fetch_cache[cache_key]
                self.tidbit_ready.emit(entry["tidbit"])
                if entry["image_bytes"]:
                    self.image_ready.emit(entry["image_bytes"], entry["image_prompt"])
                self.fetch_done.emit(self.date_str, self.age_group,
                                     entry["image_prompt"], "(cached)")
                return
            else:
                debug.trace(3, f"_FetchWorker: cache miss for {cache_key!r}")

            tidbit = get_random_tidbit(
                self.date_str, self.prompt_text,
                self.prefer, self.exclude, self.age_group,
                language=self.language)
            self.tidbit_ready.emit(tidbit)

            image_bytes = b""
            image_prompt = ""
            note = ""
            if SHOW_IMAGE:
                image_bytes_raw, image_prompt = get_tidbit_image(
                    tidbit, age_group=self.age_group)
                image_bytes = image_bytes_raw or b""
                if image_bytes:
                    self.image_ready.emit(image_bytes, image_prompt)
                else:
                    note = "image unavailable"

            _fetch_cache[cache_key] = {
                "tidbit": tidbit,
                "image_bytes": image_bytes,
                "image_prompt": image_prompt,
            }
            _save_cache()
            self.fetch_done.emit(self.date_str, self.age_group, image_prompt, note)

    _worker = [None]  # keeps reference so GC doesn't collect the running thread
    _image_worker = [None]

    class _ImageWorker(QThread):
        """Background thread that regenerates only the image for an existing tidbit."""
        image_ready = Signal(bytes, str)
        image_done = Signal(str, str, str, str)   # date_str, age_group, image_prompt, note

        def __init__(self, date_str, age_group, tidbit, parent=None):
            super().__init__(parent)
            self.date_str = date_str
            self.age_group = age_group
            self.tidbit = tidbit

        def run(self):
            """Regenerate the image while keeping the existing tidbit text."""
            image_bytes_raw, image_prompt = get_tidbit_image(
                self.tidbit, age_group=self.age_group)
            image_bytes = image_bytes_raw or b""
            note = "image refreshed" if image_bytes else "image unavailable"
            if image_bytes:
                self.image_ready.emit(image_bytes, image_prompt)
            cache_key = (self.date_str, self.age_group)
            entry = _fetch_cache.get(cache_key, {"tidbit": self.tidbit})
            entry["tidbit"] = self.tidbit
            entry["image_bytes"] = image_bytes
            entry["image_prompt"] = image_prompt
            _fetch_cache[cache_key] = entry
            _save_cache()
            self.image_done.emit(self.date_str, self.age_group, image_prompt, note)

    def _on_tidbit(tidbit):
        """Slot: update result pane when tidbit arrives."""
        result_text.setPlainText(tidbit)

    def _on_image(image_bytes, image_prompt):
        """Slot: decode and display image when it arrives."""
        magic = image_bytes[:8] if image_bytes else b""
        debug.trace(3, f"_on_image: received {len(image_bytes)} bytes magic={magic!r}")
        pixmap = QPixmap()
        ok = pixmap.loadFromData(image_bytes)
        debug.trace(3, f"_on_image: loadFromData ok={ok} isNull={pixmap.isNull()}")
        if not pixmap.isNull():
            _raw_pixmap[0] = pixmap
            _rescale_image_label()
            image_label.setText("")
            # Show caption only if image came from Wikipedia (prompt prefix used as hint)
            _set_image_caption("")
        else:
            image_label.setText("Image decode\nfailed.")
            _set_image_caption(image_prompt[:120] if image_prompt else "")

    def _on_fetch_done(date_str, age_group, image_prompt, note):
        """Slot: called when the worker finishes; updates debug pane."""
        tidbit = result_text.toPlainText()
        _set_debug_info(date_str, tidbit, image_prompt, age_group, extra=note)
        fetch_button.setEnabled(True)
        image_refresh_button.setEnabled(True)

    def _on_image_refresh_done(date_str, age_group, image_prompt, note):
        """Slot: called when an image-only regeneration finishes."""
        tidbit = result_text.toPlainText()
        _set_debug_info(date_str, tidbit, image_prompt, age_group, extra=note)
        image_refresh_button.setEnabled(True)

    def _on_image_unavailable():
        """Slot: show placeholder text when no image was returned."""
        if _raw_pixmap[0] is None:
            image_label.setText("No image.\n(timeout or API error)")
            debug.trace(3, "_on_image_unavailable: image not received — likely a timeout; "
                        "set POE_IMAGE_TIMEOUT env var to increase (default 120 s)")
            # Retrieve prompt from debug pane as fallback display
            cached_prompt = ""
            for line in debug_pane.toPlainText().splitlines():
                if line.startswith("image_prompt:"):
                    cached_prompt = line[len("image_prompt:"):].strip()
                    break
            _set_image_caption(cached_prompt[:160] if cached_prompt else "(image unavailable)")

    def on_fetch(bypass_cache=True):
        """Start a background worker to fetch tidbit and image for the current date."""
        if ((_worker[0] and _worker[0].isRunning()) or
                (_image_worker[0] and _image_worker[0].isRunning())):
            debug.trace(3, "on_fetch: previous fetch still in progress, skipping")
            return
        result_text.setPlainText("Fetching…")
        image_label.setText("Generating image…")
        image_label.setPixmap(QPixmap())
        image_caption.setText("")
        _raw_pixmap[0] = None
        debug_pane.setPlainText("Fetching tidbit…")
        fetch_button.setEnabled(False)
        image_refresh_button.setEnabled(False)

        date_str = date_edit.date().toString("MMMM dd")
        age_group = age_combo.currentText()
        language = lang_combo.currentText()
        worker = _FetchWorker(
            date_str, prompt_edit.text(),
            prefer_edit.text(), exclude_edit.text(),
            age_group, bypass_cache, language=language, parent=window)
        worker.tidbit_ready.connect(_on_tidbit)
        worker.image_ready.connect(_on_image)
        worker.fetch_done.connect(_on_fetch_done)
        # Show placeholder if image slot never fired
        worker.fetch_done.connect(lambda *_: _on_image_unavailable())
        _worker[0] = worker
        worker.start()

    def on_regenerate_image():
        """Regenerate just the image for the currently displayed tidbit."""
        if ((_worker[0] and _worker[0].isRunning()) or
                (_image_worker[0] and _image_worker[0].isRunning())):
            debug.trace(3, "on_regenerate_image: worker already running, skipping")
            return
        tidbit = result_text.toPlainText().strip()
        if not tidbit or tidbit.startswith("Fetching"):
            debug.trace(3, "on_regenerate_image: no stable tidbit available yet")
            return
        image_label.setText("Generating image…")
        image_label.setPixmap(QPixmap())
        _set_image_caption("")
        _raw_pixmap[0] = None
        image_refresh_button.setEnabled(False)
        debug_pane.setPlainText("Regenerating image…")
        date_str = date_edit.date().toString("MMMM dd")
        age_group = age_combo.currentText()
        worker = _ImageWorker(date_str, age_group, tidbit, parent=window)
        worker.image_ready.connect(_on_image)
        worker.image_done.connect(_on_image_refresh_done)
        worker.image_done.connect(lambda *_: _on_image_unavailable())
        _image_worker[0] = worker
        worker.start()

    fetch_button.clicked.connect(lambda: on_fetch(bypass_cache=True))
    image_refresh_button.clicked.connect(on_regenerate_image)
    quit_button.clicked.connect(app.quit)

    # F5 shortcut to trigger fetch (natural keyboard shortcut for "refresh")
    _f5 = QShortcut(QKeySequence("F5"), window)
    _f5.activated.connect(lambda: on_fetch(bypass_cache=True))

    # Content area: stacked in portrait mode, side-by-side in landscape.
    content_row = QBoxLayout(QBoxLayout.LeftToRight)
    content_row.addWidget(result_card, 2)
    content_row.addWidget(image_card, 1)
    content_row.setAlignment(image_card, Qt.AlignTop)

    def _update_content_layout():
        """Update content orientation from the current window aspect ratio."""
        _apply_content_layout_orientation(content_row, window.width(), window.height())

    class _WindowLayoutAdapter(QObject):
        def eventFilter(self, watched, event):
            if watched is window and event.type() == QEvent.Type.Resize:
                _update_content_layout()
            return False

    _layout_adapter = _WindowLayoutAdapter(window)
    window.installEventFilter(_layout_adapter)

    layout = QVBoxLayout()
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)
    layout.addLayout(date_row)
    layout.addWidget(adv_toggle)
    layout.addWidget(adv_widget)
    layout.addWidget(separator)
    layout.addLayout(content_row, 1)
    layout.addWidget(dbg_toggle)
    layout.addWidget(debug_pane)
    window.setLayout(layout)
    _update_content_layout()

    window.show()

    # Fix Qt quirk: ensure no initial highlighting in the date field
    date_edit.lineEdit().deselect()
    fetch_button.setFocus()
    
    # Trigger initial fetch after a short delay so the form is fully rendered first.
    # bypass_cache=False: use cached result if available for same date+age_group.
    QTimer.singleShot(300, lambda: on_fetch(bypass_cache=False))
    sys.exit(app.exec())

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    main()
