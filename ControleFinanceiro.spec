# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import json
import os
import runpy

root = Path(SPECPATH)
hiddenimports = sorted('views.' + p.stem for p in (root / 'views').glob('*.py') if p.stem != '__init__')
manifest = Path(workpath) / 'view-manifest.json'
manifest.parent.mkdir(parents=True, exist_ok=True)
manifest.write_text(json.dumps(hiddenimports), encoding='utf-8')


a = Analysis(
    ['run.py'],
    pathex=[str(root)],
    binaries=[],
    datas=[('assets', 'assets'), (str(manifest), '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
if os.name == 'nt':
    runtime_helper = runpy.run_path(str(root / 'packaging/windows/runtime_binaries.py'))
    a.binaries = runtime_helper['replace_runtime'](a.binaries, os.environ['FINANCE_ASSIST_MSVC_REDIST'])
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ControleFinanceiro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
