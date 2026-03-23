import sys
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

import feature_stubs

# PySide6 requires a QApplication instance before creating any widgets
@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    yield app

def test_ai_mobile_lab_menu():
    """Verify the AI Mobile Lab menu loads and handles clicks (the Qt equivalent of Selenium UI testing)."""
    menu = feature_stubs.create_ai_mobile_lab_menu()
    assert menu is not None
    
    # Verify title widget
    layout = menu.layout()
    title_label = layout.itemAt(0).widget()
    assert "AI Mobile Lab" in title_label.text()
    
    # Test clicking the first feature button ("Tok")
    first_btn = menu._buttons[0]
    # Simulate a mouse click on the UI element (Qt's Selenium-like behavior)
    QTest.mouseClick(first_btn, Qt.LeftButton)
    
    assert first_btn.isChecked()
    assert menu._stack.currentIndex() == 0

def test_smartphone_features_menu():
    """Verify the Smartphone Features menu loads and handles clicks."""
    menu = feature_stubs.create_smartphone_features_menu()
    assert menu is not None
    
    # Verify we have exactly 10 features
    assert len(menu._buttons) == 10
    
    # Test clicking the "Camera" feature (index 2)
    camera_btn = menu._buttons[2]
    QTest.mouseClick(camera_btn, Qt.LeftButton)
    
    assert camera_btn.isChecked()
    assert menu._stack.currentIndex() == 2
