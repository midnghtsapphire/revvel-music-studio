"""
Revvel Music Studio - Setup
Audio processing provided by free and open-source libraries.
"""

from setuptools import setup, find_packages

setup(
    name="revvel-music-studio",
    version="1.0.0",
    description=(
        "Comprehensive music production and distribution studio "
        "for artist Revvel and label HOTRS (House of the Rising Sun). "
        "Audio processing provided by free and open-source libraries."
    ),
    author="Revvel",
    author_email="revvel@hotrs.music",
    url="https://github.com/MIDNGHTSAPPHIRE/revvel-music-studio",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "librosa>=0.10.0",
        "soundfile>=0.12.0",
        "noisereduce>=3.0.0",
        "pydub>=0.25.0",
        "pyloudnorm>=0.1.0",
        "edge-tts>=6.1.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-multipart>=0.0.6",
    ],
    extras_require={
        "separation": ["demucs>=4.0.0"],
        "exe": ["pyinstaller>=6.0.0"],
        "mcp": ["mcp>=1.0.0"],
        "all": [
            "demucs>=4.0.0",
            "pyinstaller>=6.0.0",
            "mcp>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "revvel=cli.main:main",
            "revvel-api=api.main:app",
            "revvel-mcp=mcp_server.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
        "Topic :: Multimedia :: Sound/Audio :: Editors",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
    ],
)
