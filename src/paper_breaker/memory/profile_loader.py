from __future__ import annotations

from dataclasses import dataclass

from ..tools.supabase_tool import (
    get_or_create_default_user,
    recent_interactions,
    get_active_topics,
)


@dataclass
class UserContext:
    """The durable memory each agent hydrates from Supabase before running."""

    user_id: str
    role: str | None
    work_context: str | None
    interests: list[str]
    tech_stack: list[str]
    goals: str | None
    recent_saves: list[str]
    recent_dismisses: list[str]
    active_topics: list[str]


def load_user_context() -> UserContext:
    profile = get_or_create_default_user()
    ixns = recent_interactions(profile["id"], limit=50)
    topics = get_active_topics(profile["id"])
    saves = [i["paper_id"] for i in ixns if i["type"] == "saved"][:10]
    dismisses = [i["paper_id"] for i in ixns if i["type"] == "dismissed"][:10]
    return UserContext(
        user_id=profile["id"],
        role=profile.get("role"),
        work_context=profile.get("work_context"),
        interests=list(profile.get("interests") or []),
        tech_stack=list(profile.get("tech_stack") or []),
        goals=profile.get("goals"),
        recent_saves=saves,
        recent_dismisses=dismisses,
        active_topics=[t["query"] for t in topics],
    )


def format_user_context_prompt(ctx: UserContext) -> str:
    """Render the user context as a system-prompt fragment."""
    lines = ["## User profile (Henry)"]
    if ctx.role:
        lines.append(f"- Role: {ctx.role}")
    if ctx.work_context:
        lines.append(f"- Day-to-day work: {ctx.work_context}")
    if ctx.interests:
        lines.append(f"- Interests: {', '.join(ctx.interests)}")
    if ctx.tech_stack:
        lines.append(f"- Tech stack: {', '.join(ctx.tech_stack)}")
    if ctx.goals:
        lines.append(f"- Goals: {ctx.goals}")
    if ctx.active_topics:
        lines.append(f"- Standing topics: {', '.join(ctx.active_topics)}")
    if ctx.recent_saves:
        lines.append(f"- Recently saved paper ids: {', '.join(ctx.recent_saves[:5])}")
    if ctx.recent_dismisses:
        lines.append(
            f"- Recently dismissed paper ids (avoid re-recommending): "
            f"{', '.join(ctx.recent_dismisses[:5])}"
        )
    if len(lines) == 1:
        lines.append(
            "- (No profile yet. Ask onboarding questions if the user hasn't answered them.)"
        )
    return "\n".join(lines)
