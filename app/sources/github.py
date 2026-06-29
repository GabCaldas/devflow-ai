import re

import httpx

from app.config import settings

GITHUB_API = "https://api.github.com"


class GitHubError(RuntimeError):
    pass


def parse_pr_url(url: str) -> tuple[str, str, int]:
    match = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", url)
    if not match:
        raise GitHubError(f"Invalid PR URL: {url}")
    owner, repo, number = match.groups()
    return owner, repo, int(number)


def _headers(as_diff: bool = False) -> dict:
    headers = {
        "Accept": "application/vnd.github.v3.diff"
        if as_diff
        else "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


async def fetch_pr_diff(owner: str, repo: str, number: int) -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{number}"
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.get(url, headers=_headers(as_diff=True))
        if resp.status_code == 404:
            raise GitHubError(
                f"PR not found ({owner}/{repo}#{number}). "
                "Private repo? Check GITHUB_TOKEN."
            )
        resp.raise_for_status()
        return resp.text


async def post_pr_comment(owner: str, repo: str, number: int, body: str) -> str:
    if not settings.github_token:
        raise GitHubError("GITHUB_TOKEN is missing - required to post a comment.")
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{number}/comments"
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(url, headers=_headers(), json={"body": body})
        resp.raise_for_status()
        return resp.json()["html_url"]
