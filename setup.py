#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="proxy-switch",
    version="0.1.0",
    description="One-click proxy configuration for Ubuntu servers",
    long_description=open("README.md").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="proxy-switch",
    url="https://github.com/user/proxy-switch",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "proxy-switch=proxy_switch.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Win32 (MS Windows)",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: System :: Networking",
        "Topic :: Utilities",
    ],
)
