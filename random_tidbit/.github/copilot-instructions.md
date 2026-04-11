# Copilot instructions for random_tidbit

## Build and test commands

- Run the desktop app locally: `python main.py`
- Run the lightweight desktop smoke test: `QT_QPA_PLATFORM=offscreen pytest -q tests/test_main.py`
- Run a single Qt UI test: `QT_QPA_PLATFORM=offscreen pytest -q tests/test_ui_qt.py -k age_combo_items_and_default`
- Run the full desktop Qt UI suite: `QT_QPA_PLATFORM=offscreen pytest -v tests/test_ui_qt.py`
- Run the Android black-box suite against an installed APK: `pytest -v tests/test_android.py`
- Rebuild and redeploy the APK after Python or packaging changes before running Android tests: `buildozer android debug deploy`
- If you edit the vendored `mezcla/` tree, use its runner instead of inventing a new one:
  - Single Mezcla test selection: `TEST_REGEX='system' ./mezcla/tools/run_tests.bash`
  - Full Mezcla suite: `./mezcla/tools/run_tests.bash`

## High-level architecture

- `main.py` is both the desktop entry point and the Android app UI. It builds the full QWidget interface inline inside `main()`: date/prompt controls, optional advanced filters, result pane, image pane, and a collapsible debug pane.
- The fetch flow spans multiple layers. `main.py` starts `_FetchWorker` on a `QThread`; the worker calls `get_random_tidbit()` and `get_tidbit_image()`; those functions lazily load the repo-local `poe_client.py`; results are cached in `_fetch_cache` and persisted to `tidbit_cache.json`.
- `poe_client.py` wraps POE's OpenAI-compatible API for both text and image generation. Image generation first derives a safe visual prompt from the tidbit, then falls back to a chat-completions-based image download path when `/images/generations` is unavailable.
- Android packaging depends on several files working together, not just `buildozer.spec`. `buildozer.spec` uses the Qt bootstrap, pins a specific `python-for-android` checkout in `my-python-for-android/`, loads local recipes from `deployment/recipes`, ships extra Qt jars from `deployment/jar/PySide6/jar`, and runs `p4a_hook.py` to patch p4a's build behavior.
- Tests are split by layer. `tests/test_main.py` checks lightweight UI assumptions, `tests/test_ui_qt.py` covers desktop Qt behavior and cache handling with offscreen Qt, and `tests/test_android.py` treats the APK as a black box through `adb`, screenshots, and logcat.

## Key conventions

- Do not import the local `poe_client.py` at module import time from `main.py`. It is intentionally loaded lazily and by path so the app avoids Mezcla CLI side effects on import and still works when Android deploys only compiled `.pyc` files.
- Keep cache semantics stable: the cache key is `(date_str, age_group)`, the cache is written through `tidbit_cache.json`, and the startup fetch intentionally uses `bypass_cache=False` after the window is rendered.
- When changing the UI, remember that most widgets only exist as locals inside `main()`. The existing Qt tests explicitly point toward a future `build_ui()` extraction; if you need deeper widget-level tests, refactor in that direction instead of adding globals.
- Keep Android assumptions synchronized across files. Package/activity names in `tests/test_android.py` must match `buildozer.spec`, and `poe_client.py` must not be excluded from the APK source bundle.
- Preserve nearby `TODO`, `## OLD:`, and `## BAD:` comments when editing. This repo uses them as review history and as hints for future tests.
- The repo root already contains Mezcla-oriented instructions in `copilot-instructions.md`; use those only when working inside the vendored `mezcla/` subtree.
- Do not run `git commit` or `git push` without explicit user confirmation.
