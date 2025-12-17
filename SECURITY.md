# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 5.x.x   | :white_check_mark: |
| < 5.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, please:

1. **Email** your findings to the maintainers (create a private security advisory on GitHub)
2. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment** within 48 hours
- **Status update** within 7 days
- **Resolution timeline** based on severity

### Severity Levels

| Severity | Response Time | Examples |
|----------|--------------|----------|
| Critical | 24-48 hours | RCE, credential exposure |
| High | 7 days | Privilege escalation, data leak |
| Medium | 30 days | Information disclosure |
| Low | 90 days | Minor issues |

## Security Best Practices

When using AI.STACK:

### During Installation

1. **Review the script** before running:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/Rinkatecam/aistack/main/install_aistack.sh -o install_aistack.sh
   less install_aistack.sh  # Review the code
   bash install_aistack.sh
   ```

2. **Use Secure Install mode** for production:
   - Randomized ports
   - Localhost binding
   - Hardened firewall rules

### After Installation

1. **Save credentials securely**:
   ```bash
   cat ~/ai-stack/secrets.conf  # Copy to password manager
   rm ~/ai-stack/secrets.conf   # Delete the file
   ```

2. **Rotate secrets** if compromised:
   ```bash
   ~/ai-stack/rotate-secrets.sh
   ```

3. **Keep updated**:
   ```bash
   ~/ai-stack/update.sh
   ```

4. **Regular backups**:
   ```bash
   ~/ai-stack/backup.sh
   ```

### Network Security

- **Don't expose** internal services to the internet without proper authentication
- **Use a reverse proxy** (nginx, Traefik) for production deployments
- **Enable HTTPS** for any internet-facing services
- **Firewall** - Only open necessary ports

### Data Security

- AI.STACK processes data **locally** - nothing sent to cloud
- Vector embeddings are stored in local Qdrant instance
- Conversation history stays in local OpenWebUI database
- **You control your data**

## Security Features

AI.STACK includes several security features:

| Feature | Description |
|---------|-------------|
| Port Randomization | Internal services use random ports |
| Credential Generation | Cryptographically secure secrets |
| Firewall Configuration | Automatic UFW rules |
| Localhost Binding | Option to restrict to local access |
| No Telemetry | Zero data collection |

## Known Limitations

- Default installation trusts local network
- Web UI has no built-in HTTPS (use reverse proxy)
- First user becomes admin (secure your first login)

## Security Checklist

- [ ] Reviewed installation script before running
- [ ] Used Secure Install mode for production
- [ ] Saved credentials to password manager
- [ ] Deleted secrets.conf file
- [ ] Configured firewall appropriately
- [ ] Set up HTTPS if internet-facing
- [ ] Scheduled regular backups
- [ ] Keep system and AI.STACK updated

## Acknowledgments

We appreciate security researchers who help keep AI.STACK secure. Responsible disclosure will be acknowledged in our security advisories.
