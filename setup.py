# setup.py for navien-nwp500
# This provides fallback version handling for installations from GitHub archives
# where git metadata is not available for setuptools-scm

from setuptools import setup
import os

# Try to get version from setuptools-scm first
try:
    from setuptools_scm import get_version
    version = get_version(fallback_version="1.2.1")
except (ImportError, LookupError):
    # Fallback for when setuptools-scm can't detect version (e.g., GitHub archive)
    version = "1.2.1"
    
    # Write the version file manually if it doesn't exist
    version_file = os.path.join("navien_nwp500", "_version.py")
    if not os.path.exists(version_file):
        os.makedirs(os.path.dirname(version_file), exist_ok=True)
        with open(version_file, "w") as f:
            f.write(f'# Version file for navien-nwp500\n')
            f.write(f'# Fallback version for archive installations\n\n')
            f.write(f'__version__ = "{version}"\n')
            f.write(f'version = "{version}"\n')
            f.write(f'__version_tuple__ = {tuple(map(int, version.split(".")))}\n')
            f.write(f'version_tuple = {tuple(map(int, version.split(".")))}\n')
            f.write(f'__commit_id__ = commit_id = "unknown"\n')

setup(version=version)
