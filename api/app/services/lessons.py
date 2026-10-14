from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.exercises import CheckResult, check, public
from app.errors import NotFoundError
from app.models import Concept, Lesson, Lexeme, Sentence
from app.presenters import sentence_out, word_out
from app.schemas.learning import (
    ExerciseOut,
    GrammarContent,
    LessonContent,
    ListeningContent,
    ReadingContent,
    SentencesContent,
    SpeakingContent,
    VocabContent,
    WritingContent,
)
from app.services import audio


def get_lesson(session: Session, lesson_id: str) -> Lesson:
    lesson = session.get(Lesson, lesson_id)
    if lesson is None:
        raise NotFoundError(f"Lesson {lesson_id} not found")
    return lesson


def exercises(lesson: Lesson) -> list[dict[str, Any]]:
    return list(lesson.payload.get("exercises") or lesson.payload.get("questions") or [])


def check_exercise(lesson: Lesson, index: int, response: dict[str, Any]) -> CheckResult:
    items = exercises(lesson)
    if index >= len(items):
        raise NotFoundError(f"Exercise {index} not found in {lesson.id}")
    return check(items[index], response)


def content(session: Session, lesson: Lesson) -> LessonContent:  # noqa: PLR0911
    payload = lesson.payload
    public_exercises = [ExerciseOut.model_validate(public(ex)) for ex in exercises(lesson)]
    match lesson.kind:
        case "grammar":
            concept = session.get(Concept, f"{lesson.module_id}/{payload['concept']}")
            if concept is None:
                raise NotFoundError(f"Concept {payload['concept']} not found")
            return GrammarContent(
                concept_title=concept.title, concept_md=concept.body_md, exercises=public_exercises
            )
        case "vocab":
            words = session.scalars(
                select(Lexeme).where(Lexeme.module_id == lesson.module_id).order_by(Lexeme.id)
            )
            return VocabContent(words=[word_out(w) for w in words])
        case "sentences":
            rows = session.scalars(select(Sentence).where(Sentence.module_id == lesson.module_id))
            return SentencesContent(sentences=[sentence_out(s) for s in rows])
        case "listening":
            return ListeningContent(
                transcript=payload["transcript"].strip(),
                audio_url=audio.url_for(audio.lesson_request(lesson)),
                exercises=public_exercises,
            )
        case "reading":
            return ReadingContent(text=payload["text"].strip(), exercises=public_exercises)
        case "writing":
            return WritingContent(
                task=payload["task"],
                prompt=payload["prompt"].strip(),
                min_words=payload["min_words"],
                max_words=payload["max_words"],
            )
        case "speaking":
            return SpeakingContent(
                task=payload["task"], prompt=payload["prompt"].strip(), seconds=payload["seconds"]
            )
    raise ValueError(f"Unknown lesson kind {lesson.kind}")
