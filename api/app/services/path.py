from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.coverage import Coverage, ModuleFacts, Status, coverage, statuses
from app.errors import ForbiddenError, NotFoundError
from app.models import Lesson, Module, ModuleProgress


@dataclass(frozen=True)
class PathView:
    modules: list[Module]
    progress: dict[str, ModuleProgress]
    status: dict[str, Status]
    coverage: Coverage

    def lessons_done(self, module_id: str) -> set[str]:
        progress = self.progress.get(module_id)
        return set(progress.lessons_done) if progress else set()

    def next_lesson(self) -> Lesson | None:
        for module in self.modules:
            if self.status[module.id] == Status.OPEN:
                done = self.lessons_done(module.id)
                return next((lesson for lesson in module.lessons if lesson.id not in done), None)
        return None


def load_path(session: Session, user_id: int) -> PathView:
    modules = list(session.scalars(select(Module).order_by(Module.order)))
    progress = {
        p.module_id: p
        for p in session.scalars(select(ModuleProgress).where(ModuleProgress.user_id == user_id))
    }
    facts = [
        ModuleFacts(
            module_id=m.id,
            level=m.level_id,
            lessons_total=len(m.lessons),
            lessons_done=len(progress[m.id].lessons_done) if m.id in progress else 0,
            check_score=progress[m.id].check_score if m.id in progress else None,
            placed=m.id in progress and progress[m.id].status == Status.PLACED,
        )
        for m in modules
    ]
    status = statuses(facts)
    return PathView(modules, progress, status, coverage(facts, status))


def open_module(session: Session, user_id: int, module_id: str) -> tuple[Module, PathView]:
    view = load_path(session, user_id)
    module = next((m for m in view.modules if m.id == module_id), None)
    if module is None:
        raise NotFoundError(f"Module {module_id} not found")
    if view.status[module_id] == Status.LOCKED:
        raise ForbiddenError("Finish the previous module first")
    return module, view


def module_progress(session: Session, user_id: int, module_id: str) -> ModuleProgress:
    progress = session.get(ModuleProgress, (user_id, module_id))
    if progress is None:
        progress = ModuleProgress(user_id=user_id, module_id=module_id, lessons_done=[])
        session.add(progress)
    return progress
