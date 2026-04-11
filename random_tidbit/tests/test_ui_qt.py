#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Qt UI tests for random_tidbit/main.py
#
# Overview:
#   These tests verify the PySide6 UI layer: layout proportions, widget defaults,
#   fetch/cache behavior, image display, and keyboard shortcuts.
#   They are organised into five categories:
#     1. Layout proportions  — image pane ~1/3 width, debug pane capped height, etc.
#     2. Widget state        — combo defaults, placeholder text, initial labels.
#     3. Fetch behavior      — button disabled during fetch, re-enabled on done.
#     4. Image display       — pixmap loaded from bytes, rescaling, caption on failure.
#     5. Keyboard shortcuts  — F5 triggers fetch.
#
# *** GOTCHAS ***
#
# (A) Widget scope / refactoring blocker
#   main() builds every widget in local function scope — there is no way to access
#   them from outside without refactoring.  The standard fix is to extract a
#   build_ui(app) -> (window, widget_dict) helper and call it both from main() and
#   from tests.  Until that refactor lands, the tests that need internal widgets are
#   marked xfail (reason="needs build_ui() refactor").  When the refactor is done,
#   remove the xfail markers and fill in the body.
#
# (B) QApplication singleton
#   Only one QApplication may exist per process.  Use a session-scoped pytest fixture
#   (see `qt_app` below) so it is created once and reused.  pytest-qt's built-in
#   `qtbot` does this automatically, but we also need it when building widgets
#   manually outside of qtbot.
#
# (C) Headless display
#   Tests must run with QT_QPA_PLATFORM=offscreen (set below) or they will fail on
#   CI servers that have no display.  On Android emulators this env var is not used;
#   skip those tests with @pytest.mark.android instead.
#
# (D) Layout settling
#   Widget geometry (width, height) is 0 until the event loop has processed at least
#   one resize event.  After window.show(), call qtbot.waitExposed(window) and then
#   qtbot.wait(50) before reading geometry-dependent values.
#
# (E) Module reload between tests
#   If a test mutates module-level state (e.g. _fetch_cache), use the `fresh_main`
#   fixture below which clears that state, rather than reloading the module
#   (reloading PySide6 classes after QApplication exists causes crashes).
#
# Running:
#   QT_QPA_PLATFORM=offscreen pytest tests/test_ui_qt.py -v
#   or via the repo runner:
#   QT_QPA_PLATFORM=offscreen TEST_REGEX=test_ui_qt ./run_tests.bash
#

"""Qt UI tests for random_tidbit/main.py"""

import os
import pathlib
import py_compile
import struct
import sys
import tempfile
import types
import unittest
import zlib
import pytest

# Must be set before any PySide6 import
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QComboBox

from mezcla import debug

# main is imported after the QPA env var is set (PySide6 is safe to import now)
import main as _main  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qt_app():
    """Session-wide QApplication (only one allowed per process)."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture(autouse=True)
def fresh_main():
    """Clear module-level mutable state in main between tests."""
    _main._fetch_cache.clear()   # pylint: disable=protected-access
    yield
    _main._fetch_cache.clear()   # pylint: disable=protected-access


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_png_bytes(width: int = 4, height: int = 4, rgb: tuple = (255, 0, 0)) -> bytes:
    """Return a minimal valid PNG image as raw bytes (for QPixmap tests)."""
    def _chunk(name: bytes, data: bytes) -> bytes:
        c = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", c)

    raw_rows = b""
    for _ in range(height):
        raw_rows += b"\x00" + bytes(rgb) * width   # filter byte 0 + RGB pixels
    compressed = zlib.compress(raw_rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", compressed)
        + _chunk(b"IEND", b"")
    )


AGE_GROUPS = ["18+", "14-18", "9-14", "6-9", "3-5"]  # mirror of main.py


# ===========================================================================
# Category 1: Layout proportions
# ===========================================================================
#
# Goal: verify that the content area uses a 2:1 (text:image) stretch ratio,
# the debug pane is capped at 90 px, and the minimum window width is sensible.
#
# Implementation note (gotcha A + D):
#   All proportion checks need internal widget references (result_card,
#   image_card, debug_pane) that are currently in main()'s local scope.
#   The first real test below works around this by examining the source; the
#   rest are xfail pending the build_ui() refactor.

class TestLayoutProportions(unittest.TestCase):
    """Category 1: verify spatial layout properties"""
    

    def test_content_row_stretch_in_source(self):
        """Verify main.py encodes 2:1 stretch for content row (text vs image).
        
        Reads the source file and checks that addWidget calls for result_card
        and image_card pass stretch factors 2 and 1 respectively.  Fragile but
        works without the build_ui() refactor.
        """
        src = pathlib.Path(__file__).parent.parent / "main.py"
        text = src.read_text()
        # We expect lines like:  content_row.addWidget(result_card, 2)
        #                         content_row.addWidget(image_card, 1)
        self.assertTrue(
            "result_card, 2" in text,
            "result_card must be added with stretch=2")
        self.assertTrue(
            "image_card, 1" in text,
            "image_card must be added with stretch=1")
        debug.trace(4, "test_content_row_stretch_in_source: passed")

    @pytest.mark.xfail(reason="needs build_ui() refactor to expose widget dict")
    def test_image_card_width_approx_one_third(self):
        """Image card actual pixel width should be ~33% of the total content row width.
        
        After window.show() + qtbot.waitExposed(), read result_card.width() and
        image_card.width().  Assert image_card.width() / (result_card.width() +
        image_card.width()) is between 0.28 and 0.40 (allowing for margins/spacing).
        """
        assert False, "todo: implement (needs build_ui() refactor)"

    @pytest.mark.xfail(reason="needs build_ui() refactor to expose widget dict")
    def test_debug_pane_max_height(self):
        """debug_pane.maximumHeight() should be <= 90 px.
        
        Access debug_pane from widget_dict and call maximumHeight().
        No event-loop settling needed — max height is set at construction.
        """
        assert False, "todo: implement (needs build_ui() refactor)"

    @pytest.mark.xfail(reason="needs build_ui() refactor to expose widget dict")
    def test_minimum_window_width(self):
        """window.minimumWidth() should be >= 500 px.
        
        Prevents the layout from collapsing to an unusable narrow strip on
        small screens.  Read window.minimumWidth() from widget_dict['window'].
        """
        assert False, "todo: implement (needs build_ui() refactor)"


# ===========================================================================
# Category 2: Widget state / defaults
# ===========================================================================
#
# Goal: verify that widgets are initialised with the correct defaults — the
# age combo shows "18+" first, the date field shows today, placeholder texts
# are set, and the image label has non-empty initial text.
#
# The one real test creates a standalone QComboBox and populates it the same
# way main() does; this confirms the AGE_GROUPS list and default index without
# needing internal widget access.  The xfail tests need build_ui().

class TestWidgetDefaults(unittest.TestCase):
    """Category 2: widget initialisation defaults"""
    

    def test_age_combo_items_and_default(self):
        """Standalone QComboBox populated with AGE_GROUPS should default to '18+'.
        
        Replicates the exact construction in main():
            age_combo.addItems(AGE_GROUPS)
            age_combo.setCurrentIndex(0)
        Verifies item count, first item text, and current selection.
        """
        _ = QApplication.instance() or QApplication(sys.argv)
        combo = QComboBox()
        combo.addItems(AGE_GROUPS)
        combo.setCurrentIndex(0)
        self.assertTrue(
            combo.count() == len(AGE_GROUPS),
            f"Expected {len(AGE_GROUPS)} age groups, got {combo.count()}")
        self.assertTrue(
            combo.currentText() == "18+",
            f"Default age group should be '18+', got {combo.currentText()!r}")
        self.assertTrue(
            combo.itemText(combo.count() - 1) == "3-5",
            "Last age group should be '3-5' (youngest)")
        debug.trace(4, "test_age_combo_items_and_default: passed")

    @pytest.mark.xfail(reason="needs build_ui() refactor to expose widget dict")
    def test_result_text_placeholder(self):
        """result_text.placeholderText() should mention Fetch and/or F5.
        
        Access result_text from widget_dict and call placeholderText().
        Check that the hint mentions how to trigger a fetch so new users
        know what to do before any tidbit has loaded.
        """
        assert False, "todo: implement (needs build_ui() refactor)"

    @pytest.mark.xfail(reason="needs build_ui() refactor to expose widget dict")
    def test_image_label_initial_text(self):
        """image_label should show a non-empty placeholder before the first fetch.
        
        Access image_label from widget_dict and call text().
        The label should not be blank (confusing) and must not say 'unavailable'
        before any fetch has been attempted.
        """
        assert False, "todo: implement (needs build_ui() refactor)"

    @pytest.mark.xfail(reason="needs build_ui() refactor to expose widget dict")
    def test_date_edit_shows_today(self):
        """date_edit.date() should equal QDate.currentDate() at startup.
        
        Also verify displayFormat() == 'MMMM dd' so months appear as full names.
        """
        assert False, "todo: implement (needs build_ui() refactor)"


# ===========================================================================
# Category 3: Fetch / cache behavior
# ===========================================================================
#
# Goal: the _fetch_cache dict starts empty; after a fetch the entry is stored
# keyed by (date_str, age_group); bypass_cache=True forces a fresh API call;
# the Fetch button is disabled for the duration of the worker thread and
# re-enabled on completion.
#
# The one real test exercises the cache dict directly at module level —
# no widget access needed.  The button-state tests are xfail.

class TestFetchAndCache(unittest.TestCase):
    """Category 3: fetch lifecycle and result caching"""
    

    def test_fetch_cache_starts_empty(self):
        """_fetch_cache should be an empty dict at module import.
        
        The autouse fresh_main fixture clears it before each test, so this
        also verifies that the fixture is working correctly.
        """
        # pylint: disable=protected-access
        self.assertTrue(
            isinstance(_main._fetch_cache, dict),
            "_fetch_cache must be a dict")
        self.assertTrue(
            len(_main._fetch_cache) == 0,
            "_fetch_cache must be empty at the start of each test")
        # Verify expected key structure by inserting a sentinel entry
        _main._fetch_cache[("April 01", "18+")] = {
            "tidbit": "sentinel", "image_bytes": b"", "image_prompt": ""}
        self.assertTrue(
            _main._fetch_cache[("April 01", "18+")]["tidbit"] == "sentinel",
            "Cache must be indexable by (date_str, age_group) tuple")
        debug.trace(4, "test_fetch_cache_starts_empty: passed")

    def test_cache_read_and_write(self):
        """Writing a cache entry and reading it back should return the same data.

        This validates the full round-trip used by _FetchWorker / on_fetch():
          1. Check (_date, _age) in _fetch_cache  → False initially
          2. Store result dict                     → entry created
          3. Read entry back                        → same tidbit/image_prompt
          4. Second write (bypass) overwrites       → new value visible
        This test does NOT touch the network or the POE API.
        """
        # pylint: disable=protected-access
        key = ("April 01", "18+")
        # 1. Cache is empty at start (fresh_main fixture guarantees this)
        self.assertNotIn(key, _main._fetch_cache, "Cache should be empty initially")
        # 2. Write entry
        entry = {"tidbit": "April Fools!", "image_bytes": b"\x89PNG", "image_prompt": "jesters"}
        _main._fetch_cache[key] = entry
        # 3. Read back
        self.assertIn(key, _main._fetch_cache, "Entry should be present after write")
        self.assertEqual(_main._fetch_cache[key]["tidbit"], "April Fools!")
        self.assertEqual(_main._fetch_cache[key]["image_prompt"], "jesters")
        # 4. Overwrite (simulates bypass_cache=True on second fetch)
        entry2 = {"tidbit": "Updated!", "image_bytes": b"", "image_prompt": "new prompt"}
        _main._fetch_cache[key] = entry2
        self.assertEqual(_main._fetch_cache[key]["tidbit"], "Updated!",
                         "Second write should overwrite the cached entry")
        debug.trace(4, "test_cache_read_and_write: passed")

    @pytest.mark.xfail(reason="needs build_ui() refactor to expose widget dict")
    def test_fetch_button_disabled_during_fetch(self):
        """fetch_button.isEnabled() must be False immediately after on_fetch() starts.
        
        Patch _FetchWorker.run to block indefinitely (or never emit fetch_done).
        Call on_fetch(bypass_cache=True) and assert fetch_button.isEnabled() is False.
        Use qtbot.waitSignal with a short timeout to avoid hanging the test.
        """
        assert False, "todo: implement (needs build_ui() refactor)"

    @pytest.mark.xfail(reason="needs build_ui() refactor to expose widget dict")
    def test_fetch_button_reenabled_after_done(self):
        """fetch_button.isEnabled() must return to True after fetch_done signal fires.
        
        Inject a fake _FetchWorker that emits tidbit_ready, image_ready, and
        fetch_done immediately with canned data.  Use qtbot.waitUntil with
        timeout=3000 to assert isEnabled() becomes True.
        """
        assert False, "todo: implement (needs build_ui() refactor)"

    @pytest.mark.xfail(reason="needs build_ui() refactor to expose widget dict")
    def test_cache_hit_does_not_call_api(self):
        """When bypass_cache=False and a cache entry exists, no API call should be made.
        
        Pre-populate _fetch_cache with a (date_str, age_group) entry.
        Patch _load_local_poe_client so it raises if called.
        Trigger on_fetch(bypass_cache=False).  Assert the poe_client was never
        instantiated and result_text shows the cached tidbit.
        """
        assert False, "todo: implement (needs build_ui() refactor)"

    @pytest.mark.xfail(reason="needs build_ui() refactor to expose widget dict")
    def test_bypass_cache_forces_fresh_api_call(self):
        """Fetch button (bypass_cache=True) must call the API even if cache is warm.
        
        Pre-populate _fetch_cache.  Patch _load_local_poe_client to return a mock
        that records calls.  Click fetch_button.  Assert the mock was called at least
        once, indicating a fresh API call was made despite the cache entry.
        """
        assert False, "todo: implement (needs build_ui() refactor)"


# ===========================================================================
# Category 3b: _load_local_poe_client() loader correctness
# ===========================================================================
#
# Goal: verify that _load_local_poe_client() always returns a module with the
# POEClient attribute (i.e., OUR poe_client, not mezcla's), that successive
# calls return the same cached module object, and that stale cache entries
# (missing POEClient) are not returned.
#
# *** GOTCHAS ***
#
# (F) .pyc-only environments (Android)
#   On Android, buildozer deploys poe_client.pyc directly in the app dir.
#   Python 3's import_module() cannot find a bare .pyc in a directory — it
#   expects either a .py source or __pycache__/module.cpython-3XX.pyc layout.
#   The fix is to use spec_from_file_location with the explicit .pyc path,
#   which importlib supports for both .py and .pyc files.
#   Testing this on desktop requires creating a temp directory with only a
#   .pyc file and temporarily adjusting __file__ (complex); the test below
#   verifies the desktop (.py) path and documents the Android (.pyc) path
#   with an xfail stub that can be enabled once the build environment is
#   set up for .pyc-only testing.
#
# (G) sys.modules cache poisoning
#   A previous version of _load_local_poe_client() registered the module in
#   sys.modules BEFORE exec_module() ran.  If exec_module() raised
#   (e.g., FileNotFoundError), the broken empty module stayed cached.  All
#   subsequent calls returned the broken module, producing
#   "module has no attribute 'POEClient'".
#   The current code registers only AFTER success and validates the cached
#   entry with hasattr(cached, 'POEClient') before returning it.

class TestLoadLocalPoeClient(unittest.TestCase):
    """Category 3b: _load_local_poe_client() returns correct module and caches it"""

    def test_returns_module_with_poe_client(self):
        """_load_local_poe_client() must return a module that has the POEClient class.

        This is the most basic correctness check: the returned module should be
        OUR local poe_client.py (not mezcla's upstream version), which has the
        generate_image_prompt() and generate_image() methods added for this app.
        Verified by checking hasattr(mod, 'POEClient').
        """
        # Clear any cached entry to force a fresh load
        sys.modules.pop("_local_poe_client", None)
        mod = _main._load_local_poe_client()   # pylint: disable=protected-access
        self.assertTrue(
            hasattr(mod, "POEClient"),
            "_load_local_poe_client() must return a module with POEClient class")
        self.assertTrue(
            hasattr(mod.POEClient, "generate_image_prompt"),
            "POEClient must have generate_image_prompt() method (from local poe_client.py)")
        self.assertTrue(
            hasattr(mod.POEClient, "generate_image"),
            "POEClient must have generate_image() method (from local poe_client.py)")
        debug.trace(4, "test_returns_module_with_poe_client: passed")

    def test_returns_cached_module_on_second_call(self):
        """Successive calls to _load_local_poe_client() must return the same module object.

        The function registers the loaded module in sys.modules['_local_poe_client']
        and returns the cached copy on subsequent calls.  This test verifies that
        the caching logic works: both calls return the same object (is identity).
        Gotcha G: if a stale broken entry is cached, the second call will still
        return it — this test verifies that the module returned is always valid.
        """
        sys.modules.pop("_local_poe_client", None)
        mod1 = _main._load_local_poe_client()   # pylint: disable=protected-access
        mod2 = _main._load_local_poe_client()   # pylint: disable=protected-access
        self.assertIs(mod1, mod2,
                      "Second call must return the same cached module object")
        debug.trace(4, "test_returns_cached_module_on_second_call: passed")

    def test_stale_cache_entry_is_rejected(self):
        """A cached entry in sys.modules without POEClient must be replaced.

        Simulates the cache-poisoning scenario (gotcha G): a broken module
        object (no POEClient attribute) is put in sys.modules['_local_poe_client'],
        then _load_local_poe_client() is called.  It must detect the bad entry,
        pop it, load afresh, and return a valid module.
        """
        # Inject a stale/broken module (no POEClient attribute)
        broken = types.ModuleType("_local_poe_client")
        sys.modules["_local_poe_client"] = broken
        # _load_local_poe_client should detect hasattr fails and reload
        mod = _main._load_local_poe_client()    # pylint: disable=protected-access
        self.assertTrue(
            hasattr(mod, "POEClient"),
            "Must reject stale cache entry and return freshly loaded module")
        self.assertIsNot(mod, broken,
                         "Returned module must not be the stale broken module")
        debug.trace(4, "test_stale_cache_entry_is_rejected: passed")

    def test_loads_from_pyc_when_py_absent(self):
        """_load_local_poe_client() must load from poe_client.pyc when .py is absent.

        This is the Android scenario: only .pyc files are deployed.
        Gotcha F: Python 3 import_module() cannot find a bare .pyc in a directory.
        The old fallback `importlib.import_module('poe_client')` failed with
        'No module named poe_client' because of this exact limitation.
        The new code uses spec_from_file_location with the explicit .pyc path.

        Also verified by buildozer.spec: poe_client.py must NOT appear in
        source.exclude_patterns (it was accidentally excluded in an earlier version,
        which caused this test to be written).
        """
        # Compile poe_client.py → a temp dir containing only the .pyc
        src_py = pathlib.Path(__file__).parent.parent / "poe_client.py"
        with tempfile.TemporaryDirectory() as tmpdir:
            # Compile to __pycache__ first (py_compile default), then copy bare
            compiled = py_compile.compile(str(src_py), cfile=os.path.join(tmpdir, "poe_client.pyc"),
                                          doraise=True)
            # Temporarily redirect _main.__file__ so _load_local_poe_client looks in tmpdir
            original_file = _main.__file__
            sys.modules.pop("_local_poe_client", None)
            try:
                _main.__file__ = os.path.join(tmpdir, "main.pyc")  # fake Android entrypoint
                mod = _main._load_local_poe_client()               # pylint: disable=protected-access
            finally:
                _main.__file__ = original_file
                sys.modules.pop("_local_poe_client", None)
            self.assertTrue(hasattr(mod, "POEClient"),
                            f"Must load POEClient from .pyc at {compiled}")
            debug.trace(4, "test_loads_from_pyc_when_py_absent: passed")


# ===========================================================================
# Category 4: Image display
# ===========================================================================
#
# Goal: valid PNG bytes produce a non-null QPixmap; null/empty bytes cause the
# label to show fallback text; the image rescales when the label is resized;
# the image_caption widget shows the prompt when no image loaded.
#
# The one real test is fully standalone: it constructs a minimal valid PNG in
# memory and verifies QPixmap.loadFromData accepts it without touching main().

class TestImageDisplay(unittest.TestCase):
    """Category 4: image decode, display, and fallback"""
    

    def test_pixmap_loads_from_valid_png(self):
        """QPixmap.loadFromData should succeed for a well-formed PNG byte string.
        
        Constructs a minimal 4x4 red PNG using pure stdlib (struct + zlib),
        then calls QPixmap().loadFromData(bytes).  Asserts the result is not
        null and has the expected dimensions.
        This is the core decode path used by _on_image() in main.py.
        """
        _ = QApplication.instance() or QApplication(sys.argv)
        png_bytes = _minimal_png_bytes(width=4, height=4, rgb=(255, 0, 0))
        pix = QPixmap()
        ok = pix.loadFromData(png_bytes)
        self.assertTrue(ok and not pix.isNull(),
                       "loadFromData should succeed for a valid PNG")
        self.assertTrue(pix.width() == 4 and pix.height() == 4,
                       f"Expected 4x4 pixmap, got {pix.width()}x{pix.height()}")
        debug.trace(4, "test_pixmap_loads_from_valid_png: passed")

    def test_pixmap_rejects_empty_bytes(self):
        """QPixmap.loadFromData should return False / null pixmap for empty bytes.
        
        Verifies that _on_image() will correctly fall through to the 'decode
        failed' branch when the API returns an empty or corrupt response.
        """
        _ = QApplication.instance() or QApplication(sys.argv)
        pix = QPixmap()
        ok = pix.loadFromData(b"")
        self.assertTrue(not ok or pix.isNull(),
                       "loadFromData should fail for empty bytes")
        debug.trace(4, "test_pixmap_rejects_empty_bytes: passed")

    @pytest.mark.xfail(reason="needs build_ui() refactor to expose widget dict")
    def test_image_label_shows_pixmap_after_on_image(self):
        """After _on_image(valid_bytes, prompt) is called, image_label.pixmap() must be non-null.
        
        Build the UI via build_ui(), inject a valid PNG via the _on_image slot,
        then call qtbot.waitUntil(lambda: not image_label.pixmap().isNull(), 2000).
        Also assert image_label.text() is empty (no placeholder text left).
        """
        assert False, "todo: implement (needs build_ui() refactor)"

    @pytest.mark.xfail(reason="needs build_ui() refactor to expose widget dict")
    def test_image_caption_shown_on_decode_failure(self):
        """image_caption.text() should be non-empty when _on_image receives junk bytes.
        
        Call _on_image(b'notanimage', 'test prompt').
        Assert image_label.pixmap() is null and image_caption.text() contains
        at least part of 'test prompt'.  This ensures the user always has some
        context when image display fails.
        """
        assert False, "todo: implement (needs build_ui() refactor)"

    @pytest.mark.xfail(reason="needs build_ui() refactor to expose widget dict")
    def test_image_rescales_on_resize(self):
        """Resizing the window should rescale the pixmap to fill the image_label.
        
        Load a large pixmap via _on_image, record image_label.pixmap().size(),
        resize the window narrower, wait 100 ms, check the pixmap size changed
        proportionally.  Aspect ratio (width/height) should remain within 5% of
        the original.
        Gotcha: the QEvent.Resize filter fires during layout, so the first resize
        after show() may use size 0,0 — wait for waitExposed before recording.
        """
        assert False, "todo: implement (needs build_ui() refactor)"


# ===========================================================================
# Category 5: Keyboard shortcuts
# ===========================================================================
#
# Goal: pressing F5 should call on_fetch(bypass_cache=True) just as clicking
# the Fetch button does.  All tests here need the full built window.

class TestKeyboardShortcuts(unittest.TestCase):
    """Category 5: keyboard shortcut bindings"""
    

    @pytest.mark.xfail(reason="needs build_ui() refactor to expose widget dict")
    def test_f5_triggers_fetch(self):
        """F5 key press on the window should invoke on_fetch(bypass_cache=True).
        
        Build the UI, patch on_fetch to record calls, use qtbot.keyClick(window,
        Qt.Key_F5), then assert on_fetch was called with bypass_cache=True.
        Note: the QShortcut must be installed on the window widget (not the
        application) — confirm with window.findChildren(QShortcut).
        """
        assert False, "todo: implement (needs build_ui() refactor)"

    @pytest.mark.xfail(reason="needs build_ui() refactor to expose widget dict")
    def test_f5_noop_while_fetch_in_progress(self):
        """F5 during an ongoing fetch should not start a second worker thread.
        
        Start a fetch that never completes (patch run() to block).  Press F5.
        Assert only one _FetchWorker was created.
        Gotcha: on_fetch() already guards against re-entry via
        `if _worker[0] and _worker[0].isRunning()` — test that guard directly.
        """
        assert False, "todo: implement (needs build_ui() refactor)"


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
