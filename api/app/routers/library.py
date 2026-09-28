from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import or_, select

from app.db import SessionDep
from app.models import Card, Concept, Lesson, Lexeme, ModuleProgress, Sentence
from app.schemas.learning import ConceptOut, ReviewCard, ReviewRating, SentenceOut, WordOut
from app.services import library
from app.services.users import CurrentUser

router = APIRouter(tags=["library"])


@router.get("/reviews/due")
def due_reviews(session: SessionDep, user: CurrentUser, limit: int = 20) -> list[ReviewCard]:
    cards = library.due_cards(session, user.id, min(limit, 100), datetime.now(UTC))
    return [_review_card(session, card) for card in cards]


@router.post("/reviews/{card_id}")
def rate_card(
    card_id: int, body: ReviewRating, session: SessionDep, user: CurrentUser
) -> ReviewCard:
    card = library.review(session, user.id, card_id, body.rating, datetime.now(UTC))
    return _review_card(session, card)


@router.get("/library/words")
def learned_words(session: SessionDep, user: CurrentUser, q: str | None = None) -> list[WordOut]:
    query = select(Lexeme).join(
        Card, (Card.item_id == Lexeme.id) & (Card.item_type == "lexeme") & (Card.user_id == user.id)
    )
    if q:
        like = f"%{q}%"
        query = query.where(or_(Lexeme.lemma.ilike(like), Lexeme.en.ilike(like)))
    return [
        WordOut.model_validate(w, from_attributes=True)
        for w in session.scalars(query.order_by(Lexeme.lemma))
    ]


@router.get("/library/sentences")
def learned_sentences(
    session: SessionDep, user: CurrentUser, q: str | None = None
) -> list[SentenceOut]:
    query = select(Sentence).join(
        Card,
        (Card.item_id == Sentence.id) & (Card.item_type == "sentence") & (Card.user_id == user.id),
    )
    if q:
        like = f"%{q}%"
        query = query.where(or_(Sentence.fr.ilike(like), Sentence.en.ilike(like)))
    return [SentenceOut.model_validate(s, from_attributes=True) for s in session.scalars(query)]


@router.get("/library/concepts")
def learned_concepts(session: SessionDep, user: CurrentUser) -> list[ConceptOut]:
    progress = session.scalars(select(ModuleProgress).where(ModuleProgress.user_id == user.id))
    done = [lesson_id for p in progress for lesson_id in p.lessons_done]
    grammar_lessons = session.scalars(
        select(Lesson).where(Lesson.kind == "grammar", Lesson.id.in_(done))
    )
    concept_ids = [f"{lesson.module_id}/{lesson.payload['concept']}" for lesson in grammar_lessons]
    concepts = session.scalars(select(Concept).where(Concept.id.in_(concept_ids)))
    return [ConceptOut.model_validate(c, from_attributes=True) for c in concepts]


def _review_card(session: SessionDep, card: Card) -> ReviewCard:
    if card.item_type == "lexeme":
        word = session.get_one(Lexeme, card.item_id)
        prompt, answer, gender, example = word.en, word.lemma, word.gender, word.example_fr
    else:
        sentence = session.get_one(Sentence, card.item_id)
        prompt, answer, gender, example = sentence.en, sentence.fr, None, None
    return ReviewCard(
        id=card.id,
        item_type=card.item_type,
        prompt_en=prompt,
        answer_fr=answer,
        gender=gender,
        example_fr=example,
        due_at=card.due_at,
        reviews=card.reviews,
    )
