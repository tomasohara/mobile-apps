#! /usr/bin/env python
#
# based on https://www.qt.io/blog/2018/05/04/hello-qt-for-python
#

"""Simple Hello World style app for use with buildozer"""

import datetime
import sys
from PySide6.QtWidgets import QApplication, QPushButton, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QApplication, QCalendarWidget, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget)
from mezcla import debug, system

def main():
    """Entry point"""
    app = QApplication(sys.argv)

    # Create main window widget
    window = QWidget()
    window.setWindowTitle("Buildozer Template")

    # Create widgets
    label = QLabel("buildozer template label")
    label.setWordWrap(True)
    button = QPushButton("Quit")

    # Connect button properly
    button.clicked.connect(app.quit)    # pylint: disable=no-member

    # Layout
    layout = QVBoxLayout()
    layout.addWidget(label)
    layout.addWidget(button)
    window.setLayout(layout)

    # Start app and then exit when done
    window.show()
    sys.exit(app.exec())

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    main()
