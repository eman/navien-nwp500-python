# 🚀 NaviLink Release Guide

## Step-by-Step Release Process

### Prerequisites ✅
- [x] Code is production-ready and tested
- [x] All tests passing locally
- [x] CHANGELOG.md updated
- [x] README.md reflects current features
- [ ] PyPI account setup
- [ ] GitHub repository configured

### 1. 📋 Pre-Release Checklist

```bash
# Ensure everything is committed and pushed
cd /Users/emmanuel/Projects/navilink
git status
git add -A
git commit -m "Prepare for v1.0.0 release"
git push origin main

# Run final tests
pytest tests/ -v
black --check .
isort --check-only .
```

### 2. 🏷️ Create Version Tag

```bash
# Create and push the version tag
git tag v1.0.0
git push origin v1.0.0
```

### 3. 📦 Build Package Locally (Optional Test)

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build the package
python -m build

# Check the package
python -m twine check dist/*

# Test install (in new environment)
pip install dist/navien_nwp500-1.0.0-py3-none-any.whl
```

### 4. 🔐 Setup PyPI Account & Token

#### Create PyPI Account
1. **Visit PyPI**: https://pypi.org/account/register/
2. **Create account** with username/password
3. **Verify email** address
4. **Enable 2FA** (REQUIRED): Account Settings → Security → Two-Factor Authentication

#### Generate API Token
1. **Go to tokens**: https://pypi.org/manage/account/token/
2. **Create new token**:
   - Token name: `navien-nwp500-github-actions`
   - Scope: "Entire account" (for first upload)
   - Click "Create Token"
3. **Copy token** (starts with `pypi-`): `pypi-AgEIcHlwaS5vcmcCJGZkNWY4...`
   - ⚠️ **Save immediately** - you won't see it again!

#### Add Token to GitHub Secrets
1. **Go to repository**: https://github.com/eman/navien-nwp500-python
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret**:
   - Name: `PYPI_API_TOKEN`
   - Value: `pypi-AgEIcHlwaS5vcmcCJGZkNWY4...` (your full token)
   - Click "Add secret"

✅ **After this setup, releases will be fully automated!**

### 5. 📤 Manual PyPI Upload (If CI Fails)

```bash
# Upload to PyPI using your API token
python -m twine upload dist/*
# Username: __token__
# Password: [your-pypi-token]

# Or set environment variable
export TWINE_PASSWORD="pypi-your-actual-token-here"
python -m twine upload -u __token__ dist/*
```

### 6. 🎯 GitHub Release (Manual)

1. **Go to GitHub**: https://github.com/eman/navien-nwp500-python/releases
2. **Click "Create a new release"**
3. **Fill in details**:
   - **Tag version**: `v1.0.0`
   - **Release title**: `NaviLink v1.0.0 - Production Ready`
   - **Description**: Use the template below

### 7. 📝 GitHub Release Template

```markdown
# NaviLink v1.0.0 - Production Ready 🎉

## What's New

This is the **initial production release** of NaviLink, a Python library for controlling and monitoring Navien NWP500 Heat Pump Water Heaters via the NaviLink service.

### ✨ Key Features

- **🔥 Real-time Tank Monitoring**: Track DHW charge levels, temperatures, and heat pump operation
- **🎛️ Device Control**: Adjust temperature settings, operation modes, and power state  
- **📊 Production Examples**: Ready-to-use monitoring scripts with CSV export
- **🧪 HAR-Validated Parsers**: Thoroughly tested against real API responses
- **🔐 Enterprise Configuration**: Secure .env-based credential management
- **⚡ Async Python**: Full asyncio support for concurrent operations

### 🏗️ Supported Hardware

- ✅ **Navien NWP500** Heat Pump Water Heater (50-gallon, validated)
- ✅ **NaviLink** smart control service
- ✅ **Residential installations**

### 🔧 Installation

```bash
pip install navien-nwp500
```

### 🚀 Quick Start

```python
import asyncio
from navien_nwp500 import NaviLinkClient, NaviLinkConfig

async def main():
    # Load credentials from .env file
    config = NaviLinkConfig.from_environment()
    client = NaviLinkClient(config=config)
    
    # Authenticate and get devices
    await client.authenticate(config.email, config.password)
    devices = await client.get_devices()
    device = devices[0]
    
    # Get current tank status
    status = await device.get_status()
    print(f"🏠 Tank: {status.dhw_charge_per}% | 🌡️ Temp: {status.dhw_temperature}°F")
    
    # Control device
    await device.set_dhw_temperature(120)
    print("✅ Temperature set to 120°F")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### 📊 Production Monitoring

```bash
# Create .env file with your credentials
cp .env.template .env
# Edit .env with your NaviLink email/password

# Start production tank monitoring
python -m examples.tank_monitoring_production --interval 300
```

### 📚 Documentation & Examples

- **📖 [README.md](README.md)** - Complete setup and usage guide
- **📋 [API Documentation](docs/)** - Detailed API reference
- **💡 [Examples](examples/)** - Working code examples
- **🧪 [Testing](tests/)** - HAR-validated test suite

### 🐛 Bug Reports & 💡 Feature Requests

Found an issue or have an idea? Please use our [GitHub Issues](https://github.com/eman/navien-nwp500-python/issues) page.

### 🏷️ Version Information

- **Python**: 3.8+ (tested on 3.8, 3.9, 3.10, 3.11, 3.12, 3.13)
- **Platforms**: Windows, macOS, Linux  
- **License**: MIT

**Full Changelog**: [CHANGELOG.md](CHANGELOG.md)
```

### 8. ⚙️ Automated Release (Recommended)

The repository includes a GitHub Actions workflow that will:

1. **Trigger on tag push**: `git push origin v1.0.0`
2. **Run tests** on multiple Python versions
3. **Build package** automatically
4. **Create GitHub release** with changelog
5. **Upload to PyPI** (requires setup)

To use automated PyPI publishing:

1. **Add PyPI API token to GitHub Secrets**:
   - Go to: Repository → Settings → Secrets and variables → Actions
   - Add secret: `PYPI_API_TOKEN` with your token value

2. **Push tag** (triggers everything):
```bash
git tag v1.0.0
git push origin v1.0.0
```

### 9. 📋 Post-Release Checklist

- [ ] Verify package on PyPI: https://pypi.org/project/navien-nwp500/
- [ ] Test installation: `pip install navien-nwp500`
- [ ] Update repository README with PyPI badge
- [ ] Announce release (social media, forums, etc.)
- [ ] Plan next version features

### 🎯 PyPI Package URL

After release, your package will be available at:
- **PyPI**: https://pypi.org/project/navien-nwp500/
- **Install**: `pip install navien-nwp500`

### 🚨 Troubleshooting

#### PyPI Upload Issues
```bash
# Check package before upload
python -m twine check dist/*

# Upload to Test PyPI first
python -m twine upload --repository testpypi dist/*

# Test install from Test PyPI
pip install --index-url https://test.pypi.org/simple/ navien-nwp500
```

#### Version Issues
```bash
# Check current version
python -c "from navien_nwp500 import __version__; print(__version__)"

# Force version with setuptools-scm
git describe --tags
```

### 🎉 Success Indicators

- ✅ GitHub tag created: `v1.0.0`
- ✅ GitHub release published with assets
- ✅ PyPI package available and installable
- ✅ GitHub Actions build passing
- ✅ Documentation updated and accessible

**You're ready for production! 🚀**