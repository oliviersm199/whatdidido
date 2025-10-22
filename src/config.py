import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class JiraConfig(BaseModel):
    jira_url: str
    jira_username: str
    jira_api_key: str


class GithubConfig(BaseModel):
    github_token: str


class OpenRouterConfig(BaseModel):
    openrouter_api_key: str
    openrouter_workitem_summary_model: str = "anthropic/claude-haiku-4.5"
    openrouter_summary_model: str = "anthropic/claude-sonnet-4.5"


class Config(BaseModel):
    jira: JiraConfig
    github: GithubConfig
    openrouter: OpenRouterConfig


CONFIG_DIR = Path.home() / ".whatdididoagain"
CONFIG_FILE = CONFIG_DIR / "config.env"


def get_config() -> Config:
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.touch()
    else:
        load_dotenv(CONFIG_FILE)

    jira_config = JiraConfig(
        jira_url=os.getenv("JIRA_URL", ""),
        jira_username=os.getenv("JIRA_USERNAME", ""),
        jira_api_key=os.getenv("JIRA_API_KEY", ""),
    )
    github_config = GithubConfig(github_token=os.getenv("GITHUB_TOKEN", ""))

    openrouter_config = OpenRouterConfig(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_workitem_summary_model=os.getenv(
            "OPENROUTER_WORKITEM_SUMMARY_MODEL", "anthropic/claude-haiku-4.5"
        ),
        openrouter_summary_model=os.getenv(
            "OPENROUTER_OVERALL_SUMMARY_MODEL", "anthropic/claude-sonnet-4.5"
        ),
    )
    return Config(jira=jira_config, github=github_config, openrouter=openrouter_config)


def update_config(key: str, value: str):
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True)
    lines = []
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            lines = f.readlines()
    key_found = False
    with open(CONFIG_FILE, "w") as f:
        for line in lines:
            if line.startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                key_found = True
            else:
                f.write(line)
        if not key_found:
            f.write(f"{key}={value}\n")
