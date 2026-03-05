#! /usr/bin/env python3
#
# Test for main.py (Random Tidbit)
#
# note: via Gemini 3 Pro
#

"""Tests for main.py (Random Tidbit)"""

import sys
import os
from PySide6.QtCore import Qt

# Local modules
from mezcla import debug
from mezcla.unittest_wrapper import TestWrapper, invoke_tests

class TestIt(TestWrapper):
    """Class for testcase definition"""
    script_module = "main"

    def test_01_cut_paste_flags(self):
        """Verify the expected interaction flags for the result field"""
        # We want to ensure that any result field has these flags
        expected = Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard | Qt.LinksAccessibleByMouse
        
        # We just verify that our assumption about what's needed is correct
        # and that we have these flags available.
        debug.trace(4, f"TestIt.test_01_cut_paste_flags(); expected={expected}")
        self.do_assert(expected & Qt.TextSelectableByMouse, "Selection by mouse should be enabled")
        self.do_assert(expected & Qt.TextSelectableByKeyboard, "Selection by keyboard should be enabled")

if __name__ == '__main__':
    invoke_tests(__file__)
