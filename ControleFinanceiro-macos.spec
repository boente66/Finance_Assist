# -*- mode: python ; coding: utf-8 -*-
import json
from pathlib import Path

root = Path(SPECPATH)
hiddenimports = sorted(
    'views.' + path.stem
    for path in (root / 'views').glob('*.py')
    if path.stem != '__init__'
)
if not hiddenimports or 'views.resumo_financeiro_view' not in hiddenimports:
    raise RuntimeError('Inventário de views incompleto')
manifest = Path(workpath) / 'view-manifest.json'
manifest.parent.mkdir(parents=True, exist_ok=True)
manifest.write_text(json.dumps(hiddenimports), encoding='utf-8')

a = Analysis(
    ['run.py'], pathex=[str(root)], binaries=[],
    datas=[('assets', 'assets'), (str(manifest), '.')],
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=['pytest', '_pytest'], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='FinanceAssist-test', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)
app = BUNDLE(
    exe,
    name='Finance Assist Test.app',
    icon=None,
    bundle_identifier='br.com.financeassist.test',
    info_plist={
        'CFBundleDisplayName': 'Finance Assist (Teste)',
        'NSHighResolutionCapable': True,
    },
)
