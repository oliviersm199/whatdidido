# What Did I Do Again?

[![PyPI version](https://badge.fury.io/py/whatdidido.svg)](https://badge.fury.io/py/whatdidido)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Track your work across Jira and Linear. Generate AI-powered summaries of your activities.**

`whatdidido` is a command-line tool that syncs your work items from ticketing systems (Jira, Linear) and generates intelligent summaries using OpenAI. Perfect for status reports, performance reviews, and keeping track of what you've accomplished.

## Features

- **Multi-Platform Sync**: Connect to Jira and Linear simultaneously
- **AI-Powered Summaries**: Generate narrative reports using OpenAI
- **Secure**: Credentials and all data stored on your computer
- **Fast Setup**: Interactive configuration wizard
- **Flexible Reporting**: Filter by date range, user, and more
- **Team-Friendly**: Track work for multiple team members

## Installation

Install via pip:

```bash
pip install whatdidido
```

**Requirements:** Python 3.13 or higher

For detailed installation instructions, see [INSTALL.md](INSTALL.md).

## Quick Start

### 1. Configure Your Integrations

```bash
whatdidido connect
```

This interactive wizard will guide you through:

- Selecting which integrations to connect (Jira, Linear)
- Entering API credentials
- Configuring OpenAI for AI summaries (optional)

### 2. Sync Your Work

```bash
whatdidido sync
```

Fetches your work items from all configured integrations.

### 3. Generate a Report

```bash
whatdidido report
```

Creates an AI-powered summary of your activities in `whatdidido.md`.

## Usage Examples

```bash
# Sync work from the last 30 days (Suppose today is 2025-10-23)
whatdidido sync --start-date 2025-09-23

# Sync work for a specific user
whatdidido sync --user colleague@company.com

# Sync a specific date range
whatdidido sync --start-date 2024-01-01 --end-date 2024-12-31

# View current configuration
whatdidido config

# Clean up synced data
whatdidido clean
```

## Available Commands

| Command      | Description                              |
| ------------ | ---------------------------------------- |
| `connect`    | Configure integrations and credentials   |
| `sync`       | Fetch work items from configured sources |
| `report`     | Generate AI-powered summary report       |
| `config`     | Display current configuration            |
| `disconnect` | Remove integration credentials           |
| `clean`      | Delete synced data files                 |

For comprehensive usage instructions, see [USER_GUIDE.md](USER_GUIDE.md).

## Documentation

- **[Configuration Guide](CONFIG.md)** - How to obtain and configure API credentials

## Supported Integrations

### Data Sources (Ticketing Systems)

- **Jira** - Full support
- **Linear** - Full support
- PENDING **GitHub** - Planned for future release

### Service Integrations

- **OpenAI** - For AI-powered report generation
- **OpenRouter** - Same as OpenAI, support for cha

## Requirements

- Python 3.13 or higher
- API credentials for at least one data source (Jira or Linear)
- OpenAI API key (optional, required for `report` command)

## Contributing

We welcome contributions! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests: `pytest`
5. Format code: `black .`
6. Submit a pull request

### Development Setup

For local development:

```bash
git clone https://github.com/oliviersm199/whatdididoagain.git
cd whatdididoagain
pip install -e ".[dev]"
pre-commit install
```

### Running Tests

```bash
pytest
pytest --cov=src  # with coverage
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/oliviersm199/whatdididoagain/issues)
- **Discussions**: [GitHub Discussions](https://github.com/oliviersm199/whatdididoagain/discussions)

## Roadmap

- [ ] GitHub integration support
- [ ] GitLab integration support
- [ ] Slack notifications
- [ ] Custom report templates
- [ ] Export to multiple formats (PDF, HTML)
- [ ] Team analytics and insights
