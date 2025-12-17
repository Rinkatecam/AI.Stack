# Changelog

All notable changes to AI.STACK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [5.0.0] - 2024-12-17

### Added

#### Installation Improvements
- **Pre-flight validation** (`--check` flag) - Verify system compatibility before installing
- **Installation resume** (`--resume` flag) - Continue interrupted installations
- **Clean up** (`--clean` flag) - Reset partial installations
- **Verbose mode** (`-v` flag) - Detailed installation output
- **Quiet mode** (`-q` flag) - Minimal output
- **Cleanup trap** - Friendly error handling for failed installations

#### New Management Scripts
- `uninstall.sh` - Clean removal with 4 different levels
- `update.sh` - Check and apply AI.STACK updates
- Enhanced `backup.sh` with verification and restore capabilities

#### Post-Installation
- **Health check** - Automatic verification after installation
- **Disk space estimation** - Per-component space requirements

#### Tools
- All 12 tools now embedded directly in installer
- Tool selection saved for import helper
- Import helper only shows user's selected tools
- Department presets (R&D, RA, QS, HR, IT)

#### Security
- Prominent security warning for credentials
- Clear instructions to save to password manager
- Reminder to delete secrets.conf after saving

### Changed
- Installer now ~9,300 lines (comprehensive single-file)
- Improved error messages with recovery options
- Better progress tracking throughout installation
- Dynamic tool counts in import helper

### Fixed
- Import helper now respects tool selection from installation
- Backup script properly handles all data types

---

## [4.0.0] - 2024-12-01

### Added
- Initial public release
- OpenWebUI + Ollama + Qdrant stack
- NVIDIA GPU auto-detection and driver installation
- AMD GPU experimental support
- Three installation modes (Quick, Custom, Secure)
- Three security levels (Basic, Standard, Hardened)
- 12 AI tools for OpenWebUI
- AI personalities system
- Infrastructure options (Portainer, n8n, Paperless)
- Network fileshare integration
- Automatic model selection based on hardware

### Security
- Port randomization
- Secure credential generation
- Firewall auto-configuration
- Localhost binding options

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 5.0.0 | 2024-12-17 | Resume, health check, uninstall, backup verification |
| 4.0.0 | 2024-12-01 | Initial public release |

---

## Upgrade Notes

### From 4.x to 5.x

No breaking changes. Simply run the updater:
```bash
~/ai-stack/update.sh
```

Or download and run the new installer - it will detect existing configuration.

---

## Roadmap

### Planned Features
- [ ] Web-based configuration UI
- [ ] Automatic SSL/TLS with Let's Encrypt
- [ ] Cluster/multi-node support
- [ ] More AI tool templates
- [ ] Model fine-tuning helpers
- [ ] Prometheus/Grafana monitoring integration

### Under Consideration
- Windows WSL2 native support
- macOS support
- Kubernetes deployment option
- Cloud backup integration
