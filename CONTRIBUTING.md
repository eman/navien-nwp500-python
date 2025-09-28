# Contributing to NaviLink

Thank you for your interest in contributing to NaviLink! This guide will help you get started with development and ensure code quality standards.

## 🚀 Getting Started

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/eman/navien-nwp500-python.git
   cd navien-nwp500-python
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies**:
   ```bash
   pip install -e ".[dev,test]"
   ```

4. **Install pre-commit hooks** (recommended):
   ```bash
   pre-commit install
   ```

## 📋 Code Quality Standards

### **🧪 CRITICAL: Testing Requirements for ALL Contributors**

**⚠️ This applies to ALL contributors: human developers, AI coding assistants, automated tools, and any code generation systems.**

### **🚨 MANDATORY PRE-SUBMISSION CHECKLIST**

**BEFORE submitting ANY code changes, you MUST:**

#### **1. ✅ Run Tests and Verify They Pass**
```bash
# Run the test suite (REQUIRED - must pass before submission)
pytest tests/ --ignore=tests/legacy -v

# Expected result: 24+ passed, 3 skipped (or better)
# ❌ NEVER submit code if tests are failing
# ❌ NEVER decrease the number of passing tests
```

#### **2. ✅ Format Code (CI will reject improperly formatted code)**
```bash
# Format code with Black (REQUIRED - CI will fail if not formatted)
black navien_nwp500 tests examples

# Sort imports with isort (REQUIRED)  
isort navien_nwp500 tests examples
```

#### **3. ✅ Run Type Checking (Recommended)**
```bash
# Type checking (helps catch issues early)
mypy navien_nwp500
```

#### **4. ✅ For Release/Packaging Changes (Additional Required Tests)**
```bash
# If modifying setup.py, pyproject.toml, __init__.py, or version info:

# Test package building (REQUIRED before release changes)
python -m build --sdist --wheel

# Test package installation (verify setup changes work)
pip install -e .

# Test import after installation (catch import errors)
python -c "import navien_nwp500; print('✅ Import successful')"

# Test version consistency (for version changes)
python -c "import navien_nwp500; print(f'Version: {navien_nwp500.__version__}')"
```

### **🎯 Test Quality Standards**

#### **Current Baseline (DO NOT BREAK):**
- ✅ **24 passing tests** (core functionality validated)
- ✅ **3 skipped tests** (integration tests requiring credentials)
- ✅ **89% pass rate** (24/27 tests)
- ✅ **Legacy tests disabled** (`tests/legacy/` - these are broken by design)

#### **Rules for Test Changes:**
- **✅ Adding tests**: Always welcome when adding features
- **❌ Breaking existing tests**: Must be fixed in same commit
- **❌ Reducing passing test count**: Never acceptable  
- **✅ Fixing broken tests**: Encouraged (but not required for contributions)

### **🚫 Zero Tolerance Policy**

**Code submissions will be REJECTED if they:**
- Break existing working tests
- Reduce the number of passing tests
- Are not properly formatted with Black/isort
- Don't include test fixes for any test breakage they introduce
- **Break package building/installation** (for setup.py, pyproject.toml, or version changes)

**Exception:** Only when explicitly asked to create failing tests for debugging purposes.

### **🤖 Special Instructions for AI Assistants**

**If you are an AI coding assistant or automated tool:**
- **ALWAYS run tests before suggesting code changes**
- **ALWAYS verify your changes don't break existing functionality**  
- **ALWAYS include test fixes if your changes break tests**
- **NEVER submit code with failing tests unless explicitly asked**
- **ALWAYS format code with Black and isort**
- **For packaging changes**: ALWAYS test package building and installation

### **🔍 Additional Quality Checks**

```bash
# Linting (helps catch issues)
flake8 navien_nwp500 --exclude=navien_nwp500/_version.py

# Full development workflow check
make test  # If using Makefile
```

### **✅ Quick Pre-Submission Commands**

#### **For Regular Code Changes:**
```bash
# Standard workflow for most changes:
black navien_nwp500 tests examples && isort navien_nwp500 tests examples && pytest tests/ --ignore=tests/legacy -v
```

#### **For Release/Packaging Changes:**
```bash
# Extended workflow for setup.py, pyproject.toml, version changes:
black navien_nwp500 tests examples && isort navien_nwp500 tests examples && pytest tests/ --ignore=tests/legacy -v && python -m build --sdist --wheel && pip install -e . && python -c "import navien_nwp500; print('✅ Import successful')"
```

## 🚀 Development Workflow

# Check all quality standards at once
make check  # or run individual commands above
```

### **🤖 For AI Coding Assistants & Automated Tools**

AI assistants and automated code generation tools **must** apply the same formatting standards:

- **Always run `black .`** after generating or modifying code
- **Always run `isort .`** to sort imports properly  
- **Verify formatting** with `black --check .` before submitting
- **Use the same standards** as human contributors

**Note**: AI-generated code is subject to the same CI checks as human-written code. The build will fail if formatting is not applied, regardless of the source.

### **⚠️ CI Enforcement**

Our GitHub Actions CI automatically checks:
- ✅ **Black formatting** - CI fails if code is not formatted
- ✅ **Import sorting** (isort) - CI fails if imports not sorted
- ✅ **Test coverage** - All tests must pass
- ✅ **Type hints** - MyPy checks (warnings only)

**Important**: The CI build will **fail** if Black or isort formatting is not applied. Always run these tools before committing.

### **🛠️ Pre-commit Hooks (Recommended)**

Install pre-commit hooks to automatically format code on commit:

```bash
pre-commit install
```

This will automatically run Black and isort on your code before each commit, preventing CI failures.

## 🧪 Testing Guidelines

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_har_integration.py -v

# Run with coverage
pytest --cov=navien_nwp500 --cov-report=html

# Run integration tests (requires credentials)
pytest tests/test_integration.py -v
```

### Test Categories

- **Unit Tests**: `tests/test_*.py` - Fast, isolated tests
- **Integration Tests**: `tests/test_integration.py` - Requires real credentials
- **HAR Tests**: `tests/test_har_integration.py` - Uses sanitized real data

### Adding New Tests

1. Create test files following the pattern `test_*.py`
2. Use meaningful test names that describe what's being tested
3. Include docstrings for complex test scenarios
4. Use HAR-based test data when possible for real-world validation

## 📝 Documentation Standards

### Code Documentation

- **Type Hints**: All public functions must have type hints
- **Docstrings**: Use Google-style docstrings for public APIs
- **Comments**: Explain complex logic, especially MQTT/AWS IoT interactions

### Example Docstring Format

```python
async def get_device_status(self, use_cache: bool = True) -> DeviceStatus:
    """
    Get current device status via MQTT.

    Args:
        use_cache: If True, return cached status if recent

    Returns:
        DeviceStatus object with current device state

    Raises:
        DeviceError: If device is offline or unreachable
        MQTTError: If MQTT communication fails
    """
```

## 🔄 Development Workflow

### 1. **Before Starting Work**

```bash
# Update your local repository
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. **During Development**

```bash
# Run tests frequently
pytest tests/ -v

# Format code before committing (REQUIRED)
black .
isort .

# Commit with descriptive messages
git commit -m "Add tank monitoring error recovery

- Implement exponential backoff for MQTT reconnection
- Add comprehensive error logging
- Update tests with offline device scenarios"
```

### 3. **Before Submitting PR**

```bash
# Final quality check (MUST PASS)
black --check .          # Must show no changes needed
isort --check-only .     # Must show no changes needed
pytest tests/ -v         # All tests must pass
mypy navien_nwp500      # Check for type issues

# Push your branch
git push origin feature/your-feature-name
```

## 📋 Pull Request Guidelines

### PR Checklist

- [ ] **Code formatted with Black** (`black .`)
- [ ] **Imports sorted with isort** (`isort .`)
- [ ] **All tests passing** (`pytest`)
- [ ] **Type hints added** for new public functions
- [ ] **Documentation updated** if adding new features
- [ ] **CHANGELOG.md updated** for user-facing changes
- [ ] **Examples updated** if API changes affect usage

### PR Description Template

```markdown
## What Changed
Brief description of the changes made.

## Why
Explain the motivation for these changes.

## Testing
- [ ] Existing tests pass
- [ ] New tests added for new functionality
- [ ] Tested with real hardware (if applicable)

## Breaking Changes
List any breaking changes and migration path.

## Checklist
- [ ] Code formatted with Black
- [ ] Imports sorted with isort
- [ ] Tests passing
- [ ] Documentation updated
```

## 🔧 Development Tools Configuration

### Black Configuration
Black is configured in `pyproject.toml`:
```toml
[tool.black]
line-length = 88
target-version = ['py38']
```

### isort Configuration
isort is configured for Black compatibility:
```toml
[tool.isort]
profile = "black"
line_length = 88
```

### MyPy Configuration
Type checking configuration in `pyproject.toml` allows flexibility for AWS/MQTT complexity.

## 🏗️ Architecture Guidelines

### Code Organization

```
navien_nwp500/
├── __init__.py          # Public API exports
├── client.py            # Main client class
├── device.py            # Device abstraction
├── auth.py              # Authentication handling
├── mqtt.py              # High-level MQTT wrapper
├── aws_iot_websocket.py # Low-level AWS IoT client
├── models.py            # Data models
├── config.py            # Configuration management
├── exceptions.py        # Custom exceptions
└── utils.py             # Utility functions
```

### Design Principles

1. **Async First**: All I/O operations use asyncio
2. **Type Safety**: Comprehensive type hints and dataclasses
3. **Error Recovery**: Robust error handling with exponential backoff
4. **Configuration**: Flexible .env-based configuration
5. **Testing**: HAR-validated parsers for real-world reliability

## 🔒 Security Guidelines

### Credentials and Sensitive Data

- **Never commit credentials** or API tokens
- **Use .env files** for local development
- **Sanitize test data** - remove MACs, tokens, emails
- **Environment variables** for CI/production

### Security Review Areas

- AWS IoT signature generation
- MQTT authentication
- Session management
- Input validation

## 🐛 Debugging Tips

### MQTT Issues
```bash
# Enable debug logging
export NAVILINK_LOG_LEVEL=DEBUG
python your_script.py
```

### HAR File Analysis
```bash
# Extract test data from new HAR files
python extract_test_data.py  # (Create this when needed)
```

### Device Connectivity
```bash
# Test device connectivity
python -c "
import asyncio
from navien_nwp500 import NaviLinkClient, NaviLinkConfig

async def test():
    config = NaviLinkConfig.from_environment()
    client = NaviLinkClient(config=config)
    await client.authenticate(config.email, config.password)
    devices = await client.get_devices()
    print(f'Found {len(devices)} devices')
    await client.close()

asyncio.run(test())
"
```

## 📞 Getting Help

- **Issues**: [GitHub Issues](https://github.com/eman/navien-nwp500-python/issues)
- **Discussions**: [GitHub Discussions](https://github.com/eman/navien-nwp500-python/discussions)
- **Documentation**: [README.md](README.md) and [docs/](docs/)

## 🎯 Areas for Contribution

### High Priority
- Additional device type support (tankless water heaters)
- Home Assistant integration
- Energy usage analytics
- Advanced scheduling features

### Testing & Quality
- More integration test scenarios
- Performance benchmarking
- Security auditing
- Documentation improvements

### Developer Experience
- Better error messages
- More examples and tutorials
- IDE type hint improvements
- Debugging tools

## ✅ First Contribution Tips

1. **Start small**: Fix typos, improve documentation, add tests
2. **Read existing code**: Understand patterns before adding new features
3. **Ask questions**: Use GitHub Discussions for design questions
4. **Follow standards**: Use Black, isort, and type hints consistently
5. **Test thoroughly**: Include both unit and integration tests

Thank you for contributing to NaviLink! 🚀