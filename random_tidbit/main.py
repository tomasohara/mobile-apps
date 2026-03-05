#! /usr/bin/env python
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

"""Displays random historical tidbit"""

import datetime
import sys
from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QCalendarWidget, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget)
from mezcla import poe_client, system

DEFAULT_PROMPT = "Give some random bit of history for {date}--one entry"

# --- Inline POE client (avoids mezcla dependency to reduce APK size) ---

POE_API = system.getenv_value(
    ## TODO1: get from vault
    "POE_API", "Gek9rnD3phMdVY5xM2JCTAKaMYHWR8B6oVt70-jGnc0",
    desc="Platform for Open Exploration (POE)")
POE_MODEL = system.getenv_text(
    "POE_MODEL", "GPT-5-mini",
    desc="LLM model for POE")
POE_TIMEOUT = system.getenv_float(
    "POE_TIMEOUT", 30.0,
    desc="Timeout in seconds")


def get_random_tidbit(date_str=None, prompt_override=None,
                      prefer_topics=None, exclude_topics=None):
    """Fetch a random historical tidbit via POE API
    DATE_STR: date like "March 01" (defaults to today)
    PROMPT_OVERRIDE: custom prompt (use {date} placeholder for the date)
    PREFER_TOPICS: comma-separated topics to prefer
    EXCLUDE_TOPICS: comma-separated topics to exclude
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
    result = ""
    try:
        client = poe_client.POEClient(api_key=POE_API, model=POE_MODEL)
        result = client.ask(question)
    except Exception as exc:
        result = f"Unable to fetch tidbit for {date_str}: {exc}"
    return result

def main():
    """Entry point"""
    app = QApplication(sys.argv)

    # Create main window widget
    window = QWidget()
    window.setWindowTitle("Random Tidbit")
    window.setMinimumWidth(600)

    # Style
    app.setStyleSheet("""
        QWidget {
            background-color: #f7f9fc;
            font-family: sans-serif;
            font-size: 16px;
        }
        QLineEdit, QDateEdit, QTextEdit {
            background-color: #ffffff;
            border: 1px solid #dcdfe6;
            border-radius: 8px;
            padding: 8px;
        }
        QPushButton {
            background-color: #608eb5;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: bold;
        }
        #quit_button {
            background-color: #c27c7c;
        }
        #cal_button {
            background-color: transparent;
            border: none;
            font-size: 32px;
            padding: 0px;
        }
        .suggestion {
            color: #999999;
            font-size: 13px;
            font-style: italic;
        }
        QDateEdit::up-button, QDateEdit::down-button {
            width: 0px;
            height: 0px;
            border: none;
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

    cal_button = QPushButton("📅")
    cal_button.setObjectName("cal_button")
    cal_button.setFixedWidth(48)

    def open_calendar_dialog():
        dlg = QDialog(window)
        dlg.setWindowTitle("Select Date")
        cal = QCalendarWidget()
        cal.setSelectedDate(date_edit.date())
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
    prefer_sugg = QLabel("e.g. science, art, sports")
    prefer_sugg.setProperty("class", "suggestion")

    exclude_edit = QLineEdit()
    exclude_edit.setPlaceholderText("e.g. wars, politics, religion")
    exclude_sugg = QLabel("e.g. wars, politics, religion")
    exclude_sugg.setProperty("class", "suggestion")

    form_layout = QFormLayout()
    form_layout.addRow("Date:", date_row)
    form_layout.addRow("Prompt:", prompt_edit)

    # Add Prefer Topics with suggestion
    prefer_vbox = QVBoxLayout()
    prefer_vbox.addWidget(prefer_edit)
    prefer_vbox.addWidget(prefer_sugg)
    form_layout.addRow("Prefer topics:", prefer_vbox)

    # Add Exclude Topics with suggestion
    exclude_vbox = QVBoxLayout()
    exclude_vbox.addWidget(exclude_edit)
    exclude_vbox.addWidget(exclude_sugg)
    form_layout.addRow("Exclude topics:", exclude_vbox)

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
    result_text.setPlaceholderText("Press Fetch to get a tidbit.")

    fetch_button = QPushButton("Fetch Tidbit")
    quit_button = QPushButton("Quit")
    quit_button.setObjectName("quit_button")

    def on_fetch():
        result_text.setPlainText("Fetching...")
        app.processEvents()
        date_str = date_edit.date().toString("MMMM dd")
        tidbit = get_random_tidbit(date_str, prompt_edit.text(),
                                   prefer_edit.text(), exclude_edit.text())
        result_text.setPlainText(tidbit)

    fetch_button.clicked.connect(on_fetch)
    quit_button.clicked.connect(app.quit)

    button_row = QHBoxLayout()
    button_row.addWidget(fetch_button)
    button_row.addWidget(quit_button)

    layout = QVBoxLayout()
    layout.addLayout(form_layout)
    layout.addWidget(separator)
    layout.addWidget(result_text, 1)
    layout.addLayout(button_row)
    window.setLayout(layout)

    window.show()
    # Fix Qt quirk: ensure no initial highlighting in the date field
    date_edit.lineEdit().deselect()
    fetch_button.setFocus()
    # Trigger initial fetch after the event loop starts, ensuring window is visible
    QTimer.singleShot(0, on_fetch)
    sys.exit(app.exec())

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    main()
