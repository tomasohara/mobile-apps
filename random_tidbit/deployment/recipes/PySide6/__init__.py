# Copyright (C) 2023 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from pythonforandroid.logger import info
from pythonforandroid.recipe import PythonRecipe


# Only the Qt modules the app actually uses (Core, Gui, Widgets).
# Adding a module here will include both its native .so and PySide6 binding.
NEEDED_QT_MODULES = ["QtCore", "QtGui", "QtWidgets"]

# Prefixes to extract into site-packages (everything else is skipped).
# The .abi3.so Python extensions must be in site-packages for Python import.
# This keeps libpybundle.so small by excluding .pyi stubs,
# Qt/lib native libs, QML files, translations, jars, etc.
_SITE_PREFIXES = [
    "PySide6/__init__.py",
    "PySide6/_config.py",
    "PySide6/_git_pyside_version.py",
    "PySide6/libpyside6.abi3.so",
    "PySide6-",  # dist-info
] + [f"PySide6/{m}.abi3.so" for m in NEEDED_QT_MODULES]


## BAD: hardcoded aarch64 wheel path — x86_64 builds got no Qt6 native libs
## wheel_path = '/home/tomohara/Downloads/PySide6-6.10.1-6.10.1-cp311-cp311-android_aarch64.whl'

# Map p4a arch names to wheel filename suffixes
_ARCH_TO_WHEEL_SUFFIX = {
    "arm64-v8a": "aarch64",
    "x86_64": "x86_64",
}
_WHEEL_DIR = "/home/tomohara/Downloads"
_VERSION = "6.10.1"


class PySideRecipe(PythonRecipe):
    version = _VERSION
    # wheel_path is resolved per-arch in build_arch(); set a default for p4a introspection
    wheel_path = f"{_WHEEL_DIR}/PySide6-{_VERSION}-{_VERSION}-cp311-cp311-android_aarch64.whl"
    depends = ["shiboken6"]
    call_hostpython_via_targetpython = False
    install_in_hostpython = False

    def build_arch(self, arch):
        """Selectively extract only needed files from the PySide6 wheel."""
        suffix = _ARCH_TO_WHEEL_SUFFIX.get(arch.arch, arch.arch)
        self.wheel_path = (
            f"{_WHEEL_DIR}/PySide6-{_VERSION}-{_VERSION}-cp311-cp311-android_{suffix}.whl"
        )
        info(f"Using PySide6 wheel: {self.wheel_path}")
        libs_dir = Path(self.ctx.get_libs_dir(arch.arch))
        site_dir = Path(self.ctx.get_python_install_dir(arch.arch))

        info("Copying libc++_shared.so from NDK")
        libcpp = f"{self.ctx.ndk.sysroot_lib_dir}/{arch.command_prefix}/libc++_shared.so"
        shutil.copyfile(libcpp, libs_dir / "libc++_shared.so")

        with zipfile.ZipFile(self.wheel_path, "r") as zf:
            # 1) Extract only minimal Python files into site-packages
            info(f"Selectively installing {self.name} Python files into {site_dir}")
            for member in zf.infolist():
                if any(member.filename.startswith(p) for p in _SITE_PREFIXES):
                    zf.extract(member, site_dir)

            # 2) Copy only needed Qt native .so files into libs/
            info("Copying needed Qt native libraries")
            qt_lib_prefix = f"PySide6/Qt/lib/"
            needed_native = {f"libQt6{m[2:]}_{arch.arch}.so" for m in NEEDED_QT_MODULES}
            for member in zf.infolist():
                if not member.filename.startswith(qt_lib_prefix):
                    continue
                basename = member.filename.rsplit("/", 1)[-1]
                if basename in needed_native:
                    info(f"  -> {basename}")
                    (libs_dir / basename).write_bytes(zf.read(member.filename))

            # 3) Copy libpyside6.abi3.so and binding .abi3.so to libs/
            #    QtLoader needs these in the native libs dir before Python starts
            pyside_so = "PySide6/libpyside6.abi3.so"
            (libs_dir / "libpyside6.abi3.so").write_bytes(zf.read(pyside_so))
            info("Copied libpyside6.abi3.so to libs/")

            for mod in NEEDED_QT_MODULES:
                so_name = f"{mod}.abi3.so"
                wheel_path = f"PySide6/{so_name}"
                (libs_dir / so_name).write_bytes(zf.read(wheel_path))
                info(f"  -> {so_name}")

            # 4) Copy the Android platform plugin
            plugin_name = f"libplugins_platforms_qtforandroid_{arch.arch}.so"
            plugin_path = f"PySide6/Qt/plugins/platforms/{plugin_name}"
            try:
                (libs_dir / plugin_name).write_bytes(zf.read(plugin_path))
                info(f"  -> {plugin_name}")
            except KeyError:
                info(f"Warning: platform plugin {plugin_path} not found in wheel")

            # 5) Copy JPEG and WebP imageformat plugins so Qt can decode images
            # NOTE: qpng does NOT exist as a plugin — PNG is built into QtGui natively
            for fmt in ("qjpeg", "qwebp", "qgif"):
                img_plugin = f"libplugins_imageformats_{fmt}_{arch.arch}.so"
                img_path = f"PySide6/Qt/plugins/imageformats/{img_plugin}"
                try:
                    (libs_dir / img_plugin).write_bytes(zf.read(img_path))
                    info(f"  -> {img_plugin}")
                except KeyError:
                    info(f"Warning: imageformat plugin {img_path} not found in wheel")


recipe = PySideRecipe()
