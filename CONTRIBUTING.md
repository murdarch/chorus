# Contributing to Chorus

Thank you for considering contributing to Chorus! 🎉

## How to Contribute

### Reporting Bugs

Found a bug? Please [open an issue](https://github.com/murdarch/chorus/issues/new) with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (Python version, OS, etc.)
- Relevant logs (remove any API keys!)

### Suggesting Features

Have an idea? We'd love to hear it! [Open an issue](https://github.com/murdarch/chorus/issues/new) with:
- Clear description of the feature
- Why it would be useful
- How it might work
- Any examples or mockups

### Submitting Pull Requests

1. **Fork the repository**
2. **Create a branch**: `git checkout -b feature/your-feature-name`
3. **Follow the development guidelines** in `CLAUDE.md`
4. **Write tests** for new functionality
5. **Commit your changes**: Use clear, descriptive messages
6. **Push to your fork**: `git push origin feature/your-feature-name`
7. **Open a Pull Request** with a clear description

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/chorus.git
cd chorus

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
# Add your test API keys

# Run tests
uv run python scripts/test_image_processing.py
uv run python scripts/test_image_generation.py
```

### Code Style

- Follow PEP 8
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and simple
- Follow patterns established in the codebase

### Development Philosophy

From `CLAUDE.md`:
- **Incremental progress** over big bangs
- **Learning from existing code** before implementing
- **Pragmatic over dogmatic**
- **Clear intent over clever code**
- **Test-driven when possible**

### Commit Messages

Good commit messages help everyone understand changes:

```
Add support for custom image aspect ratios

- Add aspect_ratio parameter to generate_image tool
- Update Discord bot to pass user-specified ratios
- Add validation for supported ratios
- Update documentation
```

### Testing

- Write tests for new features
- Ensure existing tests pass
- Test with real bots when possible
- Check for API key leaks before committing

### Documentation

- Update relevant docs (README, IMAGE_SUPPORT.md, etc.)
- Add examples for new features
- Update IMPLEMENTATION_PLAN.md if needed
- Keep docstrings current

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the project
- Show empathy towards others

### Unacceptable Behavior

- Harassment or discriminatory language
- Trolling or insulting comments
- Public or private harassment
- Publishing others' private information
- Other unprofessional conduct

## Questions?

Not sure about something? Just ask!
- Open an issue
- Start a discussion
- Reach out to maintainers

## Recognition

Contributors will be:
- Listed in release notes
- Credited in commit history
- Appreciated by the community! ❤️

---

**Thank you for making Chorus better!** 🎭✨
