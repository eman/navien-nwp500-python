# 🎨 Code Formatting Requirements

## ⚠️ IMPORTANT: CI Will Fail Without Proper Formatting

This project **requires** all code to be formatted with **Black** and **isort**. The CI build will **fail** if formatting standards are not met.

## 🚀 Quick Fix for Contributors

**Before committing any code**, always run:

```bash
# Format all code (REQUIRED)
make format

# Or run individually:
black .
isort .
```

## 🔧 Automated Setup (Recommended)

Install pre-commit hooks to automatically format code on every commit:

```bash
# One-time setup
make pre-commit-install

# Now your code will be auto-formatted on commit!
git commit -m "Your changes"  # Automatically formatted
```

## 📋 What Gets Checked

The CI system validates:

1. **✅ Black formatting** - Python code style
2. **✅ Import sorting** - isort for consistent imports  
3. **✅ HAR-based tests** - Parser validation with real data
4. **📦 Package building** - Ensures distribution works

## 🔍 Manual Validation

To check your code before committing:

```bash
# Check formatting (should show no changes needed)
black --check .
isort --check-only .

# Run full quality check
make check
```

## 📚 Why This Matters

- **Consistency**: All code follows the same style
- **Readability**: Black's formatting is optimized for reading
- **Automation**: No debates about formatting in reviews
- **CI Reliability**: Prevents formatting-related build failures

## 🚨 Common Issues

### "would reformat" Errors in CI

If CI fails with messages like `would reformat file.py`:

```bash
# Fix locally:
black .
git add -A
git commit -m "Fix Black formatting"
git push
```

### Import Sorting Errors

If CI fails with isort errors:

```bash
# Fix locally:
isort .
git add -A  
git commit -m "Fix import sorting"
git push
```

## 🛠️ Configuration

Both tools are configured in `pyproject.toml`:

```toml
[tool.black]
line-length = 88
target-version = ['py38']

[tool.isort]
profile = "black"
line_length = 88
```

## 🎯 Development Workflow

1. **Make changes** to code
2. **Run `make format`** (REQUIRED)
3. **Run `make check`** (full validation)
4. **Commit and push**

## 📞 Need Help?

- **Documentation**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Issues**: [GitHub Issues](https://github.com/eman/navien-nwp500-python/issues)  
- **Quick commands**: Run `make help`

---

**Remember**: Running `make format` before committing prevents CI failures! 🚀