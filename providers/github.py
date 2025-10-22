from providers.base import BaseProvider


class GithubProvider(BaseProvider):
    async def fetch_items(self, start_date, end_date):
        # Implementation for fetching GitHub issues and PRs
        pass

    def authenticate(self):
        # Implementation for authenticating with GitHub
        pass

    def is_configured(self) -> bool:
        # Implementation to check if GitHub is configured
        pass

    def setup(self):
        pass

    def get_name(self) -> str:
        return "GitHub"
