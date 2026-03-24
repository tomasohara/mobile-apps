"""python-for-android build hooks."""
import os
import glob
import logging

def patch_start_c(start_c):
    """
    Directly set the filesystem encoding in PyConfig to avoid auto-detection
    bugs on Android during Python 3.11+ initialization.
    """
    logger = logging.getLogger('p4a.hook')

    target_code = "      PyConfig_InitPythonConfig(&config);"
    
    patch_code = """
      #if PY_VERSION_HEX >= 0x030B0000
      // In Python 3.11+, the filesystem encoding detection on Android can fail.
      // Explicitly set it to UTF-8 to prevent a crash during initialization.
      PyConfig_SetString(&config, &config.filesystem_encoding, L"utf-8");
      PyConfig_SetString(&config, &config.filesystem_errors, L"surrogateescape");
      #endif
"""
    
    full_target = target_code
    full_replacement = target_code + patch_code

    try:
        with open(start_c, 'r', encoding="utf-8") as f:
            content = f.read()

        if full_replacement in content:
            return "already_patched"

        if full_target in content:
            content = content.replace(full_target, full_replacement)
            with open(start_c, 'w', encoding="utf-8") as f:
                f.write(content)
            return "patched"
            
    except Exception as e:
        logger.error("p4a_hook: Failed to read/write %s: %s", start_c, e)
    
    return "not_found"

def before_apk_build(toolchain):
    """
    p4a hook to patch start.c before APK build.
    """
    logger = logging.getLogger('p4a.hook')
    logger.info("Running p4a_hook to patch start.c for filesystem encoding bug...")

    # Robustly find the p4a source dir by going up from the build_dir
    platform_dir = os.path.dirname(toolchain.ctx.build_dir)
    p4a_dir = os.path.join(platform_dir, 'python-for-android')

    if not os.path.isdir(p4a_dir):
        logger.error("p4a_hook: Could not determine python-for-android directory. Looked in %s", p4a_dir)
        return

    p4a_source_start_c = os.path.join(
        p4a_dir,
        "pythonforandroid", "bootstraps", "common", "build",
        "jni", "application", "src", "start.c"
    )

    all_start_files = [p4a_source_start_c]
    
    build_dir = toolchain.ctx.build_dir
    patterns = [
        os.path.join(build_dir, "bootstrap_builds", "*", "jni", "application", "src", "start.c"),
        os.path.join(build_dir, "dists", "*", "jni", "application", "src", "start.c")
    ]
    for pattern in patterns:
        all_start_files.extend(glob.glob(pattern))

    patched_count = 0
    for start_c in set(all_start_files):
        if not os.path.exists(start_c):
            continue
        result = patch_start_c(start_c)
        if result == "patched":
            logger.info("p4a_hook: Patched %s", start_c)
            patched_count += 1
        elif result == "already_patched":
            logger.info("p4a_hook: %s is already patched.", start_c)
        else:
            logger.warning("p4a_hook: Target code not found in %s.", start_c)

    if patched_count == 0:
        logger.info("p4a_hook: No C files were patched (they may have been patched already).")
