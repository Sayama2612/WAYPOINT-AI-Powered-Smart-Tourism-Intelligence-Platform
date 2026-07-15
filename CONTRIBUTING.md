# Contributing to WAYPOINT

Thank you for your interest in contributing! This document outlines how to get started and what we expect.

## Getting Started

1. Clone the repo and set up a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

2. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

## Development Workflow

### Running Tests
Run the full test suite before pushing:
```bash
python -m unittest discover -v
```

### Code Quality
We use `flake8` for linting. Check your code before committing:
```bash
flake8 services/ utils/ models/ app.py --max-line-length=120
```

### Testing with Coverage
To see test coverage:
```bash
pip install coverage
coverage run -m unittest discover -v
coverage report -m
```

## Submitting Changes

1. Make your changes and commit with clear messages:
```bash
git commit -m "feat: add feature XYZ"
```

2. Push to your branch:
```bash
git push origin feature/your-feature-name
```

3. Open a pull request against `main` with:
   - Clear description of what changed and why
   - Reference any relevant issues
   - Ensure all tests pass

## Standards

- **Tests**: Add tests for new features. Aim for >80% coverage on new code.
- **Code style**: Follow PEP 8; flake8 checks will catch issues.
- **Commits**: Use clear, descriptive commit messages.
- **Documentation**: Update README.md if adding new features or changing behavior.

## CI/CD

GitHub Actions runs tests and linting on every push/PR. All checks must pass before merging.

Thank you for contributing to WAYPOINT!
