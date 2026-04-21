"""CLI entry point for skateboard-phase verification.

Lets you exercise the agents end-to-end without spinning up the full A2A server.
"""
from __future__ import annotations

import asyncio
from datetime import date

import typer
from rich import print

from .agents import (
    build_analysis_agent,
    build_notification_agent,
    build_search_agent,
)
from .memory import load_user_context
from .tools.supabase_tool import (
    get_or_create_default_user,
    update_user_profile,
)

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _run(coro):
    return asyncio.run(coro)


@app.command()
def search(query: str, days: int = 7):
    """Pull recent papers on a query and persist them to Supabase."""
    agent = build_search_agent()
    prompt = f"Find the top papers on '{query}' from the last {days} days and persist them."
    result = _run(agent.run(prompt))
    print(result.last_message.text)


@app.command()
def analyze(arxiv_id: str):
    """Break down a single paper into sections + a Henry-specific application."""
    agent = build_analysis_agent()
    prompt = (
        f"Analyze arxiv paper {arxiv_id}. Fetch the PDF, produce the JSON "
        "output described in the system prompt, and persist the analysis + embedding."
    )
    result = _run(agent.run(prompt))
    print(result.last_message.text)


@app.command()
def digest():
    """Run the notification agent manually — builds today's digest row."""
    agent = build_notification_agent()
    prompt = (
        f"It's {date.today().isoformat()}. Build today's digest following "
        "the steps in your instructions."
    )
    result = _run(agent.run(prompt))
    print(result.last_message.text)


@app.command()
def profile(
    role: str = typer.Option(None),
    work_context: str = typer.Option(None),
    interests: str = typer.Option(None, help="Comma-separated list."),
    tech_stack: str = typer.Option(None, help="Comma-separated list."),
    goals: str = typer.Option(None),
):
    """Seed or update Henry's user profile from the CLI (shortcut around onboarding chat)."""
    user = get_or_create_default_user()
    updates = {}
    if role:
        updates["role"] = role
    if work_context:
        updates["work_context"] = work_context
    if interests:
        updates["interests"] = [s.strip() for s in interests.split(",") if s.strip()]
    if tech_stack:
        updates["tech_stack"] = [s.strip() for s in tech_stack.split(",") if s.strip()]
    if goals:
        updates["goals"] = goals
    if not updates:
        print("[yellow]No fields to update. See --help.[/yellow]")
        return
    updated = update_user_profile(user["id"], updates)
    print(updated)


@app.command()
def whoami():
    """Print the currently-loaded user context (debugging aid)."""
    ctx = load_user_context()
    print(ctx)


if __name__ == "__main__":
    app()
