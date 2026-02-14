#!/usr/bin/env python3
"""
Build script for creating PyInstaller executable.

Usage:
    python build_exe.py

This creates a standalone executable at dist/revvel that can be
distributed without requiring Python to be installed.

Audio processing provided by free and open-source libraries.
"""

import os
import sys
import subprocess


def build():
    """Build the PyInstaller executable."""
    project_dir = os.path.dirname(os.path.abspath(__file__))

    # PyInstaller spec
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
# Revvel Music Studio - PyInstaller Spec
# Audio processing provided by free and open-source libraries.

import os
import sys

block_cipher = None

a = Analysis(
    ['{os.path.join(project_dir, "cli", "main.py")}'],
    pathex=['{project_dir}'],
    binaries=[],
    datas=[
        ('{os.path.join(project_dir, "engine")}', 'engine'),
        ('{os.path.join(project_dir, "models")}', 'models'),
    ],
    hiddenimports=[
        'numpy',
        'scipy',
        'scipy.signal',
        'librosa',
        'soundfile',
        'noisereduce',
        'pydub',
        'edge_tts',
        'pyloudnorm',
        'engine',
        'engine.cleanup',
        'engine.mastering',
        'engine.separation',
        'engine.voice',
        'engine.video',
        'engine.distribution',
    ],
    hookspath=[],
    hooksconfig={{}},
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
    name='revvel',
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
"""

    spec_path = os.path.join(project_dir, "revvel.spec")
    with open(spec_path, "w") as f:
        f.write(spec_content)

    print("Building Revvel Music Studio executable...")
    print(f"Spec file: {spec_path}")

    # Run PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        spec_path,
    ]

    result = subprocess.run(cmd, cwd=project_dir)

    if result.returncode == 0:
        exe_path = os.path.join(project_dir, "dist", "revvel")
        print(f"\n✓ Build successful!")
        print(f"  Executable: {exe_path}")
        print(f"\n  Usage: ./dist/revvel --help")
    else:
        print(f"\n✗ Build failed with exit code {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    build()
