#!/usr/bin/env python3
"""
Setup script for PhotosSorter package.
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
requirements_file = this_directory / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="photos-sorter",
    version="1.0.0",
    author="PhotosSorter Team",
    author_email="",
    description="Automatic photo and video organizer that sorts files by date using EXIF metadata",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/abshka/PhotosSorter",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Graphics",
        "Topic :: System :: Filesystems",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "video": ["ffmpeg-python>=0.2.0"],
        "dev": ["pytest>=7.0.0", "black>=22.0.0", "flake8>=4.0.0"],
    },
    entry_points={
        "console_scripts": [
            "photos-sorter=photos_sorter:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml"],
    },
    keywords="photos videos organize exif metadata sorting",
    project_urls={
        "Bug Reports": "https://github.com/abshka/PhotosSorter/issues",
        "Source": "https://github.com/abshka/PhotosSorter",
        "Documentation": "https://github.com/abshka/PhotosSorter#readme",
    },
)
