# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

datas = [('living_storyworld/web', 'web')]
binaries = []
hiddenimports = [
    'living_storyworld',
    'living_storyworld.__main__',
    'living_storyworld.webapp',
    'living_storyworld.cli',
    'living_storyworld.desktop',
    'living_storyworld.generator',
    'living_storyworld.world',
    'living_storyworld.storage',
    'living_storyworld.models',
    'living_storyworld.config',
    'living_storyworld.presets',
    'living_storyworld.settings',
    'living_storyworld.image',
    'living_storyworld.wizard',
    'living_storyworld.tui',
    'living_storyworld.api',
    'living_storyworld.api.worlds',
    'living_storyworld.api.chapters',
    'living_storyworld.api.images',
    'living_storyworld.api.settings',
    'living_storyworld.api.generate',
    'living_storyworld.api.dependencies',
    'living_storyworld.providers',
    'living_storyworld.providers.text',
    'living_storyworld.providers.image',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'win32com',
    'win32com.client',
    'pythoncom',
    'pywintypes',
]

tmp_ret = collect_all('webview')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Collect Windows-specific dependencies
if os.name == 'nt':
    try:
        tmp_ret = collect_all('win32com')
        datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
    except Exception:
        pass


a = Analysis(
    ['living_storyworld/desktop.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='LivingStoryworld',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Show console for debugging (especially on Windows)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
