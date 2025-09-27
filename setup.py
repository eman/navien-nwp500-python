from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="navilink",
    version="1.0.0",
    author="Emmanuel Jarvis",
    description="Production-ready Python library for Navien NaviLink service",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/navilink/navilink-python",
    packages=find_packages(exclude=["tests*", "examples*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Home Automation",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="navien navilink water heater heat pump iot smart home",
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "isort>=5.0.0",
            "mypy>=1.0.0",
            "flake8>=5.0.0",
        ],
        "analysis": [
            "pandas>=1.5.0",
            "matplotlib>=3.5.0",
            "numpy>=1.21.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "navilink-monitor=examples.tank_monitoring_production:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/navilink/navilink-python/issues",
        "Source": "https://github.com/navilink/navilink-python",
        "Documentation": "https://github.com/navilink/navilink-python/blob/main/README.md",
    },
)