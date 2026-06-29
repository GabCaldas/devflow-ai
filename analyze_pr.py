import asyncio
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from rich.console import Console

from app.config import settings
from app.graph import analyze
from app.report import to_markdown
from app.sources.github import (
    GitHubError,
    fetch_pr_diff,
    parse_pr_url,
    post_pr_comment,
)

console = Console()


async def main() -> None:
    if len(sys.argv) < 2:
        console.print("[red]Usage: python analyze_pr.py <pr-url> [--post][/red]")
        raise SystemExit(1)

    url = sys.argv[1]
    should_post = "--post" in sys.argv

    owner, repo, number = parse_pr_url(url)
    console.print(f"[bold cyan]Analyzing[/bold cyan] {owner}/{repo}#{number}")

    with console.status("[green]Fetching PR diff..."):
        diff = await fetch_pr_diff(owner, repo, number)
    diff = diff[: settings.max_diff_chars]
    console.print(f"[dim]diff: {len(diff)} characters[/dim]")

    with console.status("[green]Agents analyzing..."):
        state = await analyze(diff, language=None)

    report = to_markdown(state)
    console.print(report)

    if should_post:
        with console.status("[green]Posting comment on PR..."):
            comment_url = await post_pr_comment(owner, repo, number, report)
        console.print(f"[bold green]Comment posted:[/bold green] {comment_url}")
    else:
        console.print("[dim]Use --post to publish this review as a PR comment.[/dim]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except GitHubError as exc:
        Console().print(f"[red]GitHub error:[/red] {exc}")
        raise SystemExit(1)
