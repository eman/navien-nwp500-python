# Version Management

This document explains how version management works in the navien-nwp500 package.

## Version Management Strategy

The package uses **static versioning** defined in `pyproject.toml` for reliable and consistent builds across all environments.

### Why Static Versioning?

- **Reliable builds**: Same version number every time, regardless of git state
- **Archive compatibility**: Works with GitHub archive downloads
- **Simpler CI/CD**: No dependency on git history or setuptools-scm in build process
- **Clear versioning**: Explicit version numbers in source code

## Version Configuration

### Primary Version Source: `pyproject.toml`

```toml
[project]
version = "1.2.2"
```

### Fallback Configuration

1. **setuptools-scm fallback** in `pyproject.toml`:
   ```toml
   [tool.setuptools_scm]
   fallback_version = "1.2.2"
   ```

2. **Python fallback** in `navien_nwp500/__init__.py`:
   ```python
   try:
       from ._version import __version__
   except ImportError:
       __version__ = "1.2.2"
   ```

## Version Bumping Workflow

### Automated Script: `scripts/bump_version.py`

The script handles all aspects of version bumping:

```bash
# Patch version (1.2.2 → 1.2.3)
python scripts/bump_version.py patch

# Minor version (1.2.2 → 1.3.0)  
python scripts/bump_version.py minor

# Major version (1.2.2 → 2.0.0)
python scripts/bump_version.py major

# Custom version
python scripts/bump_version.py custom --version 1.5.0

# Dry run (see what would be changed)
python scripts/bump_version.py patch --dry-run

# Bump and push tag immediately
python scripts/bump_version.py patch --push
```

### What the Script Does

1. **Reads current version** from `pyproject.toml`
2. **Calculates new version** based on semantic versioning rules
3. **Updates multiple files**:
   - `pyproject.toml` - primary version
   - `pyproject.toml` - setuptools-scm fallback_version
   - `navien_nwp500/__init__.py` - Python fallback version  
   - `CHANGELOG.md` - release notes
4. **Creates git commit** with version changes
5. **Creates git tag** (`v1.2.3`)
6. **Optionally pushes tag** to trigger CI/CD

### Manual Version Updates

If you need to update versions manually:

1. **Update `pyproject.toml`**:
   ```toml
   version = "1.2.3"
   ```

2. **Update setuptools-scm fallback**:
   ```toml
   [tool.setuptools_scm]
   fallback_version = "1.2.3"
   ```

3. **Update Python fallback**:
   ```python
   __version__ = "1.2.3"
   ```

4. **Update CHANGELOG.md**
5. **Commit and tag**:
   ```bash
   git add .
   git commit -m "Bump version to 1.2.3"
   git tag -a v1.2.3 -m "Release version 1.2.3"
   ```

## Release Process

### 1. Prepare Release

```bash
# Ensure you're on main branch with latest changes
git checkout main
git pull origin main

# Bump version (creates commit and tag)
python scripts/bump_version.py patch

# Push changes and tag
git push origin main
git push origin v1.2.3
```

### 2. GitHub Actions

When a version tag is pushed:
- Builds package with static version
- Runs tests across Python versions
- Publishes to PyPI automatically

### 3. Verify Release

- Check [PyPI](https://pypi.org/project/navien-nwp500/) for new version
- Test installation: `pip install navien-nwp500==1.2.3`
- Verify version: `python -c "import navien_nwp500; print(navien_nwp500.__version__)"`

## Development Versioning

### Development Builds

During development, the version system provides:

- **Static version** from `pyproject.toml` for build tools
- **Dynamic version** from `_version.py` (if available from setuptools-scm)
- **Fallback version** if neither is available

### Local Development

```bash
# Install in development mode
pip install -e .

# Check current version
python -c "import navien_nwp500; print(navien_nwp500.__version__)"

# Build package locally
python -m build
```

## Troubleshooting

### Version Mismatch

If you see different versions in different contexts:

1. **Check pyproject.toml**: `grep version pyproject.toml`
2. **Check Python package**: `python -c "import navien_nwp500; print(navien_nwp500.__version__)"`
3. **Rebuild if needed**: `pip install -e .`

### setuptools-scm Issues

The package no longer depends on setuptools-scm for builds, but it's kept for development convenience:

- **Build issues**: Use static version from pyproject.toml
- **Development versions**: setuptools-scm provides git-based versions
- **Archive builds**: Always use static fallback

### CI/CD Issues

- **Missing version**: Check pyproject.toml has `version = "x.y.z"`
- **Wrong version**: Ensure all files are updated consistently
- **Build failures**: Verify static version is valid semver

## Migration Notes

### From setuptools-scm Only

The package previously used only setuptools-scm. The current hybrid approach:

- **Maintains compatibility** with existing workflows
- **Adds reliability** with static versioning
- **Improves build consistency** across environments

### Version File Locations

- ✅ **Primary**: `pyproject.toml` - `version = "1.2.3"`
- ✅ **Fallback**: `pyproject.toml` - `fallback_version = "1.2.3"`
- ✅ **Python**: `navien_nwp500/__init__.py` - `__version__ = "1.2.3"`
- 📝 **Generated**: `navien_nwp500/_version.py` (if setuptools-scm runs)