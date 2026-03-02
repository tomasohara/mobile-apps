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
from PySide6.QtWidgets import (QApplication, QDateEdit, QFormLayout, QFrame,
                                QHBoxLayout, QLabel, QLineEdit, QPushButton,
                                QVBoxLayout, QWidget)
from mezcla import debug, poe_client, system

DEFAULT_PROMPT = "Give some random bit of history for {date}--one entry"

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
    # Build the prompt
    if prompt_override and prompt_override.strip():
        question = prompt_override.strip()
        if "{date}" in question:
            question = question.replace("{date}", date_str)
    else:
        question = DEFAULT_PROMPT.format(date=date_str)
    # Append preferred topics if provided
    if prefer_topics and prefer_topics.strip():
        question += f". Prefer topics related to: {prefer_topics.strip()}"
    # Append exclusions if provided
    if exclude_topics and exclude_topics.strip():
        question += f". Exclude the following topics: {exclude_topics.strip()}"
    debug.trace(4, f"get_random_tidbit: question={question!r}")
    try:
        ## TODO1: get from vault
        POE_API = "Gek9rnD3phMdVY5xM2JCTAKaMYHWR8B6oVt70-jGnc0"
        client = poe_client.POEClient(api_key=POE_API, model="GPT-5-mini")
        result = client.ask(question)
    except Exception as exc:
        debug.trace(3, f"Error fetching tidbit: {exc}")
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

    prompt_edit = QLineEdit(DEFAULT_PROMPT)

    prefer_edit = QLineEdit()
    prefer_edit.setPlaceholderText("e.g. science, art, sports")

    exclude_edit = QLineEdit()
    exclude_edit.setPlaceholderText("e.g. wars, politics, religion")

    form_layout = QFormLayout()
    form_layout.setHorizontalSpacing(12)
    form_layout.setVerticalSpacing(10)
    form_layout.addRow("Date:", date_edit)
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
        app.processEvents()     # pylint: disable=no-member
        date_str = date_edit.date().toString("MMMM dd")
        prompt = prompt_edit.text()
        prefers = prefer_edit.text()
        excludes = exclude_edit.text()
        tidbit = get_random_tidbit(date_str, prompt, prefers, excludes)
        result_label.setText(tidbit)

    fetch_button.clicked.connect(on_fetch)      # pylint: disable=no-member
    quit_button.clicked.connect(app.quit)        # pylint: disable=no-member

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
    sys.exit(app.exec())

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    main()
