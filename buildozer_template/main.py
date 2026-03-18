#! /usr/bin/env python
#
# based on https://www.qt.io/blog/2018/05/04/hello-qt-for-python
#

"""Simple Hello World style app for use with buildozer"""

# Standard packages
import datetime
import os
import sys


# Installed packages
from PySide6.QtWidgets import QApplication, QPushButton, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QApplication, QCalendarWidget, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget)

# Local modules
## TEMP (force tracing):
os.environ.setdefault("DEBUG_LEVEL", "5")
from mezcla import debug, system
import feature_stubs

# Constants
VIA_STUDIO = system.getenv_bool(
    "VIA_STUDIO", False,
    desc="Wether invoked via Android Studio")
USE_FEATURES = system.getenv_value(
    "USE_FEATURES", None,
    desc="Wether invoked via Android Studio")
## TEMP: USE_FEATURES = False

def main():
    """Entry point"""
    debug.trace(4, "main()")
    ## TEMP (for logcat check):
    system.print_stderr(f"in main(): {__name__}")
    app = QApplication(sys.argv)
    debugging = debug.debugging(4)
    if not debugging:
        debugging = VIA_STUDIO

    # Decide whether to show AI feature demos or the barebones template.
    # Run barebones when the current time as HHMMSS is an odd integer.
    use_features = USE_FEATURES
    if (use_features is None) and not debugging:
        now = datetime.datetime.now()
        hhmmss = int(now.strftime("%H%M%S"))
        use_features = (hhmmss % 2 == 0)
        debug.trace(4, f"hhmmss={hhmmss} use_features={use_features}")

    # Create main window widget
    window = QWidget()
    window.setWindowTitle("Buildozer Template")

    # Create widgets
    label = QLabel("buildozer template label")
    if debug.debugging(6):
        ## TODO4: debug.traceback.print_stack(file=sys.stderr)
        ## TODO?: debug.raise_exception(4)
        try:
            raise RuntimeError()
        except:
            debug.traceback.print_stack(file=sys.stderr)
            label = QLabel(str(sys.exc_info()))
    label.setWordWrap(True)
    button = QPushButton("Quit")

    # Connect button properly
    button.clicked.connect(app.quit)    # pylint: disable=no-member

    # Layout
    layout = QVBoxLayout()
    layout.addWidget(label)
    if use_features:
        app.setStyleSheet(feature_stubs.APP_STYLE)
        window.setWindowTitle("AI Mobile Lab")
        window.resize(480, 780)
        layout.addWidget(feature_stubs.create_feature_tabs())
    if debug.debugging():
        layout.addWidget(QLabel(__name__))
    layout.addWidget(button)
    window.setLayout(layout)
    debug.trace_expr(5, app, window, label, button, layout)

    # Start app and then exit when done
    window.show()
    sys.exit(app.exec())

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    main()
