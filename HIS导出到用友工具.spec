# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['test.py'],
    pathex=[],
    binaries=[],
    datas=[('requirements.txt', '.'), ('lib/instantclient_11_21', 'instantclient_11_21')],
    hiddenimports=['pandas', 'openpyxl', 'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets'],
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
    name='HIS导出到用友工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='x64',
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
)
