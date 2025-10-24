# Configuration Guide

## Overview

"What Did I Do Again?" uses a global configuration file stored in your home directory to manage credentials and settings for various integrations (Jira, Linear, etc.).

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

#### Linear Configuration

| Variable         | Description      | Example            |
| ---------------- | ---------------- | ------------------ |
| `LINEAR_API_KEY` | Linear API token | `lin_xxxxxxxxxxxx` |

#### OpenAI Configuration

| Variable         | Description    | Example           |
| ---------------- | -------------- | ----------------- |
| `OPENAI_API_KEY` | OpenAI API key | `sk-xxxxxxxxxxxx` |

## Configuration Methods

### Method 1: Using the `connect` Command (Recommended)

The easiest way to configure the tool is through the interactive setup:

```bash
whatdidido connect
```

This will:

1. Prompt you to select which integrations to configure (Jira, Linear)
2. Guide you through entering credentials for each selected integration
3. Prompt you to configure service integrations (OpenAI)
4. Automatically validate your credentials
5. Save the configuration to `~/.whatdidido/config.env`

The connect command is smart:

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
   LINEAR_API_KEY=lin_xxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxx
   ```

## Obtaining API Credentials

### Jira API Token

1. Log in to your Atlassian account at https://id.atlassian.com
2. Click on Profile in top right and navigate to "Account Settings"
3. Click on "Security" and then click on "Create API token"
4. Give it a name (e.g., "whatdidido")
5. Copy the token immediately (you won't be able to see it again)

### Linear API Token

1. Log in to Linear at https://linear.app
2. Navigate to Settings → API → security and access settings
3. Under "Personal API keys", click "New API key"
4. Give it a descriptive name (e.g., "whatdidido")
5. Select the required scopes (at minimum: `read`)
6. Click "Create"
7. Copy the token immediately

### OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Give it a descriptive name (e.g., "whatdidido")
4. Click "Create secret key"
5. Copy the key immediately (you won't be able to see it again)
