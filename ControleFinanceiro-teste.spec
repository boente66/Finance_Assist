# -*- mode: python ; coding: utf-8 -*-
import json
import os
import runpy
from pathlib import Path

root = Path(SPECPATH)
# Enumerate source files without importing the package in PyInstaller's process.
# Its sys.path can omit the project when invoked through the venv entry point.
hiddenimports = sorted('views.' + p.stem for p in (root / 'views').glob('*.py') if p.stem != '__init__')
if not hiddenimports or 'views.resumo_financeiro_view' not in hiddenimports:
    raise RuntimeError('Inventário de views incompleto')
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
    excludes=['pytest', '_pytest'],
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
    name='FinanceAssist-test',
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
