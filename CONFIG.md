# Configuration Guide

## Overview

"What Did I Do Again?" uses a global configuration file stored in your home directory to manage credentials and settings for various integrations (Jira, GitHub, etc.).

## Configuration File Location

The configuration is stored as an `.env` file at:

```
~/.whatdidido/config.env
```

This file is automatically created when you run the `init` command for the first time.

## How Configuration Works

### Architecture

The configuration system consists of three main components:

1. **Config Storage** ([src/config.py:25-26](src/config.py#L25-L26))

   - Global config directory: `~/.whatdidido/`
   - Config file: `~/.whatdidido/config.env`

2. **Config Reading** ([src/config.py:29-43](src/config.py#L29-L43))

   - Uses `python-dotenv` to load environment variables from the config file
   - Provides strongly-typed config objects using Pydantic models

3. **Config Writing** ([src/config.py:46-62](src/config.py#L46-L62))
   - Updates individual key-value pairs in the config file
   - Preserves existing values when updating specific keys

### Supported Configuration Values

#### Jira Configuration

| Variable        | Description              | Example                             |
| --------------- | ------------------------ | ----------------------------------- |
| `JIRA_URL`      | Your Jira instance URL   | `https://your-domain.atlassian.net` |
| `JIRA_USERNAME` | Your Jira email/username | `your.email@company.com`            |
| `JIRA_API_KEY`  | Jira API token           | `ATATTxxxxxxxxxxxxx`                |

#### GitHub Configuration

| Variable       | Description                  | Example            |
| -------------- | ---------------------------- | ------------------ |
| `GITHUB_TOKEN` | GitHub personal access token | `ghp_xxxxxxxxxxxx` |

## Configuration Methods

### Method 1: Using the `init` Command (Recommended)

The easiest way to configure the tool is through the interactive setup:

```bash
whatdidido init
```

This will:

1. Prompt you to select which integrations to configure
2. Guide you through entering credentials for each selected integration
3. Automatically validate your credentials
4. Save the configuration to `~/.whatdidido/config.env`

The init command is smart:

- It detects if an integration is already configured
- It asks for confirmation before overwriting existing settings
- It validates credentials immediately after setup

### Method 2: Manual Configuration

You can also manually edit the config file directly:

1. Create the directory if it doesn't exist:

   ```bash
   mkdir -p ~/.whatdidido
   ```

2. Create or edit the config file:

   ```bash
   nano ~/.whatdidido/config.env
   ```

3. Add your configuration values:
   ```env
   JIRA_URL=https://your-domain.atlassian.net
   JIRA_USERNAME=your.email@company.com
   JIRA_API_KEY=ATATTxxxxxxxxxxxxx
   GITHUB_TOKEN=ghp_xxxxxxxxxxxx
   ```

## Obtaining API Credentials

### Jira API Token

1. Log in to your Atlassian account at https://id.atlassian.com
2. Go to Security → API tokens
3. Click "Create API token"
4. Give it a name (e.g., "whatdidido")
5. Copy the token immediately (you won't be able to see it again)

### GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a descriptive name
4. Select the required scopes (at minimum: `repo`, `read:user`)
5. Click "Generate token"
6. Copy the token immediately

## Configuration Validation

The tool validates your configuration in two ways:

1. **Configuration Check** ([src/providers/jira.py:13-19](src/providers/jira.py#L13-L19))

   - Ensures all required fields are present
   - Checked before attempting to sync

2. **Authentication Check** ([src/providers/jira.py:41-53](src/providers/jira.py#L41-L53))
   - Makes a test API call to verify credentials work
   - Displays server version information on success
   - Shows error message if authentication fails

## Security Considerations

- The config file contains sensitive credentials
- The file is stored in your home directory (not in the project directory)
- **Never commit the `~/.whatdidido/config.env` file to version control**
- File permissions should be set to be readable only by your user:
  ```bash
  chmod 600 ~/.whatdidido/config.env
  ```

## Troubleshooting

### "No authenticated integrations found"

This means either:

- You haven't run `init` yet
- Your credentials are missing or incorrect
- Your API tokens have expired

**Solution:** Run `whatdidido init` to reconfigure

### Configuration not being recognized

Check that:

1. The config file exists: `ls -la ~/.whatdidido/config.env`
2. The file has the correct format (KEY=VALUE pairs)
3. There are no extra spaces around the `=` sign
4. Values don't have quotes around them (unless the value itself contains quotes)

### Testing your configuration

You can test if your configuration is working by running:

```bash
whatdidido sync
```

This will attempt to authenticate with your configured integrations and show any errors.
