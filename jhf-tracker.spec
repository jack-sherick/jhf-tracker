# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_all

extra_datas, extra_binaries, extra_hiddenimports = [], [], []
if sys.platform == 'darwin':
    for pkg in ('objc', 'pystray'):
        d, b, h = collect_all(pkg)
        extra_datas += d
        extra_binaries += b
        extra_hiddenimports += h

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=extra_binaries,
    datas=[('assets/stoke.png', 'assets')] + extra_datas,
    hiddenimports=extra_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='jhf-tracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=sys.platform == 'win32',
    icon='assets/stoke.ico' if sys.platform == 'win32' else None,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='jhf-tracker.app',
        bundle_identifier='com.jhf-tracker',
        icon='assets/stoke.icns',
        info_plist={'LSUIElement': True},
    )
