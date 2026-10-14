from fastapi import APIRouter

from app.db import SessionDep
from app.schemas.learning import SearchHit
from app.services import knowledge
from app.services.knowledge import Scope
from app.services.users import CurrentUser

router = APIRouter(tags=["search"])


@router.get("/search")
def search(
    q: str,
    session: SessionDep,
    user: CurrentUser,
    scope: Scope = "learned",
    kind: str | None = None,
) -> list[SearchHit]:
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
        for e in knowledge.search(session, user.id, q, scope, kind)
    ]
