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
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (QApplication, QCalendarWidget, QDateEdit,
                                QDialog, QDialogButtonBox, QFormLayout,
                                QFrame, QHBoxLayout, QLabel, QLineEdit,
                                QPushButton, QVBoxLayout, QWidget)
import os
import requests

DEFAULT_PROMPT = "Give some random bit of history for {date}--one entry"

# --- Inline POE client (avoids mezcla dependency to reduce APK size) ---

POE_API_KEY = os.environ.get(
    "POE_API", "Gek9rnD3phMdVY5xM2JCTAKaMYHWR8B6oVt70-jGnc0")
POE_URL = os.environ.get("POE_URL", "https://api.poe.com/v1")
POE_MODEL = os.environ.get("POE_MODEL", "GPT-5-mini")
POE_TIMEOUT = float(os.environ.get("POE_TIMEOUT", "30"))


def poe_ask(question, model=None, api_key=None):
    """Send a question to the POE API and return the response text"""
    url = f"{POE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key or POE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or POE_MODEL,
        "messages": [{"role": "user", "content": question}],
        "temperature": 0.7,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=POE_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return data.get("output", str(data))

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
    try:
        result = poe_ask(question)
    except Exception as exc:
        result = f"Error fetching tidbit: {exc}"
    return result

def main():
    """Entry point"""
    app = QApplication(sys.argv)

    # Create main window widget
    window = QWidget()
    window.setWindowTitle("Random Tidbit")
    window.setMinimumWidth(600)

    # --- Input fields ---
    date_edit = QDateEdit()
    date_edit.setCalendarPopup(True)
    date_edit.setDate(QDate.currentDate())
    date_edit.setDisplayFormat("MMMM dd")

    # Calendar button as fallback (Android doesn't support calendar popup)
    cal_button = QPushButton("📅")
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
    form_layout.setHorizontalSpacing(12)
    form_layout.setVerticalSpacing(10)
    form_layout.addRow("Date:", date_row)
    form_layout.addRow("Prompt:", prompt_edit)
    form_layout.addRow("Prefer topics:", prefer_edit)
    form_layout.addRow("Exclude topics:", exclude_edit)

    # --- Result label (with visible separator) ---
    separator = QFrame()
    separator.setFrameShape(QFrame.HLine)
    separator.setFrameShadow(QFrame.Sunken)

    result_label = QLabel("Press Fetch to get a tidbit.")
    result_label.setWordWrap(True)
    result_label.setContentsMargins(4, 4, 4, 4)

    # --- Buttons ---
    fetch_button = QPushButton("Fetch Tidbit")
    quit_button = QPushButton("Quit")

    def on_fetch():
        """Read fields, fetch tidbit, and update the label"""
        result_label.setText("Fetching...")
        app.processEvents()
        date_str = date_edit.date().toString("MMMM dd")
        prompt = prompt_edit.text()
        prefers = prefer_edit.text()
        excludes = exclude_edit.text()
        tidbit = get_random_tidbit(date_str, prompt, prefers, excludes)
        result_label.setText(tidbit)

    fetch_button.clicked.connect(on_fetch)
    quit_button.clicked.connect(app.quit)

    button_row = QHBoxLayout()
    button_row.addWidget(fetch_button)
    button_row.addWidget(quit_button)

    # --- Main layout ---
    layout = QVBoxLayout()
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)
    layout.addLayout(form_layout)
    layout.addWidget(separator)
    layout.addWidget(result_label, 1)
    layout.addLayout(button_row)
    window.setLayout(layout)

    # Start app and then exit when done
    window.show()
    on_fetch()
    sys.exit(app.exec())

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    main()
