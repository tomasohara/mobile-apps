#! /usr/bin/env python
#
# note:
# - base class for creating menus (BaseMenuWidget)
# - developed via Gemini
#

"""Core menu widget components and shared styling."""

# pylint: disable=cyclic-import

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QStackedWidget, QVBoxLayout, QWidget
)

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
BG     = "#0f0f1a"
PANEL  = "#1a1a2e"
CARD   = "#16213e"
DEEP   = "#0f3460"
RED    = "#e94560"
GREEN  = "#4ade80"
BLUE   = "#38bdf8"
YELLOW = "#facc15"
PURPLE = "#a78bfa"
TEXT   = "#e2e8f0"
MUTED  = "#94a3b8"
TOKEN_COLORS = [RED, "#f97316", YELLOW, GREEN, BLUE, PURPLE, "#f472b6", "#34d399"]

# ---------------------------------------------------------------------------
# Global stylesheet
# ---------------------------------------------------------------------------
APP_STYLE = f"""
QWidget            {{ background-color:{BG}; color:{TEXT}; font-size:13px; }}
QTabWidget::pane   {{ border:1px solid {PANEL}; background:{PANEL}; }}
QTabBar::tab       {{ background:{CARD}; color:{MUTED}; padding:8px 10px;
                      border:none; min-width:55px; }}
QTabBar::tab:selected {{ background:{DEEP}; color:{RED}; font-weight:bold; }}
QLineEdit, QTextEdit {{ background:{CARD}; color:{TEXT};
                        border:1px solid {DEEP}; border-radius:6px; padding:6px; }}
QPushButton        {{ background:{RED}; color:white; border:none;
                      border-radius:6px; padding:8px 14px; font-weight:bold; }}
QPushButton:hover  {{ background:#c73652; }}
QPushButton:disabled {{ background:#3a3a4a; color:{MUTED}; }}
QPushButton#alt    {{ background:{DEEP}; }}
QPushButton#alt:hover {{ background:#1a4a80; }}
QPushButton#ok     {{ background:#16a34a; }}
QPushButton#ok:hover  {{ background:#15803d; }}
QProgressBar       {{ background:{CARD}; border:1px solid {DEEP};
                      border-radius:4px; height:22px; text-align:center; color:{TEXT}; }}
QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 {RED},stop:1 {BLUE}); border-radius:3px; }}
QListWidget        {{ background:{CARD}; border:1px solid {DEEP}; border-radius:6px; }}
QListWidget::item  {{ padding:6px; }}
QListWidget::item:selected {{ background:{DEEP}; color:{BLUE}; }}
QScrollBar:vertical {{ background:{CARD}; width:8px; border-radius:4px; }}
QScrollBar::handle:vertical {{ background:{DEEP}; border-radius:4px; min-height:20px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QComboBox          {{ background:{CARD}; color:{TEXT}; border:1px solid {DEEP};
                      border-radius:6px; padding:6px; }}
QComboBox::drop-down {{ border:none; }}
"""

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _title(text, color=RED):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{color}; font-size:15px; font-weight:bold; padding:2px 0;")
    return lbl


def _hint(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{MUTED}; font-size:11px;")
    lbl.setWordWrap(True)
    return lbl


def _sep():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"background:{DEEP}; max-height:1px; margin:4px 0;")
    return f


# ===========================================================================
# Feature tab factory
# ===========================================================================

class BaseMenuWidget(QWidget):
    """Abstract base class for launcher-style feature menus."""

    def __init__(self, title, description, feature_list):
        super().__init__()
        self._buttons = []
        self._stack = QStackedWidget()
        self._grid = QGridLayout()
        self._grid_columns = 0
        self._is_fullscreen = False

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        self._header_widget = QWidget()
        header_layout = QVBoxLayout(self._header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_row = QHBoxLayout()
        title_row.addWidget(_title(title))
        self._fullscreen_btn = QPushButton("⛶ Full Screen")
        self._fullscreen_btn.setCheckable(True)
        self._fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        title_row.addWidget(self._fullscreen_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        header_layout.addLayout(title_row)
        header_layout.addWidget(_hint(description))
        header_layout.addWidget(_sep())
        
        self._grid_widget = QWidget()
        self._grid_widget.setLayout(self._grid)
        header_layout.addWidget(self._grid_widget)
        
        layout.addWidget(self._header_widget)

        self._grid.setSpacing(8)

        for index, (tab_name, widget) in enumerate(feature_list):
            btn = QPushButton(tab_name)
            btn.setCheckable(True)
            btn.setMinimumHeight(54)
            btn.clicked.connect(lambda checked=False, i=index: self._show_feature(i))
            self._buttons.append(btn)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(widget)
            scroll.setStyleSheet("QScrollArea { border: none; }")
            self._stack.addWidget(scroll)

        layout.addWidget(self._stack, 1)
        self._update_grid_layout()
        self._show_feature(0)

    def _toggle_fullscreen(self):
        self._is_fullscreen = not self._is_fullscreen
        if self._is_fullscreen:
            self._grid_widget.hide()
            self._fullscreen_btn.setText("🗗 Exit Full Screen")
        else:
            self._grid_widget.show()
            self._fullscreen_btn.setText("⛶ Full Screen")

    def _show_feature(self, index):
        self._stack.setCurrentIndex(index)
        for btn_index, button in enumerate(self._buttons):
            button.setChecked(btn_index == index)
            if btn_index == index:
                button.setStyleSheet(
                    f"background:{DEEP}; color:{BLUE}; border:1px solid {BLUE}; "
                    "border-radius:6px; padding:8px 14px; font-weight:bold;"
                )
            else:
                button.setStyleSheet("")

    def _update_grid_layout(self):
        landscape = (self.width() >= self.height())
        columns = 5 if landscape else 2
        if columns == self._grid_columns:
            return

        self._grid_columns = columns
        for index, button in enumerate(self._buttons):
            row = index // columns
            column = index % columns
            self._grid.addWidget(button, row, column)

        for column in range(5):
            self._grid.setColumnStretch(column, 1 if column < columns else 0)

        rows = (len(self._buttons) + columns - 1) // columns
        for row in range(5):
            self._grid.setRowStretch(row, 1 if row < rows else 0)

    def showEvent(self, event):
        super().showEvent(event)
        self._update_grid_layout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_grid_layout()


def create_ai_mobile_lab_menu():
    """Return an instance of the AI Mobile Lab menu."""
    import ai_feature_stubs  # pylint: disable=import-outside-toplevel
    return ai_feature_stubs.AIMobileLabMenu()

def create_smartphone_features_menu():
    """Return an instance of the Smartphone Features menu."""
    import handheld_feature_stubs  # pylint: disable=import-outside-toplevel
    return handheld_feature_stubs.SmartphoneFeaturesMenu()
