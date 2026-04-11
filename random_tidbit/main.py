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
from PySide6.QtCore import QDate, QEvent, QObject, Qt, QThread, QTimer, QRect
from PySide6.QtGui import QFont, QIcon, QKeySequence, QPainter, QColor, QPixmap, QShortcut, QTextCharFormat
from PySide6.QtWidgets import (
    QApplication, QCalendarWidget, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
    QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit,
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
    desc="Timeout in seconds",
    skip_register=True)
POE_IMAGE_MODEL = system.getenv_text(
    "POE_IMAGE_MODEL", "FLUX-schnell",
    desc="Image generation model for POE",
    skip_register=True)
SHOW_IMAGE = system.getenv_bool(
    "SHOW_IMAGE", True,
    desc="Whether to generate and show an image alongside the tidbit",
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
                      prefer_topics=None, exclude_topics=None, age_group=None):
    """Fetch a random historical tidbit via POE API
    DATE_STR: date like "March 01" (defaults to today)
    PROMPT_OVERRIDE: custom prompt (use {date} placeholder for the date)
    PREFER_TOPICS: comma-separated topics to prefer
    EXCLUDE_TOPICS: comma-separated topics to exclude
    AGE_GROUP: target audience age range (e.g., "3-5", "18+")
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
    """
    image_bytes = None
    image_prompt = ""
    try:
        # Use local poe_client.py (not mezcla's version) to get image-generation support
        poc = _load_local_poe_client()
        client = poc.POEClient(api_key=POE_API, model=POE_MODEL)
        image_prompt = client.generate_image_prompt(tidbit, age_group=age_group)
        debug.trace(4, f"get_tidbit_image: image_prompt={image_prompt!r}")
        image_bytes = client.generate_image(image_prompt, model=image_model or POE_IMAGE_MODEL)
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
    app.setStyleSheet("""
        QWidget {
            background-color: #f4f6f9;
            color: #2d3748;
            font-family: sans-serif;
            font-size: 13px;
        }
        QLineEdit, QDateEdit, QComboBox, QTextEdit {
            background-color: #ffffff;
            border: 1px solid #d2d8e3;
            border-radius: 6px;
            padding: 5px 8px;
        }
        QComboBox::drop-down { border: none; }
        QPushButton {
            background-color: #4a7fa8;
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 6px 14px;
            font-weight: bold;
            font-size: 13px;
        }
        QPushButton:disabled {
            background-color: #a0b8cc;
        }
        QPushButton:hover:!disabled {
            background-color: #3a6f98;
        }
        #quit_button {
            background-color: #4a8c5c;
        }
        #quit_button:hover {
            background-color: #3a7c4c;
        }
        #cal_button {
            background-color: transparent;
            border: none;
            font-size: 22px;
            padding: 0px;
        }
        QDateEdit::up-button, QDateEdit::down-button {
            width: 0px;
            height: 0px;
            border: none;
        }
        #result_card {
            background-color: #ffffff;
            border: 1px solid #d2d8e3;
            border-radius: 8px;
        }
        #image_card {
            background-color: #ffffff;
            border: 1px solid #d2d8e3;
            border-radius: 8px;
        }
        #image_caption {
            color: #7a8898;
            font-size: 10px;
            font-style: italic;
            padding: 4px 6px;
        }
        #debug_pane {
            background-color: #1a1b2e;
            color: #8a9bb0;
            border: none;
            border-radius: 0px;
            padding: 4px;
            font-family: monospace;
            font-size: 9px;
        }
    """)

    # --- Input fields ---
    date_edit = QDateEdit()
    # Removed setCalendarPopup(True) to fix S23 Ultra crash
    date_edit.setDate(QDate.currentDate())
    date_edit.setDisplayFormat("MMMM dd")
    date_edit.setSelectedSection(QDateEdit.NoSection)
    # Hide the spin buttons (red circle in screenshot)
    date_edit.setButtonSymbols(QDateEdit.NoButtons)

    def _make_calendar_icon(size: int = 32) -> QIcon:
        """Draw a monthly-grid calendar icon (5-col × 6-row day cells + header bar).

        No day number is shown — the grid pattern evokes a monthly view without
        the cognitive dissonance of a large prominent date digit.
        """
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)

        bg        = QColor("#4CAF50")   # green body (matches app theme)
        header    = QColor("#2E7D32")   # darker green header strip
        cell_line = QColor("#A5D6A7")   # light green grid lines
        cell_bg   = QColor("#FFFFFF")   # white day cells
        ring      = QColor("#1B5E20")   # dark ring/border

        # Outer rounded rectangle (calendar body)
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)

        # Header bar (top ~25 %)
        header_h = max(6, size // 4)
        p.setBrush(header)
        p.drawRoundedRect(1, 1, size - 2, header_h + 2, 3, 3)
        p.setBrush(bg)
        p.drawRect(1, header_h // 2, size - 2, header_h)  # flatten bottom of header

        # Two binding rings on the header
        p.setBrush(ring)
        ring_r = max(2, size // 12)
        for rx in (size // 3, size * 2 // 3):
            p.drawEllipse(rx - ring_r, 0, ring_r * 2, ring_r * 2 + 2)

        # Day-cell grid: 5 columns × 6 rows
        cols, rows = 5, 6
        pad = max(2, size // 16)
        grid_x = pad
        grid_y = header_h + pad
        grid_w = size - 2 * pad
        grid_h = size - grid_y - pad
        cell_w = grid_w / cols
        cell_h = grid_h / rows
        p.setBrush(cell_bg)
        p.setPen(cell_line)
        for r in range(rows):
            for c in range(cols):
                cx = int(grid_x + c * cell_w) + 1
                cy = int(grid_y + r * cell_h) + 1
                cw = max(1, int(cell_w) - 2)
                ch = max(1, int(cell_h) - 2)
                p.drawRect(cx, cy, cw, ch)

        p.end()
        return QIcon(pix)

    cal_button = QPushButton()
    cal_button.setIcon(_make_calendar_icon(32))
    cal_button.setIconSize(cal_button.sizeHint())
    cal_button.setObjectName("cal_button")
    cal_button.setFixedWidth(48)

    def open_calendar_dialog():
        """Create calendar for selecting date of tidbit"""
        # Note: month and year can be selected independently,
        # and there is < and > controls for moving backward of forward.
        dlg = QDialog(window)
        dlg.setWindowTitle("Select Date")
        cal = QCalendarWidget()
        cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        fmt = QTextCharFormat()
        fmt.setForeground(Qt.black)
        cal.setWeekdayTextFormat(Qt.Saturday, fmt)
        cal.setWeekdayTextFormat(Qt.Sunday, fmt)
        cal.setSelectedDate(date_edit.date())
        buttons = QDialogButtonBox()
        buttons.addButton("OK", QDialogButtonBox.AcceptRole)
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

    date_row = QHBoxLayout()
    date_row.addWidget(date_edit, 1)
    date_row.addWidget(cal_button)

    prompt_edit = QLineEdit(DEFAULT_PROMPT)

    prefer_edit = QLineEdit()
    prefer_edit.setPlaceholderText("e.g. science, art, sports")

    exclude_edit = QLineEdit()
    exclude_edit.setPlaceholderText("e.g. wars, politics, religion")

    form_layout = QFormLayout()
    form_layout.addRow("Date:", date_row)
    form_layout.addRow("Prompt:", prompt_edit)

    # Add Prefer Topics with suggestion
    form_layout.addRow("Prefer topics:", prefer_edit)

    # Add Exclude Topics with suggestion
    form_layout.addRow("Exclude topics:", exclude_edit)

    # Age group combobox: controls content and image filtering
    AGE_GROUPS = ["18+", "14-18", "9-14", "6-9", "3-5"]
    age_combo = QComboBox()
    age_combo.addItems(AGE_GROUPS)
    age_combo.setCurrentIndex(0)      # default: 18+
    form_layout.addRow("Age group:", age_combo)

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

    image_card = QWidget()
    image_card.setObjectName("image_card")
    image_card_layout = QVBoxLayout(image_card)
    image_card_layout.setContentsMargins(4, 4, 4, 4)
    image_card_layout.setSpacing(3)
    image_card_layout.addWidget(image_label, 1)
    image_card_layout.addWidget(image_caption)

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

    fetch_button = QPushButton("Fetch Tidbit")
    quit_button = QPushButton("Quit")
    quit_button.setObjectName("quit_button")

    def _set_debug_info(date_str, tidbit, image_prompt, age_group, extra=""):
        """Populate the debug pane with run details."""
        api_key_display = (POE_API[:8] + "…") if POE_API else "(not set)"
        lines = [
            f"date={date_str}  age_group={age_group}  {extra}",
            f"text_model={POE_MODEL}  image_model={POE_IMAGE_MODEL}",
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
                     bypass_cache, parent=None):
            super().__init__(parent)
            self.date_str = date_str
            self.prompt_text = prompt_text
            self.prefer = prefer
            self.exclude = exclude
            self.age_group = age_group
            self.bypass_cache = bypass_cache

        def run(self):
            """Fetch tidbit (and image) then emit signals back to the main thread."""
            cache_key = (self.date_str, self.age_group)
            if not self.bypass_cache and cache_key in _fetch_cache:
                entry = _fetch_cache[cache_key]
                self.tidbit_ready.emit(entry["tidbit"])
                if entry["image_bytes"]:
                    self.image_ready.emit(entry["image_bytes"], entry["image_prompt"])
                self.fetch_done.emit(self.date_str, self.age_group,
                                     entry["image_prompt"], "(cached)")
                return

            tidbit = get_random_tidbit(
                self.date_str, self.prompt_text,
                self.prefer, self.exclude, self.age_group)
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
            image_caption.setText("")
        else:
            image_label.setText("Image decode\nfailed.")
            image_caption.setText(image_prompt[:120] if image_prompt else "")

    def _on_fetch_done(date_str, age_group, image_prompt, note):
        """Slot: called when the worker finishes; updates debug pane."""
        tidbit = result_text.toPlainText()
        _set_debug_info(date_str, tidbit, image_prompt, age_group, extra=note)
        fetch_button.setEnabled(True)

    def _on_image_unavailable():
        """Slot: show placeholder text when no image was returned."""
        if _raw_pixmap[0] is None:
            image_label.setText("No image.")
            # Retrieve prompt from debug pane as fallback display
            cached_prompt = ""
            for line in debug_pane.toPlainText().splitlines():
                if line.startswith("image_prompt:"):
                    cached_prompt = line[len("image_prompt:"):].strip()
                    break
            image_caption.setText(cached_prompt[:160] if cached_prompt else "(image unavailable)")

    def on_fetch(bypass_cache=True):
        """Start a background worker to fetch tidbit and image for the current date."""
        if _worker[0] and _worker[0].isRunning():
            debug.trace(3, "on_fetch: previous fetch still in progress, skipping")
            return
        result_text.setPlainText("Fetching…")
        image_label.setText("Generating image…")
        image_label.setPixmap(QPixmap())
        image_caption.setText("")
        _raw_pixmap[0] = None
        debug_pane.setPlainText("Fetching tidbit…")
        fetch_button.setEnabled(False)

        date_str = date_edit.date().toString("MMMM dd")
        age_group = age_combo.currentText()
        worker = _FetchWorker(
            date_str, prompt_edit.text(),
            prefer_edit.text(), exclude_edit.text(),
            age_group, bypass_cache, parent=window)
        worker.tidbit_ready.connect(_on_tidbit)
        worker.image_ready.connect(_on_image)
        worker.fetch_done.connect(_on_fetch_done)
        # Show placeholder if image slot never fired
        worker.fetch_done.connect(lambda *_: _on_image_unavailable())
        _worker[0] = worker
        worker.start()

    fetch_button.clicked.connect(lambda: on_fetch(bypass_cache=True))
    quit_button.clicked.connect(app.quit)

    # F5 shortcut to trigger fetch (natural keyboard shortcut for "refresh")
    _f5 = QShortcut(QKeySequence("F5"), window)
    _f5.activated.connect(lambda: on_fetch(bypass_cache=True))

    button_row = QHBoxLayout()
    button_row.addWidget(fetch_button)
    button_row.addWidget(quit_button)

    # Content row: text card (2/3) + image card (1/3)
    content_row = QHBoxLayout()
    content_row.addWidget(result_card, 2)
    content_row.addWidget(image_card, 1)

    layout = QVBoxLayout()
    layout.addLayout(form_layout)
    layout.addWidget(separator)
    layout.addLayout(content_row, 1)
    layout.addLayout(button_row)
    layout.addWidget(debug_pane)
    window.setLayout(layout)

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
