from app.models import Module
from app.schemas.learning import LessonSummary, ModuleDetail, ModuleSummary
from app.services.path import PathView


def module_summary(module: Module, view: PathView) -> ModuleSummary:
    progress = view.progress.get(module.id)
    return ModuleSummary(
        id=module.id,
        order=module.order,
        title=module.title,
        theme=module.theme,
        status=view.status[module.id],
        lessons_total=len(module.lessons),
        lessons_done=len(view.lessons_done(module.id)),
        check_score=progress.check_score if progress else None,
    )


def module_detail(module: Module, view: PathView) -> ModuleDetail:
    done = view.lessons_done(module.id)
    return ModuleDetail(
        **module_summary(module, view).model_dump(),
        level=module.level_id,
        summary=module.summary,
        lessons=[
            LessonSummary(
                id=lesson.id, kind=lesson.kind, title=lesson.title, done=lesson.id in done
            )
            for lesson in module.lessons
        ],
        can_take_check=len(done) >= len(module.lessons),
    )
