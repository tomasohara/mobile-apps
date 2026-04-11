#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Android coarse-grained tests for random_tidbit
#
# Overview:
#   These tests treat the installed APK as a complete black box and interact
#   with it only through adb shell commands and screenshots.  They are
#   intentionally coarse: rather than inspecting pixel values or parsing UI
#   trees in detail, they ask questions like "is there a non-blank region in
#   the image pane?" or "did the logcat output mention a completed fetch?".
#
# *** GOTCHAS ***
#
# (A) Device / emulator required
#   All tests in this file are skipped automatically when `adb devices` returns
#   no connected device.  Run against a real device or start an AVD before
#   invoking pytest.  The `-m android` flag is NOT needed — no @pytest.mark.android
#   decorators are used; all device tests auto-skip when no device is connected.
#   CI pipelines should use `@pytest.mark.skipif(not _adb_device_available(), ...)`
#   or a dedicated Android CI runner (e.g. GitHub Actions + Genymotion cloud).
#
# (B) Buildozer rebuild
#   Any Python source change requires a fresh APK: `buildozer android debug deploy`.
#   Tests run against whatever APK is currently installed; they do NOT rebuild it.
#   Always rebuild before running this suite after code changes.
#
# (C) Timing / non-determinism
#   Image generation (LLM call + chat-completions image fallback) can take
#   20-50 seconds.  Hardcoded sleeps are fragile; the preferred approach is to
#   poll logcat for a completion marker (e.g. "fetch_done") with a timeout.
#   The initial implementation uses time.sleep for simplicity; TODO items note
#   where polling should replace it.
#
# (D) Layout coordinates on Android
#   The pixel geometry of the image pane varies with screen DPI and orientation.
#   Do NOT hardcode pixel offsets.  Instead use `adb shell uiautomator dump`
#   to get widget bounds at runtime, then crop the screenshot accordingly.
#   The xfail image-region test currently hardcodes a fractional crop as a
#   placeholder — fix this once the uiautomator dump approach is implemented.
#
# (E) QComboBox → Android Spinner
#   PySide6 QComboBox renders as a native android.widget.Spinner on Android.
#   uiautomator resource IDs and class names differ from the desktop.
#   Tap by coordinate (from uiautomator dump bounds) rather than by class name.
#
# (F) Logcat noise
#   Filter logcat to the python tag: `adb logcat -s python:V`.  Even then,
#   multiple app restarts may leave stale lines in the buffer.  Always call
#   `adb logcat -c` before starting the app to clear the buffer, then read
#   fresh output after the test action.
#
# (G) Package / activity names
#   Update PACKAGE and MAIN_ACTIVITY below to match buildozer.spec settings.
#   The defaults shown are the standard Kivy/PySide6-for-Android conventions.
#
# Running:
#   pytest tests/test_android.py -v
#   (requires a connected device or running emulator; -m android is NOT needed)
#

"""Android coarse-grained tests for the random_tidbit APK"""

## OLD: import os
import pathlib
import subprocess
## OLD: import sys
import time
import pytest

try:
    from PIL import Image as _PILImage
    _PIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PILImage = None
    _PIL_AVAILABLE = False

from mezcla import debug
from mezcla import system
import unittest

# ---------------------------------------------------------------------------
# Constants — update to match buildozer.spec
# ---------------------------------------------------------------------------

PACKAGE = "org.test.random_tidbit"      # package.domain + package.name from buildozer.spec
MAIN_ACTIVITY = f"{PACKAGE}/org.kivy.android.PythonActivity"   # p4a/Qt activity class
ADB = "adb"
FETCH_WAIT_SECS = 45       # generous timeout for LLM + image generation
LOGCAT_TAG = "python"      # tag used by the PySide6/Python runtime on Android


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_adb(*args, check=False, capture=True) -> subprocess.CompletedProcess:
    """Run an adb command and return the CompletedProcess result."""
    cmd = [ADB] + list(args)
    debug.trace(4, f"_run_adb: {cmd}")
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check,
    )
    debug.trace(5, f"_run_adb() => {result!r}")
    return result


def _adb_device_available() -> bool:
    """Return True if at least one adb device (real or emulator) is connected."""
    try:
        result = _run_adb("devices")
        lines = [l.strip() for l in result.stdout.splitlines()
                 if l.strip() and not l.startswith("List of devices")]
        return any("\tdevice" in l for l in lines)
    except FileNotFoundError:
        return False


def _clear_logcat():
    """Clear the logcat buffer so subsequent reads only contain new output."""
    _run_adb("logcat", "-c")


def _read_logcat(tag: str = LOGCAT_TAG, extra_seconds: float = 0.0) -> str:
    """Dump current logcat buffer filtered to TAG.  Returns decoded text."""
    if extra_seconds:
        time.sleep(extra_seconds)
    result = _run_adb("logcat", "-d", "-s", f"{tag}:V")
    return result.stdout


def _take_screenshot(local_path: str = "/tmp/rt_screenshot.png") -> str:
    """Capture device screenshot and pull it to LOCAL_PATH.  Returns local path."""
    _run_adb("shell", "screencap", "-p", "/sdcard/rt_test_screen.png")
    _run_adb("pull", "/sdcard/rt_test_screen.png", local_path)
    return local_path


def _kill_app():
    """Force-stop the app on the connected device (safe to call even if not running)."""
    _run_adb("shell", "am", "force-stop", PACKAGE)
    debug.trace(4, f"_kill_app: force-stopped {PACKAGE}")


def _poll_logcat_for(marker: str, timeout: float = FETCH_WAIT_SECS,
                     poll_interval: float = 2.0, tag: str = LOGCAT_TAG) -> bool:
    """Poll logcat every POLL_INTERVAL seconds until MARKER appears or TIMEOUT expires.

    Returns True if the marker was found, False if timeout elapsed first.
    Gotcha (F): caller should call _clear_logcat() *before* the action that
    generates the marker, otherwise stale lines may give a false positive.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        text = _read_logcat(tag=tag)
        if marker in text:
            debug.trace(4, f"_poll_logcat_for: found {marker!r}")
            return True
        debug.trace(5, f"_poll_logcat_for: marker not yet found, sleeping {poll_interval}s")
        time.sleep(poll_interval)
    debug.trace(3, f"_poll_logcat_for: timed out after {timeout}s waiting for {marker!r}")
    return False


def _get_screen_bounds_from_uiautomator() -> tuple:
    """Return (width, height) of the connected device screen via uiautomator dump.

    Falls back to (1080, 2400) if the dump fails.  The values are pixel
    dimensions matching the screenshot resolution.
    """
    result = _run_adb("shell", "wm", "size")
    # expected: "Physical size: 1080x2400"
    for line in result.stdout.splitlines():
        if "Physical size:" in line or "Override size:" in line:
            try:
                dims = line.split(":")[-1].strip()
                w, h = dims.split("x")
                return int(w), int(h)
            except (ValueError, IndexError):
                pass
    debug.trace(3, "_get_screen_bounds_from_uiautomator: fallback to 1080x2400")
    return 1080, 2400


# ---------------------------------------------------------------------------
# Pytest markers / skip logic
# ---------------------------------------------------------------------------

_DEVICE_AVAILABLE = _adb_device_available()

requires_device = pytest.mark.skipif(
    not _DEVICE_AVAILABLE,
    reason="No Android device/emulator connected (run `adb devices` to check)")


@pytest.fixture(autouse=True, scope="session")
def kill_app_after_session():
    """Session-scoped fixture: kill the app once at the very end of the test run.
    Also kills before tests start so any leftover instance from a previous run
    doesn't interfere with a fresh launch.
    """
    if _DEVICE_AVAILABLE:
        _kill_app()
    yield
    if _DEVICE_AVAILABLE:
        _kill_app()


# ===========================================================================
# Category 1: Tooling availability and device sanity
# ===========================================================================
#
# Goal: confirm that the adb toolchain is present, a device is connected, and
# the app is installed.  These are prerequisites for every other test.  If
# they fail it signals an environment problem, not an app bug.

class TestToolingAndDevice(unittest.TestCase):
    """Category 1: verify adb toolchain and device availability"""
    

    def test_adb_command_available(self):
        """adb must be on PATH and return a zero exit code for 'adb version'.
        
        Failure here means adb is not installed or not on PATH.  Install
        Android SDK Platform Tools and add <sdk>/platform-tools to PATH.
        This test does NOT require a connected device.
        """
        try:
            result = _run_adb("version")
            self.assertTrue(result.returncode == 0,
                           f"adb version returned non-zero: {result.stderr}")
            self.assertTrue("Android Debug Bridge" in result.stdout,
                           "adb version output did not contain expected string")
            debug.trace(4, f"test_adb_command_available: {result.stdout.splitlines()[0]}")
        except FileNotFoundError:
            self.fail("adb not found on PATH — install Android SDK Platform Tools")

    def test_poe_client_not_excluded_from_build(self):
        """buildozer.spec must NOT exclude poe_client.py from the Android build.

        poe_client.py was accidentally listed in source.exclude_patterns, which
        caused the app to fail at runtime with:
            'Cannot find poe_client.py or poe_client.pyc'
        This test reads buildozer.spec directly and asserts poe_client.py is absent
        from the exclude_patterns line so the regression cannot reoccur silently.
        Does NOT require a connected device.
        """
        spec_path = pathlib.Path(__file__).parent.parent / "buildozer.spec"
        spec_text = spec_path.read_text()
        for line in spec_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("source.exclude_patterns") and not stripped.startswith("#"):
                self.assertNotIn(
                    "poe_client.py", stripped,
                    f"poe_client.py must not be in source.exclude_patterns; found: {stripped!r}")
                debug.trace(4, f"test_poe_client_not_excluded_from_build: exclude line ok: {stripped!r}")
                return
        # No exclude_patterns line found — that's fine (means nothing is excluded)
        debug.trace(4, "test_poe_client_not_excluded_from_build: no source.exclude_patterns line found")

    @requires_device
    @pytest.mark.xfail(reason="Package name in PACKAGE constant may not match installed APK")
    def test_app_is_installed(self):
        """The APK identified by PACKAGE must be installed on the connected device.
        
        Run `adb shell pm list packages` and assert PACKAGE appears in the output.
        If this fails: rebuild with `buildozer android debug deploy` and retry.
        Gotcha: the package name is set in buildozer.spec (package.name field);
        update PACKAGE at the top of this file if it does not match.
        """
        assert False, "todo: implement — run adb shell pm list packages | grep PACKAGE"

    @requires_device
    @pytest.mark.xfail(reason="todo: implement")
    def test_device_screen_on(self):
        """The device screen should be on and unlocked before running UI tests.
        
        Run `adb shell dumpsys power | grep mWakefulness` and assert the result
        is 'Awake'.  If not, send a KEYCODE_WAKEUP event:
        `adb shell input keyevent KEYCODE_WAKEUP`.
        Unlock may require additional steps depending on the device lock type.
        """
        assert False, "todo: implement"


# ===========================================================================
# Category 2: App launch
# ===========================================================================
#
# Goal: the app starts within a reasonable time, the main window is visible,
# and the form fields are present.  Checked via uiautomator text search.

class TestAppLaunch(unittest.TestCase):
    """Category 2: verify app launches and the form is visible"""

    def tearDown(self):
        """Kill the app after each launch test to avoid leftover instances."""
        if _DEVICE_AVAILABLE:
            _kill_app()

    @requires_device
    def test_app_starts_without_crash(self):
        """The app should start and remain alive for at least 10 seconds.
        
        Launches via `adb shell am start -n MAIN_ACTIVITY`, waits 10 s, then
        checks that no Android crash dialog is visible (text 'Unfortunately'
        or 'has stopped').  Uses `adb shell uiautomator dump` + grep.
        
        Gotcha (C): 10 s may not be enough for the first fetch to complete,
        but it is enough to detect an immediate crash.
        """
        _clear_logcat()
        result = _run_adb("shell", "am", "start", "-n", MAIN_ACTIVITY)
        self.assertTrue(result.returncode == 0,
                       f"am start failed: {result.stderr}")
        time.sleep(10)
        # Dump the UI hierarchy and look for crash dialog text
        dump = _run_adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
        debug.assertion(dump.returncode == 0)
        pull = _run_adb("pull", "/sdcard/ui.xml", "/tmp/rt_ui.xml")
        crash_phrases = ["Unfortunately", "has stopped", "keeps stopping"]
        if pull.returncode == 0:
            try:
                ## OLD: with open("/tmp/rt_ui.xml") as f:
                with system.open_file("/tmp/rt_ui.xml") as f:
                    xml = f.read()
                for phrase in crash_phrases:
                    self.assertTrue(phrase not in xml,
                                   f"Crash dialog detected: '{phrase}' in UI hierarchy")
            except OSError:
                debug.trace(3, "test_app_starts_without_crash: could not read UI dump")
        debug.trace(4, "test_app_starts_without_crash: no crash dialog detected")

    @requires_device
    @pytest.mark.xfail(reason="todo: implement — needs correct uiautomator resource IDs")
    def test_fetch_button_visible(self):
        """The 'Fetch Tidbit' button must be visible in the UI hierarchy after launch.
        
        Use `adb shell uiautomator dump` and parse the XML to find a node with
        text='Fetch Tidbit' or content-desc containing 'Fetch'.
        Gotcha (E): on some Android versions, QPushButton text may be uppercased
        by the theme — search case-insensitively.
        """
        assert False, "todo: implement"

    @requires_device
    @pytest.mark.xfail(reason="todo: implement")
    def test_age_combo_visible(self):
        """The age group spinner/combo must be visible before the first fetch.
        
        After launch, dump UI hierarchy and confirm a Spinner widget (QComboBox
        on Android) is present.  Its default text should be '18+'.
        Gotcha (E): class name is android.widget.Spinner, not QComboBox.
        """
        assert False, "todo: implement"


# ===========================================================================
# Category 3: Image shown after fetch
# ===========================================================================
#
# Goal (coarse): after pressing Fetch and waiting for completion, a non-blank
# image should be visible in the right ~1/3 of the content area.
#
# 'Non-blank' = the pixel standard deviation in that region > threshold,
# indicating the image pane is not showing a solid-colour placeholder.

class TestImageShownAfterFetch(unittest.TestCase):
    """Category 3: verify a non-blank image appears after fetch completes"""
    

    @requires_device
    @pytest.mark.skipif(not _PIL_AVAILABLE, reason="Pillow (PIL) not installed — pip install Pillow")
    def test_image_region_nonblank(self):
        """Image pane region should have pixel std_dev > 15 after a successful fetch.

        Implementation steps:
          1. Clear logcat, then launch the app.
          2. Poll logcat for '_on_image: loadFromData ok=True' — this confirms Qt
             actually decoded and displayed the image (not just that generation ran).
             Falls back to checking 'generate_image() =>' if the ok=True marker
             never appears (e.g. old build without the trace).
          3. Take a screenshot via _take_screenshot().
          4. Load with PIL.Image.open(); get width × height from wm size.
          5. Crop the image-pane region: right 33 % of the content area
             (columns from width*2//3 to width), rows from 28 % to 72 % of
             screen height — skips the status bar + form fields above the image
             pane, and the Fetch/Quit button row below it.
          6. Compute per-channel std dev of the crop and assert the maximum
             across R/G/B channels exceeds IMAGE_STDDEV_THRESHOLD.

        Gotchas:
          (C) Use logcat polling, not time.sleep, to detect completion.
          (D) Crop bounds are derived from screen size reported by `adb shell wm size`
              rather than hardcoded coordinates.
          (F) Clear logcat before launching so old log lines don't give a false positive.

          FALSE POSITIVE RISK: 'Image decode failed.' text in the image pane has high
          std_dev (~40) due to white text on dark background.  The primary check uses
          the logcat marker '_on_image: loadFromData ok=True' to confirm the real image
          was rendered before measuring pixel variance.  Using only std_dev is not enough.

          A blank solid-colour placeholder has std_dev < 5; a real image exceeds 30;
          error text ('Image decode failed.') has ~40 — so std_dev alone cannot distinguish
          a real image from an error label.  The logcat marker is the authoritative check.

        Potential failure modes:
          - loadFromData() fails on Android (JPEG/WebP Qt plugin missing) →
            logcat shows '_on_image: loadFromData ok=False' → assert fails correctly.
            Fix: poe_client.py converts to PNG via PIL before returning bytes.
          - Image pane ends up outside the right-33%-crop if layout changed.
            Adjust crop fractions to match actual layout.
        """
        IMAGE_STDDEV_THRESHOLD = 15
        # Primary marker: the new trace we added in main.py confirms Qt loaded the image
        IMAGE_LOAD_SUCCESS_MARKER = "_on_image: loadFromData ok=True"
        IMAGE_GEN_MARKER = "generate_image() =>"

        # Step 1: clear logcat, launch app
        _clear_logcat()
        result = _run_adb("shell", "am", "start", "-n", MAIN_ACTIVITY)
        self.assertEqual(result.returncode, 0,
                         f"am start failed: {result.stderr}")
        debug.trace(4, "test_image_region_nonblank: app started, polling logcat")

        # Step 2: poll logcat for image generation complete then display success
        gen_found = _poll_logcat_for(IMAGE_GEN_MARKER, timeout=FETCH_WAIT_SECS)
        if not gen_found:
            logcat_tail = _read_logcat()[-2000:]
            debug.trace(3, f"test_image_region_nonblank: gen timeout; logcat:\n{logcat_tail}")
        self.assertTrue(gen_found,
                        f"Timed out after {FETCH_WAIT_SECS}s waiting for "
                        f"'{IMAGE_GEN_MARKER}' — image generation may have failed")

        # Poll a bit more for the UI update (signal emitted on main thread)
        display_found = _poll_logcat_for(IMAGE_LOAD_SUCCESS_MARKER,
                                         timeout=5.0, poll_interval=1.0)
        logcat_text = _read_logcat()
        load_ok_false = "_on_image: loadFromData ok=False" in logcat_text
        debug.trace(3, f"test_image_region_nonblank: display_found={display_found} "
                    f"load_ok_false={load_ok_false}")
        if load_ok_false:
            self.fail("_on_image: loadFromData returned False — Qt cannot decode the image. "
                      "Check that Pillow is in buildozer.spec requirements and poe_client.py "
                      "converts non-PNG images before returning.")
        self.assertTrue(display_found,
                        f"'{IMAGE_LOAD_SUCCESS_MARKER}' not found in logcat — "
                        "image was generated but Qt failed to display it. "
                        "Check logcat for '_on_image: loadFromData ok=' to diagnose.")

        # Extra pause for Qt to render to screen
        time.sleep(2)

        # Step 3: take screenshot
        local_path = "/tmp/rt_image_test.png"
        _take_screenshot(local_path)
        self.assertTrue(pathlib.Path(local_path).exists(),
                        f"Screenshot not pulled to {local_path}")

        # Step 4: load image and determine screen dimensions
        screen_w, screen_h = _get_screen_bounds_from_uiautomator()
        img = _PILImage.open(local_path).convert("RGB")
        # Use screenshot's actual size if it differs from wm size (e.g. rotation)
        img_w, img_h = img.size
        debug.trace(4, f"test_image_region_nonblank: screenshot {img_w}x{img_h} "
                    f"screen {screen_w}x{screen_h}")

        # Step 5: crop image-pane region (right 33 %, middle 28-72 % vertically)
        # top 28%: skips status bar and form-field rows (Date, Prompt, etc.)
        # bottom 72%: excludes the Fetch/Quit button row below the image pane
        left   = img_w * 2 // 3
        right  = img_w
        top    = img_h * 28 // 100
        bottom = img_h * 72 // 100
        crop = img.crop((left, top, right, bottom))
        debug.trace(4, f"test_image_region_nonblank: crop box ({left},{top})→({right},{bottom}) "
                    f"size={crop.size}")

        # Always save both outputs for visual inspection regardless of pass/fail
        crop_path = "/tmp/rt_image_crop.png"
        annotated_path = "/tmp/rt_screenshot_annotated.png"
        crop.save(crop_path)
        try:
            from PIL import ImageDraw  # pylint: disable=import-outside-toplevel
            ann = img.copy()
            draw = ImageDraw.Draw(ann)
            draw.rectangle([left, top, right - 1, bottom - 1], outline=(255, 0, 0), width=4)
            ann.save(annotated_path)
        except Exception:                # pylint: disable=broad-exception-caught
            system.print_exception_info("test_image_region_nonblank annotate")
        print(f"\n  Screenshot : {local_path}")
        print(f"  Annotated  : {annotated_path}  (red box = crop region)")
        print(f"  Cropped    : {crop_path}")

        # Step 6: compute per-channel std dev and assert above threshold
        import statistics  # stdlib — no extra dep  # pylint: disable=import-outside-toplevel
        pixels = list(crop.getdata())
        r_vals = [p[0] for p in pixels]
        g_vals = [p[1] for p in pixels]
        b_vals = [p[2] for p in pixels]
        r_std = statistics.stdev(r_vals)
        g_std = statistics.stdev(g_vals)
        b_std = statistics.stdev(b_vals)
        max_std = max(r_std, g_std, b_std)
        print(f"  Pixel std  : R={r_std:.1f} G={g_std:.1f} B={b_std:.1f} "
              f"max={max_std:.1f} threshold={IMAGE_STDDEV_THRESHOLD}")
        debug.trace(3, f"test_image_region_nonblank: R_std={r_std:.1f} G_std={g_std:.1f} "
                    f"B_std={b_std:.1f} max={max_std:.1f} threshold={IMAGE_STDDEV_THRESHOLD}")
        self.assertGreater(
            max_std, IMAGE_STDDEV_THRESHOLD,
            f"Image pane region looks blank (max channel std_dev={max_std:.1f} "
            f"≤ {IMAGE_STDDEV_THRESHOLD}). "
            f"Check logcat for '_on_image: loadFromData ok=' to diagnose."
        )

    @requires_device
    @pytest.mark.xfail(reason="todo: implement")
    def test_image_shown_for_each_age_group(self):
        """An image should load for every age group (spot-check '18+' and '3-5').
        
        Repeat test_image_region_nonblank twice, selecting a different age group
        from the spinner before each fetch.  Ensures the age-group filter is not
        breaking image generation for any group.
        """
        assert False, "todo: implement"


# ===========================================================================
# Category 4: Debug pane / logcat verification
# ===========================================================================
#
# Goal: after a fetch, the debug pane's content (written to logcat by
# _set_debug_info) should contain key fields: date, age_group, text_model,
# image_prompt.  This is a lightweight integration sanity check.

class TestDebugOutput(unittest.TestCase):
    """Category 4: verify expected keys appear in logcat after a fetch"""
    

    @requires_device
    @pytest.mark.xfail(reason="todo: implement — logcat tag may differ across Android versions")
    def test_debug_keys_in_logcat(self):
        """After one fetch, logcat must contain 'text_model=', 'image_prompt:', and 'age_group='.
        
        Steps:
          1. `adb logcat -c` to clear buffer.
          2. Launch app and wait for auto-fetch to complete (poll for 'fetch_done'
             in logcat or sleep FETCH_WAIT_SECS).
          3. Read logcat: `_read_logcat(tag=LOGCAT_TAG)`.
          4. Assert each of the three key strings appears at least once.
        
        Gotchas:
          (F) If the python logcat tag is wrong for this build, all lines will be
              missing.  Check with `adb logcat | grep -i tidbit` to find the actual tag.
          (C) Avoid sleeping the full FETCH_WAIT_SECS — poll in 2-second increments.
        """
        assert False, "todo: implement"

    @requires_device
    @pytest.mark.xfail(reason="todo: implement")
    def test_no_exception_in_logcat(self):
        """logcat should not contain Python tracebacks after a normal fetch.
        
        After a successful fetch, read logcat and assert that 'Traceback' and
        'Exception' do not appear in the python-tagged output.
        Gotcha: some debug-level exception logging (e.g. print_exception_info)
        may use 'Exception' in non-error context — filter to lines that also
        contain 'Error' or 'Traceback'.
        """
        assert False, "todo: implement"


# ===========================================================================
# Category 5: Stability — no crash under repeated / edge-case use
# ===========================================================================
#
# Goal: the app must not crash when Fetch is pressed multiple times, when an
# unusual age group is selected, or when the network is slow.

class TestStability(unittest.TestCase):
    """Category 5: coarse stability checks — no ANR or crash dialog"""
    

    @requires_device
    @pytest.mark.xfail(reason="todo: implement — timing is fragile without logcat polling")
    def test_no_crash_after_three_fetches(self):
        """The app must remain alive after three sequential Fetch button presses.
        
        Steps:
          1. Launch app.
          2. Repeat 3×: tap Fetch button, poll logcat for 'fetch_done', tap again.
          3. After all three, dump the UI hierarchy.
          4. Assert no crash dialog text ('Unfortunately', 'has stopped') is present.
        
        Gotcha (C): each fetch takes up to FETCH_WAIT_SECS; total wall time may
        exceed 2.5 minutes.  Mark this test as slow and skip in quick CI runs.
        Gotcha: on_fetch() guards against re-entrant calls (worker already running),
        so pressing Fetch while a fetch is in progress is a no-op — wait for
        completion between presses.
        """
        assert False, "todo: implement"

    @requires_device
    @pytest.mark.xfail(reason="todo: implement")
    def test_no_anr_on_slow_network(self):
        """The UI should remain responsive (no ANR) even if the network is slow.
        
        Enable network throttling: `adb shell tc qdisc add dev wlan0 root netem delay 3000ms`
        (requires root; on an AVD use the emulator's network throttle settings instead).
        Tap Fetch and immediately tap elsewhere in the UI.  Assert no ANR dialog appears
        within 15 seconds.  Restore network: `adb shell tc qdisc del dev wlan0 root`.
        
        This test validates the QThread background-fetch design — if fetch were on the
        main thread the UI would freeze and Android would show an ANR.
        """
        assert False, "todo: implement"


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
