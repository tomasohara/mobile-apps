# Copyright (C) 2023 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
from __future__ import annotations

import zipfile
from pathlib import Path

from pythonforandroid.logger import info
from pythonforandroid.recipe import PythonRecipe

# Only extract essential Python files (skip .pyi stubs, headers, cmake, etc.)
# The .abi3.so Python extension must be in site-packages for Python import.
_SITE_PREFIXES = (
    "shiboken6/__init__.py",
    "shiboken6/_config.py",
    "shiboken6/_git_shiboken_module_version.py",
    "shiboken6/Shiboken.abi3.so",
    "shiboken6-",  # dist-info
)


class ShibokenRecipe(PythonRecipe):
    version = '6.10.1'
    wheel_path = '/home/tomohara/Downloads/shiboken6-6.10.1-6.10.1-cp311-cp311-android_aarch64.whl'

    call_hostpython_via_targetpython = False
    install_in_hostpython = False

    def build_arch(self, arch):
        """Selectively extract only needed shiboken6 files."""
        site_dir = Path(self.ctx.get_python_install_dir(arch.arch))
        libs_dir = Path(self.ctx.get_libs_dir(arch.arch))

        info(f"Selectively installing {self.name} into {site_dir}")
        with zipfile.ZipFile(self.wheel_path, 'r') as zf:
            for member in zf.infolist():
                if any(member.filename.startswith(p) for p in _SITE_PREFIXES):
                    zf.extract(member, site_dir)

            # Copy native .so to libs/
            so_data = zf.read("shiboken6/libshiboken6.abi3.so")
            (libs_dir / "libshiboken6.abi3.so").write_bytes(so_data)
            info("Copied libshiboken6.abi3.so to libs/")


recipe = ShibokenRecipe()
