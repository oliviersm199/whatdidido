import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class JiraConfig(BaseModel):
    jira_url: str
    jira_username: str
    jira_api_key: str


class LinearConfig(BaseModel):
    linear_api_key: str


class OpenAIConfig(BaseModel):
    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    openai_workitem_summary_model: str = "gpt-4o-mini"
    openai_summary_model: str = "gpt-5"


class Config(BaseModel):
    jira: JiraConfig
    linear: LinearConfig
    openai: OpenAIConfig


CONFIG_DIR = Path.home() / ".whatdidido"
CONFIG_FILE = CONFIG_DIR / "config.env"


def get_config() -> Config:
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.touch()

    # Always reload the config file to get latest values
    load_dotenv(CONFIG_FILE, override=True)

    jira_config = JiraConfig(
        jira_url=os.getenv("JIRA_URL", ""),
        jira_username=os.getenv("JIRA_USERNAME", ""),
        jira_api_key=os.getenv("JIRA_API_KEY", ""),
    )
    linear_config = LinearConfig(
        linear_api_key=os.getenv("LINEAR_API_KEY", ""),
    )

    openai_config = OpenAIConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openai_workitem_summary_model=os.getenv(
            "OPENAI_WORKITEM_SUMMARY_MODEL", "gpt-4o-mini"
        ),
        openai_summary_model=os.getenv("OPENAI_SUMMARY_MODEL", "gpt-5"),
    )

    return Config(
        jira=jira_config,
        linear=linear_config,
        openai=openai_config,
    )


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
