# AI.STACK

**Private AI Infrastructure in One Command**

Deploy a complete, secure, local AI environment on your own hardware. No cloud dependencies, no API costs, full data privacy.

```bash
curl -fsSL https://raw.githubusercontent.com/Rinkatecam/aistack/main/install_aistack.sh | bash
```

---

## What is AI.STACK?

AI.STACK is a comprehensive installer that sets up a complete private AI infrastructure including:

- **OpenWebUI** - ChatGPT-like interface for your local AI
- **Ollama** - Run LLMs locally (Llama, Mistral, Qwen, etc.)
- **Qdrant** - Vector database for RAG and semantic search
- **12 AI Tools** - Files, SQL, Web Search, Chemistry, Math, and more
- **Infrastructure** - Portainer, n8n automation, Paperless-ngx (optional)

All running on YOUR hardware, with YOUR data staying private.

---

## Features

### One-Command Installation
```bash
# That's it. One command.
curl -fsSL https://raw.githubusercontent.com/Rinkatecam/aistack/main/install_aistack.sh | bash
```

### Smart Hardware Detection
- Automatically detects NVIDIA/AMD GPUs
- Installs appropriate drivers
- Selects optimal AI models for your hardware
- Works on CPU-only systems too

### Three Installation Modes
| Mode | Best For |
|------|----------|
| **Quick Install** | First-time users, home labs |
| **Custom Install** | Specific requirements, experienced users |
| **Secure Install** | Production, enterprise, internet-facing |

### Security Built-In
- Three security levels (Basic, Standard, Hardened)
- Randomized internal ports
- Auto-generated secure credentials
- Firewall auto-configuration
- Localhost binding options

### 12 Powerful AI Tools
| Tool | Description |
|------|-------------|
| Files & Documents | Search, OCR, RAG with vector embeddings |
| SQL Database | Natural language to SQL queries |
| Web Search | DuckDuckGo, Wikipedia, Weather |
| Scientific Calculator | Math, unit conversions, equations |
| Chemistry | PubChem compound lookup |
| Visualization | Charts and graphs with matplotlib |
| Shell Execute | Safe command execution |
| Multi-Model Agents | Delegate tasks to specialized models |
| Document Templates | DOCX placeholder replacement |
| Code Analysis | Syntax validation, security scanning |
| Regulatory Lookup | FDA, ISO, MDR standards reference |
| Knowledge Base | Team experience database |

### Department Presets
Pre-configured tool sets for different teams:
- **R&D** - Files, Chemistry, Math, Code, Visualize
- **Regulatory Affairs** - Files, Regulatory, Templates, WebSearch
- **Quality** - Files, SQL, Templates, KnowledgeBase
- **HR** - Files, Templates, KnowledgeBase
- **IT** - All tools

---

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Ubuntu 22.04+ | Ubuntu 24.04 LTS |
| RAM | 8 GB | 16+ GB |
| Storage | 30 GB | 100+ GB |
| GPU | None (CPU works) | NVIDIA 8GB+ VRAM |

### Supported GPUs
- **NVIDIA**: GTX 1000+, RTX 2000/3000/4000 series
- **AMD**: ROCm-compatible (experimental)
- **CPU**: Works without GPU (slower)

---

## Quick Start

### 1. Install
```bash
curl -fsSL https://raw.githubusercontent.com/Rinkatecam/aistack/main/install_aistack.sh | bash
```

### 2. Access
Open your browser: `http://localhost:3000`

### 3. Create Account
First user becomes admin. Create your account and start chatting!

---

## Installation Options

### Pre-flight Check (Recommended First)
```bash
# Check if your system is ready
curl -fsSL https://raw.githubusercontent.com/Rinkatecam/aistack/main/install_aistack.sh -o install_aistack.sh
bash install_aistack.sh --check
```

### Command Line Options
```bash
./install_aistack.sh              # Normal installation
./install_aistack.sh --check      # System compatibility check
./install_aistack.sh --resume     # Resume interrupted installation
./install_aistack.sh --clean      # Clean up failed installation
./install_aistack.sh -v           # Verbose output
./install_aistack.sh -q           # Quiet mode
./install_aistack.sh --help       # Show all options
```

---

## Management

After installation, these scripts are available in `~/ai-stack/`:

| Script | Description |
|--------|-------------|
| `status.sh` | Check service status |
| `restart.sh` | Restart all services |
| `backup.sh` | Backup with verification |
| `update.sh` | Check for updates |
| `pull-model.sh` | Add new AI models |
| `uninstall.sh` | Remove AI.STACK |

### Backup & Restore
```bash
# Create verified backup
~/ai-stack/backup.sh

# List backups
~/ai-stack/backup.sh --list

# Verify backup integrity
~/ai-stack/backup.sh --verify /path/to/backup.tgz

# Restore from backup
~/ai-stack/backup.sh --restore /path/to/backup.tgz
```

---

## Configuration Files

All configuration is stored in `~/ai-stack/`:

| File | Description |
|------|-------------|
| `docker-compose.yml` | Container orchestration |
| `ports.conf` | Port configuration |
| `secrets.conf` | API keys & passwords (delete after saving!) |
| `.install-config` | Full installation config |

### Security Note
After installation, save credentials from `secrets.conf` to your password manager, then delete the file:
```bash
cat ~/ai-stack/secrets.conf  # View credentials
rm ~/ai-stack/secrets.conf   # Delete after saving
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Browser                          │
└─────────────────────────┬───────────────────────────────────┘
                          │ :3000
┌─────────────────────────▼───────────────────────────────────┐
│                      OpenWebUI                               │
│                  (Chat Interface)                            │
└──────────┬─────────────────────────────────┬────────────────┘
           │                                 │
    ┌──────▼──────┐                  ┌───────▼───────┐
    │   Ollama    │                  │    Qdrant     │
    │   (LLMs)    │                  │  (Vectors)    │
    └─────────────┘                  └───────────────┘
           │
    ┌──────▼──────┐
    │  NVIDIA GPU │ (optional)
    └─────────────┘
```

---

## Updating

### Update AI.STACK
```bash
~/ai-stack/update.sh
```

### Update AI Models
```bash
~/ai-stack/update-models.sh
```

### Pull Specific Model
```bash
~/ai-stack/pull-model.sh llama3.2:latest
```

---

## Troubleshooting

### Check Service Status
```bash
~/ai-stack/status.sh
```

### View Logs
```bash
cd ~/ai-stack && docker compose logs -f
```

### Restart Services
```bash
~/ai-stack/restart.sh
```

### GPU Not Detected
```bash
# Check NVIDIA driver
nvidia-smi

# Reinstall container toolkit
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Port Already in Use
The installer automatically finds free ports. If issues persist:
```bash
~/ai-stack/show-ports.sh
```

---

## Uninstalling

```bash
~/ai-stack/uninstall.sh
```

Options:
1. **Containers only** - Keep data and config
2. **Containers + Config** - Keep user data
3. **Everything except models** - Fresh start, keep downloads
4. **Complete removal** - Remove everything

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [Ollama](https://ollama.ai/) - Local LLM runtime
- [OpenWebUI](https://openwebui.com/) - Beautiful chat interface
- [Qdrant](https://qdrant.tech/) - Vector database
- All the amazing open-source AI models

---

## Support

- **Issues**: [GitHub Issues](https://github.com/Rinkatecam/aistack/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Rinkatecam/aistack/discussions)

---

<p align="center">
  <b>Built with care by Rinkatecam & Atlas</b><br>
  <i>Your AI, Your Hardware, Your Data</i>
</p>
