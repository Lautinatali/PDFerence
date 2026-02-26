"""
Setup configuration for PDFerence package.
Allows installation via: pip install -e .
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pdfference",
    version="0.2.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="PDF metadata processor with Obsidian vault integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pdfference",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.31.0",
        "PyMuPDF>=1.23.0",
        "beautifulsoup4>=4.12.0",
        "python-dotenv>=1.0.0",
        "streamlit>=1.28.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
)
