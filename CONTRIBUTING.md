# Contributing to PhotosSorter

Thank you for your interest in contributing to PhotosSorter! This document provides guidelines and information for contributors.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Development Guidelines](#development-guidelines)

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- ffmpeg (for video processing features)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/abshka/PhotosSorter.git
   cd PhotosSorter
   ```

## Development Setup

### Quick Setup

Use the Makefile for easy setup:

```bash
make quick-start
```

This will:

- Install the package in development mode
- Install development dependencies
- Create a config file from the example
- Check system dependencies

### Manual Setup

1. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install development dependencies:

   ```bash
   make install-dev
   # OR manually:
   pip install -e ".[dev,video]"
   ```

3. Create configuration file:

   ```bash
   cp config.yaml.example config.yaml
   ```

4. Verify installation:
   ```bash
   make check-deps
   python run.py --help
   ```

## Code Style

We use standard Python tools for code formatting and linting:

### Formatting

- **Black** for code formatting (line length: 88)
- **flake8** for linting
- **mypy** for type checking (optional but encouraged)

### Running Code Style Tools

```bash
# Format code
make format

# Check formatting
black --check src/

# Lint code
make lint

# Run all checks
make check
```

### Style Guidelines

- Follow PEP 8 conventions
- Use meaningful variable and function names
- Add docstrings to all public functions and classes
- Use type hints where possible
- Keep functions focused and small
- Add comments for complex logic

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_specific.py

# Run with coverage
pytest --cov=src tests/
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Use descriptive test function names
- Test both success and failure cases
- Mock external dependencies (filesystem, ffmpeg)

### Test Categories

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test complete workflows
4. **Safety Tests**: Ensure dry-run mode works correctly

## Pull Request Process

### Before Submitting

1. **Check your changes**:

   ```bash
   make check
   make test
   ```

2. **Update documentation** if needed
3. **Add tests** for new functionality
4. **Update CHANGELOG.md** with your changes

### Submitting

1. Create a feature branch:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit:

   ```bash
   git add .
   git commit -m "Add feature: description of changes"
   ```

3. Push to your fork:

   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a Pull Request on GitHub

### PR Guidelines

- **Title**: Use clear, descriptive titles
- **Description**: Explain what changes you made and why
- **Testing**: Describe how you tested your changes
- **Breaking Changes**: Highlight any breaking changes
- **Related Issues**: Reference any related issues

## Issue Reporting

### Before Creating an Issue

1. Check if the issue already exists
2. Try the latest version
3. Read the documentation
4. Test with `--dry-run` mode

### Creating Good Issues

Include:

- **Clear title** and description
- **Steps to reproduce** the problem
- **Expected vs actual behavior**
- **Environment details** (OS, Python version, ffmpeg version)
- **Log files** from `logs/photos_sorter.log`
- **Configuration** (sanitized, remove sensitive paths)

### Issue Labels

We use labels to categorize issues:

- `bug`: Something isn't working
- `enhancement`: New feature or improvement
- `documentation`: Documentation improvements
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention needed

## Development Guidelines

### Project Structure

```
PhotosSorter/
├── src/                    # Source code
│   ├── __init__.py
│   ├── photos_sorter.py    # Main application
│   ├── exif_extractor.py   # EXIF handling
│   ├── file_organizer.py   # File operations
│   ├── video_processor.py  # Video processing
│   └── mpg_thm_merger.py   # MPG/THM merging
├── tests/                  # Test files
├── docs/                   # Documentation
├── config.yaml.example     # Example configuration
├── run.py                  # Entry point script
├── requirements.txt        # Dependencies
├── pyproject.toml          # Modern packaging
└── Makefile               # Development commands
```

### Adding New Features

1. **Design first**: Consider the impact on existing code
2. **Configuration**: Add new options to config.yaml.example
3. **Logging**: Add appropriate logging statements
4. **Error handling**: Handle edge cases gracefully
5. **Documentation**: Update README.md and docstrings
6. **Tests**: Add comprehensive tests

### Code Organization

- **Single responsibility**: Each module has a clear purpose
- **Dependency injection**: Pass dependencies rather than importing globally
- **Error handling**: Use exceptions for error conditions
- **Logging**: Use the configured logger, not print statements
- **Configuration**: Access config through the main class

### Performance Considerations

- **Memory usage**: Process files in batches for large collections
- **I/O operations**: Use appropriate buffering and threading
- **Progress reporting**: Provide feedback for long operations
- **Caching**: Cache expensive operations when appropriate

### Security Considerations

- **Path traversal**: Validate all file paths
- **External commands**: Sanitize inputs to external tools (ffmpeg)
- **Configuration**: Don't include sensitive data in examples
- **Logging**: Don't log sensitive information

## Getting Help

- **Documentation**: Check README.md and code comments
- **Issues**: Search existing issues on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Code**: Read the source code - it's well-documented!

## Recognition

Contributors will be recognized in:

- CHANGELOG.md for significant contributions
- GitHub's contributor list
- Release notes for major features

Thank you for contributing to PhotosSorter! 🎉
