"""Read-only MCP server over the learner's data, for Claude or any other MCP client (stdio)."""

from mcp.server.mcpserver import MCPServer
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.routers.skills import level_out
from app.schemas.learning import ErrorFingerprintOut, SearchHit, SkillLevelOut
from app.services import grading, knowledge, skills
from app.services.knowledge import Scope
from app.services.path import load_path
from app.services.users import get_or_create_learner

server = MCPServer(
    name="monsieur-francais",
    instructions=(
        "The learner's TCF Canada preparation data: what they have learned, their skill "
        "estimates on exam scales, and their most frequent errors. Use it to ground coaching."
    ),
)


def search_learned(session: Session, query: str, scope: Scope) -> list[SearchHit]:
    user = get_or_create_learner(session)
    return [
        SearchHit(
            key=e.key,
            kind=e.kind,
            title=e.title,
            text=e.text,
            source_ref=e.source_ref,
            cefr=e.cefr,
            personal=e.user_id is not None,
        )
        for e in knowledge.search(session, user.id, query, scope)
    ]


def skill_levels(session: Session) -> dict[str, SkillLevelOut | None]:
    user = get_or_create_learner(session)
    return {skill: level_out(level) for skill, level in skills.all_levels(session, user.id).items()}


def error_fingerprint(session: Session) -> list[ErrorFingerprintOut]:
    user = get_or_create_learner(session)
    return [
        ErrorFingerprintOut(tag=e.tag, count=e.count, example=e.example, correction=e.correction)
        for e in grading.top_errors(session, user.id)
    ]


def progress(session: Session) -> dict[str, object]:
    view = load_path(session, get_or_create_learner(session).id)
    return {
        "covered_modules": view.coverage.covered,
        "total_modules": view.coverage.total,
        "by_level": {
            level: {"covered": c, "total": t} for level, (c, t) in view.coverage.by_level.items()
        },
        "open_module": next((m.title for m in view.modules if view.status[m.id] == "open"), None),
    }


@server.tool()
def search_kb(query: str, scope: Scope = "learned") -> list[SearchHit]:
    """Search words, sentences, grammar and the learner's own errors and feedback (FR or EN)."""
    with SessionLocal() as session:
        return search_learned(session, query, scope)


@server.tool()
def get_skill_levels() -> dict[str, SkillLevelOut | None]:
    """Current estimates per TCF skill (CO, CE, EE, EO) with CEFR, NCLC and uncertainty."""
    with SessionLocal() as session:
        return skill_levels(session)


@server.tool()
def get_error_fingerprint() -> list[ErrorFingerprintOut]:
    """The learner's five most frequent error types, with an example and its correction."""
    with SessionLocal() as session:
        return error_fingerprint(session)


@server.tool()
def get_progress() -> dict[str, object]:
    """Module coverage overall and per CEFR level, and the module currently open."""
    with SessionLocal() as session:
        return progress(session)


if __name__ == "__main__":
    server.run("stdio")
