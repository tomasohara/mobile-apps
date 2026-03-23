import sys
import pytest
from PySide6.QtWidgets import QApplication

import main

# PySide6 requires a QApplication instance before creating any widgets
@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    yield app

def test_main_initialization(qapp, monkeypatch):
    """Verify that the main application initializes without errors."""
    
    # Mock sys.exit to prevent the test from terminating
    monkeypatch.setattr(sys, "exit", lambda x: None)
    
    # Mock QApplication.exec to prevent blocking the test indefinitely
    monkeypatch.setattr(QApplication, "exec", lambda self: 0)
    
    # Mock the QApplication constructor in the main module to return our test instance
    # This prevents the "A QApplication instance already exists" error
    monkeypatch.setattr(main, "QApplication", lambda args: qapp)
    
    # Run the main function
    main.main()
    
    # If we reached this point without any exceptions, the initialization
    # (creating the window, layouts, and menus) was successful.
