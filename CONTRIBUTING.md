# Contributing to PACTS

Thank you for your interest in contributing to PACTS! This document provides guidelines for contributing.

## 🚀 Getting Started

### Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/pacts.git
cd pacts
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
playwright install
```

## 📝 Development Workflow

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes following Python best practices (PEP 8)
3. Add tests for new functionality
4. Run tests: `pytest tests/ -v`
5. Format code: `black src/` and `isort src/`
6. Commit: `git commit -m "feat: description"`
7. Push and create Pull Request

## 🧪 Testing

- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- E2E tests: `tests/e2e/`
- Aim for >80% code coverage

## 📚 Documentation

- Use Google-style docstrings
- Add type hints
- Update `docs/` for architectural changes

## 🎨 Code Style

- Follow PEP 8
- Use Black (line length: 88)
- Use isort for imports
- Add type hints everywhere
- Keep functions small and focused

## 📄 License

By contributing, you agree your contributions will be licensed under MIT License.

Thank you for contributing to PACTS!
