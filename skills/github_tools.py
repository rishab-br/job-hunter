from datetime import datetime, timezone
from github import Github, GithubException
from config import settings

_client: Github | None = None


def get_client(token: str | None = None) -> Github:
    if token:
        return Github(token)
    global _client
    if _client is None:
        _client = Github(settings.github_token or None)
    return _client


def get_profile(username: str, token: str | None = None) -> dict:
    user = get_client(token).get_user(username)
    return {
        "login":        user.login,
        "name":         user.name,
        "bio":          user.bio,
        "company":      user.company,
        "location":     user.location,
        "blog":         user.blog,
        "public_repos": user.public_repos,
        "followers":    user.followers,
        "following":    user.following,
        "created_at":   user.created_at.isoformat(),
        "avatar_url":   user.avatar_url,
        "html_url":     user.html_url,
    }


def get_repos(username: str, token: str | None = None) -> list[dict]:
    user = get_client(token).get_user(username)
    repos = []
    for repo in user.get_repos(type="owner"):
        if repo.fork:
            continue
        last_pushed = repo.pushed_at.isoformat() if repo.pushed_at else None
        repos.append({
            "name":        repo.name,
            "description": repo.description,
            "language":    repo.language,
            "stars":       repo.stargazers_count,
            "forks":       repo.forks_count,
            "watchers":    repo.watchers_count,
            "topics":      list(repo.get_topics()),
            "has_readme":  _has_readme(repo),
            "open_issues": repo.open_issues_count,
            "last_pushed": last_pushed,
            "created_at":  repo.created_at.isoformat(),
            "url":         repo.html_url,
            "size_kb":     repo.size,
            "default_branch": repo.default_branch,
            "has_wiki":    repo.has_wiki,
            "has_pages":   repo.has_pages,
            "license":     repo.license.name if repo.license else None,
        })
    return repos


def get_readme_content(username: str, repo_name: str, token: str | None = None) -> str | None:
    try:
        repo = get_client(token).get_repo(f"{username}/{repo_name}")
        readme = repo.get_readme()
        return readme.decoded_content.decode("utf-8", errors="replace")
    except GithubException:
        return None


def get_languages(username: str, repo_name: str, token: str | None = None) -> dict[str, int]:
    try:
        repo = get_client(token).get_repo(f"{username}/{repo_name}")
        return dict(repo.get_languages())
    except GithubException:
        return {}


def days_since(iso_timestamp: str | None) -> int | None:
    if not iso_timestamp:
        return None
    ts = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - ts).days


def _has_readme(repo) -> bool:
    try:
        repo.get_readme()
        return True
    except GithubException:
        return False
