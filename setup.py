#!/usr/bin/env python
"""Setup configuration for pixibox-ue5-bridge package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pixibox-ue5-bridge",
    version="2.1.0",
    author="Pixibox.ai",
    author_email="dev@pixibox.ai",
    description="Python bridge for seamless Pixibox.ai to Unreal Engine 5 integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pixibox-ai/ue5-bridge",
    project_urls={
        "Bug Tracker": "https://github.com/pixibox-ai/ue5-bridge/issues",
        "Documentation": "https://pixibox.ai/plugins/unreal/docs",
        "Source Code": "https://github.com/pixibox-ai/ue5-bridge",
    },
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Graphics :: 3D",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.28.0",
        "websockets>=10.0",
        "aiohttp>=3.8.0",
        "click>=8.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.20.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.990",
            "isort>=5.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pixibox-ue5-bridge=pixibox_ue5.cli:main",
        ],
    },
)
