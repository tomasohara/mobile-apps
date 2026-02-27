from __future__ import annotations

import zipfile
from pathlib import Path

from pythonforandroid.logger import info
from pythonforandroid.recipe import PythonRecipe


class Urllib3Recipe(PythonRecipe):
    version = '2.6.3'
    wheel_path = str(Path(__file__).resolve().parents[2] / 'wheels' / 'urllib3-2.6.3-py3-none-any.whl')
    depends = []
    call_hostpython_via_targetpython = False
    install_in_hostpython = False

    def build_arch(self, arch):
        """Unzip the wheel and copy into site-packages of target"""
        info(f'Installing {self.name} into site-packages')
        with zipfile.ZipFile(self.wheel_path, 'r') as zip_ref:
            zip_ref.extractall(self.ctx.get_python_install_dir(arch.arch))


recipe = Urllib3Recipe()
