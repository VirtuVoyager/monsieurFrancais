from fastapi import APIRouter

from app.db import SessionDep
from app.schemas.learning import GlossOut
from app.services import glossary
from app.services.users import CurrentUser

router = APIRouter(tags=["glossary"])


@router.get("/glossary")
def get_glossary(
    session: SessionDep, user: CurrentUser, module_id: str | None = None
) -> dict[str, GlossOut]:
    entries = glossary.for_learner(session, user.id, module_id)
    return {form: GlossOut.model_validate(gloss) for form, gloss in entries.items()}
