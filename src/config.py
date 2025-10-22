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


class Config(BaseModel):
    jira: JiraConfig
    github: GithubConfig


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
    return Config(jira=jira_config, github=github_config)


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
