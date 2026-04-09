#! /usr/bin/env python
#
# based on https://www.qt.io/blog/2018/05/04/hello-qt-for-python
#

"""Simple Hello World style app for use with buildozer"""

# Standard packages
import datetime
## OLD: import os
import sys

# Installed packages
from PySide6.QtCore import QSysInfo
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QStackedWidget, QVBoxLayout, QWidget)

# Local modules
## TEMP (force tracing):
## os.environ.setdefault("DEBUG_LEVEL", "5")
from mezcla import debug, system
import feature_stubs

# Constants
VIA_STUDIO = system.getenv_bool(
    "VIA_STUDIO", False,
    desc="Whether invoked via Android Studio")
USE_AI_FEATURES = system.getenv_value(
    "USE_AI_FEATURES", None,
    desc="Whether to use the AI features")
USE_AI_FEATURES = system.getenv_value(
    "USE_AI_FEATURES", None,
    desc="Whether to use the AI features")
## TEMP: USE_FEATURES = False
USE_HANDHELD_FEATURES = system.getenv_value(
    "USE_HANDHELD_FEATURES", None,
    desc="Whether to use the handheld/smartphone features")

def main():
    """Entry point"""
    # pylint: disable=too-many-locals,too-many-statements
    debug.trace(4, "main()")
    debug.trace_expr(5, sys.platform)
    ## TEMP (for logcat check):
    system.print_stderr(f"in main(): {__name__}")
    
    try:
        # pylint: disable=import-outside-toplevel,import-error,unused-import
        from PySide6.QtWebView import QtWebView
        QtWebView.initialize()
    except ImportError:
        pass

    app = QApplication(sys.argv)
    debugging = debug.debugging(4)
    if not debugging:
        debugging = VIA_STUDIO

    # Decide whether to show AI feature demos or the barebones template.
    # Run barebones when the current time as HHMMSS is an odd integer.
    use_ai_features = USE_AI_FEATURES
    if (use_ai_features is None) and not debugging:
        now = datetime.datetime.now()
        hhmmss = int(now.strftime("%H%M%S"))
        use_ai_features = (hhmmss % 2 == 0)
        debug.trace(4, f"hhmmss={hhmmss} use_ai_features={use_ai_features}")
    use_handheld_features = USE_HANDHELD_FEATURES

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

    # Radiobox control for menu selection
    radio_layout = QHBoxLayout()
    btn_debug = QRadioButton("Debugging (no menu)")
    btn_ai = QRadioButton("AI Mobile Lab")
    btn_smart = QRadioButton("Smartphone Features")
    
    radio_group = QButtonGroup(window)
    radio_group.addButton(btn_debug)
    radio_group.addButton(btn_ai)
    radio_group.addButton(btn_smart)

    radio_layout.addWidget(btn_debug)
    radio_layout.addWidget(btn_ai)
    radio_layout.addWidget(btn_smart)
    layout.addLayout(radio_layout)

    # Stacked widget for the menus
    stack = QStackedWidget()
    
    debug_widget = QWidget()
    ai_widget = feature_stubs.create_ai_mobile_lab_menu()
    smart_widget = feature_stubs.create_smartphone_features_menu()
    
    stack.addWidget(debug_widget)
    stack.addWidget(ai_widget)
    stack.addWidget(smart_widget)
    
    def on_menu_changed():
        is_mobile = QSysInfo.productType() in ("android", "ios")
        if btn_ai.isChecked():
            stack.setCurrentWidget(ai_widget)
            app.setStyleSheet(feature_stubs.APP_STYLE)
            window.setWindowTitle("AI Mobile Lab")
            if not is_mobile:
                window.resize(480, 780)
        elif btn_smart.isChecked():
            stack.setCurrentWidget(smart_widget)
            app.setStyleSheet(feature_stubs.APP_STYLE)
            window.setWindowTitle("Smartphone Features")
            if not is_mobile:
                window.resize(480, 780)
        else:
            stack.setCurrentWidget(debug_widget)
            app.setStyleSheet("")
            window.setWindowTitle("Buildozer Template")
            
    btn_debug.toggled.connect(on_menu_changed)
    btn_ai.toggled.connect(on_menu_changed)
    btn_smart.toggled.connect(on_menu_changed)
    
    if use_ai_features:
        btn_ai.setChecked(True)
    elif use_handheld_features:
        btn_smart.setChecked(True)
    else:
        btn_debug.setChecked(True)
    on_menu_changed()

    layout.addWidget(stack)

    ## OLD:
    ## if use_features:
    ##     app.setStyleSheet(feature_stubs.APP_STYLE)
    ##     window.setWindowTitle("AI Mobile Lab")
    ##     window.resize(480, 780)
    ##     layout.addWidget(feature_stubs.create_feature_tabs())

    if debug.debugging():
        layout.addWidget(QLabel(__name__))
    layout.addWidget(button)
    window.setLayout(layout)
    debug.trace_expr(5, app, window, label, button, layout)

    # Start app and then exit when done
    is_mobile = QSysInfo.productType() in ("android", "ios")
    if is_mobile:
        window.showMaximized()
    else:
        window.show()
    sys.exit(app.exec())

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    main()
