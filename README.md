# What Did I Do Again?

[![PyPI version](https://badge.fury.io/py/whatdidido.svg)](https://badge.fury.io/py/whatdidido.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Track your work across Jira and Linear. Generate AI-powered summaries of your activities.**

**Runs 100% locally on your machine. Bring your own API keys (BYOK) - your credentials stay under your control.**

`whatdidido` is a command-line tool that syncs your work items from ticketing systems (Jira, Linear) and generates intelligent summaries using OpenAI. Perfect for status reports, performance reviews, and keeping track of what you've accomplished.

![Example Output](images/exampleOutput.png)

## Installation

Prequisite is [Python 3.10](https://www.python.org/downloads/) and above installed

### pip

```bash
pip install whatdidido
```

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

## Cost Considerations

When using the AI-powered summarization feature, OpenAI API usage will incur costs. Here's what to expect:

**Example Usage Cost:**

- **19 Jira tickets analyzed**
- **API Usage:** ~25,000 input tokens, ~3,079 output tokens
- **Approximate Cost:** $0.06 USD

Actual costs will vary based on:

- Number of work items synced
- Complexity and length of ticket descriptions
- OpenAI model used (configurable)
- Frequency of report generation

**Cost Management Tips:**

- Use date ranges to limit the number of items synced
- Sync only when you need to generate reports
- Monitor your OpenAI API usage at [platform.openai.com](https://platform.openai.com)

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
