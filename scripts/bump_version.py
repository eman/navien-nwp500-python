#!/usr/bin/env python3
"""
Version bumping script for navien-nwp500 package.

This script helps with semantic version bumping and release preparation.
Uses setuptools-scm for version management, which derives versions from git tags.
"""
import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path


def run_command(cmd, check=True):
    """Run a shell command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()


def get_current_version():
    """Get current version from setuptools-scm."""
    try:
        result = run_command("python -m setuptools_scm")
        # Clean up development versions for processing
        if '+' in result:
            result = result.split('+')[0]  # Remove +dirty suffix
        if 'post' in result:
            result = result.split('.post')[0]  # Remove .postN suffix
        return result
    except:
        return "0.0.0"


def update_changelog(version_type, new_version):
    """Update CHANGELOG.md with new version information."""
    changelog_path = Path("CHANGELOG.md")
    if not changelog_path.exists():
        print("CHANGELOG.md not found")
        return
    
    content = changelog_path.read_text()
    today = date.today().strftime("%Y-%m-%d")
    
    # Replace [Unreleased] with new version
    unreleased_header = "## [Unreleased]"
    new_version_header = f"## [{new_version}] - {today}"
    
    if unreleased_header in content:
        # Add new unreleased section and move current to version
        new_unreleased = f"{unreleased_header}\n\n### Added\n- \n\n### Changed\n- \n\n### Fixed\n- \n\n"
        content = content.replace(
            unreleased_header,
            f"{new_unreleased}{new_version_header}"
        )
        
        # Update the links at bottom
        content = content.replace(
            f"[Unreleased]: https://github.com/eman/navien-nwp500-python/compare/v",
            f"[Unreleased]: https://github.com/eman/navien-nwp500-python/compare/v{new_version}...HEAD\n[{new_version}]: https://github.com/eman/navien-nwp500-python/compare/v"
        )
        
        changelog_path.write_text(content)
        print(f"Updated CHANGELOG.md with version {new_version}")


def create_git_tag(version, push=False):
    """Create and optionally push a git tag."""
    tag_name = f"v{version}"
    
    # Check if tag already exists
    result = subprocess.run(f"git tag -l {tag_name}", shell=True, capture_output=True)
    if result.stdout.strip():
        print(f"Tag {tag_name} already exists")
        return False
    
    # Create tag
    run_command(f'git tag -a {tag_name} -m "Release version {version}"')
    print(f"Created tag: {tag_name}")
    
    if push:
        run_command(f"git push origin {tag_name}")
        print(f"Pushed tag: {tag_name}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Bump version for navien-nwp500")
    parser.add_argument(
        "version_type", 
        choices=["major", "minor", "patch", "custom"],
        help="Type of version bump"
    )
    parser.add_argument(
        "--version", 
        help="Custom version (required if version_type is 'custom')"
    )
    parser.add_argument(
        "--push", 
        action="store_true",
        help="Push the git tag to origin"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    if args.version_type == "custom" and not args.version:
        parser.error("--version is required when version_type is 'custom'")
    
    # Get current version
    current = get_current_version()
    print(f"Current version: {current}")
    
    # Calculate new version
    if args.version_type == "custom":
        new_version = args.version
    else:
        # Parse current version for semantic bumping
        parts = current.split(".")
        if len(parts) >= 3:
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        else:
            major, minor, patch = 0, 0, 0
            
        if args.version_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif args.version_type == "minor":
            minor += 1
            patch = 0
        elif args.version_type == "patch":
            patch += 1
            
        new_version = f"{major}.{minor}.{patch}"
    
    print(f"New version: {new_version}")
    
    if args.dry_run:
        print("DRY RUN - No changes made")
        return
    
    # Check for uncommitted changes
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print("Warning: There are uncommitted changes in the repository")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Update changelog
    update_changelog(args.version_type, new_version)
    
    # Commit changelog changes
    run_command("git add CHANGELOG.md")
    run_command(f'git commit -m "Update changelog for version {new_version}"')
    
    # Create git tag (this will trigger setuptools-scm versioning)
    if create_git_tag(new_version, args.push):
        print(f"✅ Version {new_version} prepared successfully")
        
        if args.push:
            print("🚀 Tag pushed to origin - GitHub Actions will handle PyPI publishing")
        else:
            print(f"📝 To publish, run: git push origin v{new_version}")
    else:
        print(f"❌ Failed to create version {new_version}")


if __name__ == "__main__":
    main()