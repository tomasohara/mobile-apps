#! /usr/bin/env python

"""python-for-android build hooks."""

import os
import glob
import logging

def patch_build_py(build_py):
    """
    Patch build.py to append PYTHONUTF8=1 to p4a_env_vars.txt.
    This prevents the Python 3.11+ filesystem encoding crash on Android
    without needing to recompile start.c via ndk-build.
    """
    logger = logging.getLogger('p4a.hook')

    target_code = 'f.write("P4A_MINSDK=" + str(args.min_sdk_version) + "\\n")'
    
    patch_code = """
        # Force Python 3.11+ to use UTF-8 filesystem encoding
        f.write("PYTHONUTF8=1\\n")
"""
    
    full_target = target_code
    full_replacement = target_code + patch_code

    try:
        with open(build_py, 'r', encoding="utf-8") as f:
            content = f.read()

        if full_replacement in content:
            return "already_patched"

        if full_target in content:
            content = content.replace(full_target, full_replacement)
            with open(build_py, 'w', encoding="utf-8") as f:
                f.write(content)
            return "patched"
            
    except Exception as e:
        logger.error("p4a_hook error: Failed to read/write %s: %s", build_py, e)
    
    return "not_found"

def before_apk_build(toolchain):
    """
    p4a hook to patch build.py before APK build.
    """
    logger = logging.getLogger('p4a.hook')
    logger.info("Running p4a_hook to patch build.py for filesystem encoding bug...")

    # Disable -OO optimization so __debug__=True at runtime (Python 3.11 inlines
    # __debug__ as a compile-time constant; -OO bakes in False permanently).
    # build.py checks NO_OPTIMIZE_PYTHON before calling compileall.
    os.environ.setdefault('NO_OPTIMIZE_PYTHON', '1')
    logger.info("p4a_hook: NO_OPTIMIZE_PYTHON=%s", os.environ.get('NO_OPTIMIZE_PYTHON'))

    build_dir = toolchain.ctx.build_dir
    # Patch the global build.py template
    platform_dir = os.path.dirname(build_dir)
    p4a_dir = os.path.join(platform_dir, 'python-for-android')
    if not os.path.isdir(p4a_dir):
        p4a_dir = os.path.join(platform_dir, '..', 'python-for-android')

    all_build_files = []
    if os.path.isdir(p4a_dir):
        p4a_source_build_py = os.path.join(
            p4a_dir,
            "pythonforandroid", "bootstraps", "common", "build", "build.py"
        )
        all_build_files.append(p4a_source_build_py)
    
    # Also patch build.py inside the actual dist folders
    arch_dir = os.path.dirname(build_dir)
    patterns = [
        os.path.join(build_dir, "bootstrap_builds", "*", "build.py"),
        os.path.join(arch_dir, "dists", "*", "build.py")
    ]
    for pattern in patterns:
        all_build_files.extend(glob.glob(pattern))

    patched_count = 0
    for build_py in set(all_build_files):
        if not os.path.exists(build_py):
            continue
        result = patch_build_py(build_py)
        if result == "patched":
            logger.info("p4a_hook: Patched %s", build_py)
            patched_count += 1
        elif result == "already_patched":
            logger.info("p4a_hook: %s is already patched.", build_py)
        else:
            logger.warning("p4a_hook: Target code not found in %s.", build_py)

    if patched_count == 0:
        logger.info("p4a_hook: No files were patched (they may have been patched already).")
