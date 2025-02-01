from setuptools import setup, find_packages
import subprocess

# Ensure required Node.js packages are installed
subprocess.run(["npm", "install", "@mozilla/readability", "jsdom", "dompurify"], check=True)

setup(
    name="article_processor",
    version="1.0.0",
    author="Lucy",
    author_email="your.email@example.com",
    description="A Python package for processing web articles using Readability and JSDOM.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/article_processor",
    packages=find_packages(),
    install_requires=[
        "readabilipy",
        "readability-lxml",
        "asyncio"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "article_processor=article_processor.main:main"
        ],
    },
)
