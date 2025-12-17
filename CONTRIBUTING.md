# Contributing to AI.STACK

First off, thank you for considering contributing to AI.STACK! It's people like you that make AI.STACK such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our commitment to creating a welcoming and inclusive environment. Please be respectful and constructive in all interactions.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include as many details as possible:

**Bug Report Template:**
```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Run '...'
2. Select '...'
3. See error

**Expected behavior**
What you expected to happen.

**System Information:**
- OS: [e.g., Ubuntu 22.04]
- RAM: [e.g., 16GB]
- GPU: [e.g., NVIDIA RTX 3080]
- AI.STACK Version: [e.g., 5.0.0]

**Logs**
```
Paste relevant logs here
```

**Screenshots**
If applicable, add screenshots.
```

### Suggesting Features

Feature suggestions are welcome! Please create an issue with:

- A clear title and description
- The problem this feature would solve
- How you envision it working
- Any alternatives you've considered

### Pull Requests

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** for your feature or fix:
   ```bash
   git checkout -b feature/my-new-feature
   ```
4. **Make your changes**
5. **Test** your changes thoroughly
6. **Commit** with clear messages:
   ```bash
   git commit -m "Add feature: description of what it does"
   ```
7. **Push** to your fork:
   ```bash
   git push origin feature/my-new-feature
   ```
8. **Create a Pull Request**

### Pull Request Guidelines

- **One feature per PR** - Keep PRs focused and manageable
- **Update documentation** - If your change affects usage, update the README
- **Test your changes** - Ensure installation works on a clean system
- **Follow existing style** - Match the code style of the project
- **Write clear commit messages** - Explain what and why

## Development Setup

### Prerequisites
- Ubuntu 22.04+ (or compatible)
- Bash 4.0+
- Docker and Docker Compose
- Git

### Local Testing
```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/aistack.git
cd aistack

# Test the installer
bash install_aistack.sh --check

# For full testing, use a VM or container
```

### Code Style

**Bash Script Guidelines:**
- Use `#!/usr/bin/env bash` shebang
- Quote variables: `"$VARIABLE"` not `$VARIABLE`
- Use `[[ ]]` for conditionals
- Add comments for complex logic
- Use meaningful variable names
- Keep functions focused and small

**Example:**
```bash
# Good
install_component() {
  local component_name="$1"

  if [[ -z "$component_name" ]]; then
    log "ERROR: Component name required"
    return 1
  fi

  log "[*] Installing $component_name..."
  # Installation logic here
}

# Avoid
install() {
  if [ -z $1 ]; then echo error; return 1; fi
  echo installing $1
}
```

## Areas We Need Help

- **Testing** on different hardware configurations
- **Documentation** improvements
- **Tool development** - New AI tools for OpenWebUI
- **Translations** - Internationalization support
- **Security** review and improvements

## Questions?

Feel free to open an issue with the "question" label or start a discussion.

## Recognition

Contributors will be recognized in our README and release notes. Thank you for making AI.STACK better!
