# Copyright (C) 2023 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from pythonforandroid.logger import info
from pythonforandroid.recipe import PythonRecipe


class ShibokenRecipe(PythonRecipe):
    version = '6.10.1'

    call_hostpython_via_targetpython = False
    install_in_hostpython = False

    def build_arch(self, arch):
        ''' Unzip the wheel and copy into site-packages of target'''
        wheel_arch = "aarch64" if arch.arch == "arm64-v8a" else "x86_64"
        wheel_path = f'/home/tomohara/Downloads/shiboken6-6.10.1-6.10.1-cp311-cp311-android_{wheel_arch}.whl'
        ## TODO2: wheel_path = f'deployment/wheels/shiboken6-6.10.1-6.10.1-cp311-cp311-android_{wheel_arch}.whl'

        info('Installing {} into site-packages'.format(self.name))
        with zipfile.ZipFile(wheel_path, 'r') as zip_ref:
            info('Unzip wheels and copy into {}'.format(self.ctx.get_python_install_dir(arch.arch)))
            zip_ref.extractall(self.ctx.get_python_install_dir(arch.arch))

        lib_dir = Path(f"{self.ctx.get_python_install_dir(arch.arch)}/shiboken6")
        shutil.copyfile(lib_dir / "libshiboken6.abi3.so",
                        Path(self.ctx.get_libs_dir(arch.arch)) / "libshiboken6.abi3.so")


recipe = ShibokenRecipe()
