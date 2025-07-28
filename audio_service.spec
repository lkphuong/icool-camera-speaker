# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['audio_service_wrapper.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'win32timezone',
        'pywintypes',
        'win32api',
        'win32con',
        'win32event',
        'win32evtlogutil',
        'win32service',
        'win32serviceutil',
        'servicemanager',
        'websockets',
        'pyaudio',
        'pycaw',
        'comtypes',
        'asyncio',
        'json',
        'base64',
        'logging',
        'datetime',
        'glob',
        'platform'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AudioSocketService',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
