# 📦 PyPI Setup and Publishing Guide

## What is PyPI?

**PyPI (Python Package Index)** is the official repository for Python packages. When you publish your package to PyPI, users can install it with:

```bash
pip install navien-nwp500
```

## 🚀 Complete Setup Process

### Step 1: Create PyPI Account

1. **Visit PyPI**: Go to https://pypi.org/account/register/
2. **Create Account**: 
   - Choose a username and password
   - Verify your email address
3. **Enable 2FA** (REQUIRED for package uploads):
   - Go to Account Settings → Security
   - Set up Two-Factor Authentication
   - **This is mandatory for uploading packages**

### Step 2: Create API Token

1. **Go to API Tokens**: https://pypi.org/manage/account/token/
2. **Create New Token**:
   - Token name: `navien-nwp500-github-actions` (or similar)
   - Scope: **"Entire account"** (for first upload)
   - Click "Create Token"
3. **Copy the Token**: 
   - Format: `pypi-AgEIcHlwaS5vcmcCJGZkNWY4...` (very long)
   - **Save this immediately** - you won't see it again!

### Step 3: Add Token to GitHub Secrets

1. **Go to your GitHub repository**: https://github.com/eman/navien-nwp500-python
2. **Navigate to Settings**:
   - Click "Settings" tab in your repo
   - Click "Secrets and variables" → "Actions"
3. **Add New Secret**:
   - Click "New repository secret"
   - Name: `PYPI_API_TOKEN`
   - Value: `pypi-AgEIcHlwaS5vcmcCJGZkNWY4...` (your full token)
   - Click "Add secret"

## 🔐 Security Best Practices

### API Token Security
- **Never commit tokens** to code repositories
- **Use scoped tokens** when possible (after first upload)
- **Regenerate tokens** periodically
- **Use different tokens** for different projects

### GitHub Secrets
- **Repository secrets** are encrypted and only accessible to GitHub Actions
- **Environment protection** can add additional security layers
- **Audit logs** track secret usage

## 🤖 Automated Publishing Workflow

Your repository already has the automated workflow configured! Here's how it works:

### Current Workflow (`.github/workflows/release.yml`)

```yaml
pypi-publish:
  needs: [build, github-release]
  runs-on: ubuntu-latest
  if: startsWith(github.ref, 'refs/tags/')
  environment:
    name: pypi
    url: https://pypi.org/p/navien-nwp500
  
  steps:
  - name: Download build artifacts
    uses: actions/download-artifact@v3
    with:
      name: dist
      path: dist/
  
  - name: Publish to PyPI
    uses: pypa/gh-action-pypi-publish@release/v1
    with:
      packages-dir: dist/
      verbose: true
```

### How It Triggers

1. **Tag Creation**: When you push a version tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **Automatic Process**:
   - ✅ Runs tests across multiple Python versions
   - ✅ Builds the package (wheel + source distribution)
   - ✅ Creates GitHub release with changelog
   - ✅ Uploads to PyPI automatically

## 📋 Manual Publishing (Backup Method)

If you need to publish manually:

```bash
# Install build tools
pip install build twine

# Build package
python -m build

# Upload to PyPI (will prompt for credentials)
python -m twine upload dist/*
# Username: __token__
# Password: pypi-AgEIcHlwaS5vcmcCJGZkNWY4... (your token)

# Or set environment variable
export TWINE_PASSWORD="pypi-your-token-here"
python -m twine upload -u __token__ dist/*
```

## 🧪 Testing with Test PyPI (Optional)

Before publishing to the main PyPI, you can test with Test PyPI:

### Setup Test PyPI
1. **Create account**: https://test.pypi.org/account/register/
2. **Create token**: https://test.pypi.org/manage/account/token/
3. **Add to GitHub Secrets**: `TEST_PYPI_API_TOKEN`

### Test Upload
```bash
# Upload to Test PyPI
python -m twine upload --repository testpypi dist/*

# Test install
pip install --index-url https://test.pypi.org/simple/ navien-nwp500
```

## 🚀 Your First Release Process

Here's exactly what to do for your first release:

### 1. Setup PyPI (One-time)
- [x] Create PyPI account with 2FA
- [x] Generate API token  
- [x] Add token to GitHub Secrets as `PYPI_API_TOKEN`

### 2. Create Release
```bash
cd /Users/emmanuel/Projects/navilink

# Ensure everything is committed
git status
git add -A
git commit -m "Prepare for v1.0.0 release"
git push origin main

# Create and push tag (triggers automated release)
git tag v1.0.0
git push origin v1.0.0
```

### 3. Monitor Release
- **GitHub Actions**: https://github.com/eman/navien-nwp500-python/actions
- **GitHub Releases**: https://github.com/eman/navien-nwp500-python/releases
- **PyPI Package**: https://pypi.org/project/navien-nwp500/ (after upload)

## 📊 After Publishing

### Verify Success
```bash
# Install your published package
pip install navien-nwp500

# Test it works
python -c "import navien_nwp500; print(navien_nwp500.__version__)"
```

### Package Statistics
- **Downloads**: View on PyPI package page
- **Versions**: Manage on PyPI project page
- **Usage**: Monitor via PyPI analytics

## 🔧 Package Configuration

Your package is already configured in `pyproject.toml`:

```toml
[project]
name = "navien-nwp500"
description = "Python library for Navien NWP500 Heat Pump Water Heaters"
authors = [{name = "Emmanuel Levijarvi", email = "emansl@gmail.com"}]
license = "MIT"
readme = "README.md"
keywords = ["navien", "nwp500", "water heater", "heat pump", "iot"]
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3.8",
    # ... more classifiers
]
```

## ❗ Troubleshooting

### Common Issues

#### 1. "Invalid credentials" Error
```bash
# Check your token format
echo $TWINE_PASSWORD  # Should start with "pypi-"

# Regenerate token on PyPI if needed
```

#### 2. "Package already exists" Error
```bash
# You can't overwrite existing versions
# Increment version and try again
git tag v1.0.1
git push origin v1.0.1
```

#### 3. "2FA Required" Error
- Ensure 2FA is enabled on your PyPI account
- Use API tokens instead of username/password

### GitHub Actions Debugging
```bash
# Check workflow logs
# Go to: Actions → Your workflow → View logs

# Common fixes:
# 1. Ensure PYPI_API_TOKEN secret exists
# 2. Check token permissions
# 3. Verify package builds successfully
```

## 🎯 Next Steps After Setup

1. **Complete PyPI setup** (account + token + GitHub secret)
2. **Create your first release** (`git tag v1.0.0 && git push origin v1.0.0`)
3. **Monitor the automated workflow**
4. **Verify package installation** (`pip install navien-nwp500`)
5. **Plan future releases** (v1.1.0, etc.)

## 📚 Resources

- **PyPI Help**: https://pypi.org/help/
- **Packaging Guide**: https://packaging.python.org/
- **GitHub Actions**: https://docs.github.com/en/actions
- **Twine Documentation**: https://twine.readthedocs.io/

---

**Ready to publish? Set up your PyPI account and token, then run `git tag v1.0.0 && git push origin v1.0.0`! 🚀**