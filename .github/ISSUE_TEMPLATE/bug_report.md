---
name: Bug Report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

## Describe the Bug
A clear and concise description of what the bug is.

## To Reproduce
Steps to reproduce the behavior:
1. Run '...'
2. Select '...'
3. See error

## Expected Behavior
What you expected to happen.

## Screenshots
If applicable, add screenshots to help explain your problem.

## System Information
- **OS**: [e.g., Ubuntu 22.04]
- **RAM**: [e.g., 16GB]
- **GPU**: [e.g., NVIDIA RTX 3080 / None]
- **GPU Driver**: [e.g., 535.154.05]
- **Docker Version**: [e.g., 24.0.7]
- **AI.STACK Version**: [e.g., 5.0.0]

## Installation Mode Used
- [ ] Quick Install
- [ ] Custom Install
- [ ] Secure Install

## Logs
<details>
<summary>Installation Log</summary>

```
Paste the output of: tail -100 ~/ai-stack/install.log
```
</details>

<details>
<summary>Docker Logs</summary>

```
Paste the output of: cd ~/ai-stack && docker compose logs --tail=50
```
</details>

## Additional Context
Add any other context about the problem here.

## Checklist
- [ ] I have checked existing issues for duplicates
- [ ] I have run `./install_aistack.sh --check` to verify system compatibility
- [ ] I have included relevant logs
