from __future__ import annotations

import zipfile
from pathlib import Path

from pythonforandroid.logger import info
from pythonforandroid.recipe import PythonRecipe


class CharsetNormalizerRecipe(PythonRecipe):
    version = '3.4.4'
    wheel_path = str(Path(__file__).resolve().parents[2] / 'wheels' / 'charset_normalizer-3.4.4-py3-none-any.whl')
    depends = []
    call_hostpython_via_targetpython = False
    install_in_hostpython = False

    def build_arch(self, arch):
        """Unzip the wheel and copy into site-packages of target"""
        info(f'Installing {self.name} into site-packages')
        with zipfile.ZipFile(self.wheel_path, 'r') as zip_ref:
            zip_ref.extractall(self.ctx.get_python_install_dir(arch.arch))


recipe = CharsetNormalizerRecipe()
