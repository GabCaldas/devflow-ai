"""Analisa um Pull Request do GitHub de ponta a ponta.

Fluxo: busca o diff do PR -> roda o pipeline multi-agente -> imprime o
relatorio -> (opcional) posta a revisao como comentario no PR.

Uso:
    python analisar_pr.py https://github.com/owner/repo/pull/123
    python analisar_pr.py https://github.com/owner/repo/pull/123 --post
"""
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
        console.print("[red]Uso: python analisar_pr.py <url-do-pr> [--post][/red]")
        raise SystemExit(1)

    url = sys.argv[1]
    should_post = "--post" in sys.argv

    owner, repo, number = parse_pr_url(url)
    console.print(f"[bold cyan]Analisando[/bold cyan] {owner}/{repo}#{number}")

    with console.status("[green]Buscando diff do PR..."):
        diff = await fetch_pr_diff(owner, repo, number)
    diff = diff[: settings.max_diff_chars]
    console.print(f"[dim]diff: {len(diff)} caracteres[/dim]")

    with console.status("[green]Agentes analisando..."):
        state = await analyze(diff, language=None)

    console.print(to_markdown(state))

    if should_post:
        with console.status("[green]Postando comentario no PR..."):
            comment_url = await post_pr_comment(owner, repo, number, to_markdown(state))
        console.print(f"[bold green]Comentario postado:[/bold green] {comment_url}")
    else:
        console.print(
            "[dim]Use --post para publicar essa revisao como comentario no PR.[/dim]"
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except GitHubError as exc:
        Console().print(f"[red]Erro GitHub:[/red] {exc}")
        raise SystemExit(1)
