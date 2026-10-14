from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.cost import Metered
from app.domain.rubric import RubricPass
from app.llm.fake import FakeGrader
from app.llm.grader import ProviderUnavailableError, SpokenTask, WritingTask
from app.models import UsageEvent, WritingSubmission
from app.services import budget, grading
from app.services.users import get_or_create_learner
from app.services.writing import grade_pending

LESSON = "/lessons/a1-01-se-presenter/ecriture"
GOOD = (
    "Bonjour à tous ! Je m'appelle Arjun, j'ai trente-deux ans et je suis indien. "
    "J'habite à Pune, mais je voudrais vivre à Montréal. Je travaille comme ingénieur "
    "dans une entreprise informatique. J'apprends le français parce que je veux passer le TCF "
    "Canada et ensuite immigrer avec ma famille."
)
WITH_ERRORS = (
    "Bonjour, je suis Arjun et je suis trente ans. Il est un ingénieur. Je aime Montréal mais "
    "je n'ai pas une voiture. Je habite à Pune avec ma femme et nos deux enfants depuis 2020."
)


def test_fake_grader_flags_classic_errors() -> None:
    task = WritingTask("EE1", "Présentez-vous.", 40, 60)

    result = FakeGrader().grade_writing(task, WITH_ERRORS).value

    assert {e.tag for e in result.errors} == {"verb-choice", "article", "negation", "elision"}
    assert (
        result.criteria["grammar"]
        < FakeGrader().grade_writing(task, GOOD).value.criteria["grammar"]
    )


def test_lesson_writing_is_graded_metered_and_feeds_the_error_fingerprint(
    client: TestClient, seeded: Session
) -> None:
    result = client.post(f"{LESSON}/writing", json={"text": WITH_ERRORS}).json()

    assert result["status"] == "graded"
    assert 0 <= result["score"] <= 20
    assert set(result["criteria"]) == {"task", "coherence", "vocabulary", "grammar"}
    assert set(result["reasons"]) == set(result["criteria"])
    assert 1 <= len(result["fixes"]) <= 3
    assert len(seeded.scalars(select(UsageEvent)).all()) == 2  # two grading passes
    tags = {e["tag"] for e in client.get("/errors").json()}
    assert "verb-choice" in tags


def test_practice_writing_never_moves_the_writing_bar(client: TestClient, seeded: Session) -> None:
    client.post(f"{LESSON}/writing", json={"text": GOOD})

    assert client.get("/skills").json()["EE"] is None


def test_timed_writing_drill_produces_a_writing_estimate(
    client: TestClient, seeded: Session
) -> None:
    drill = client.post("/writing/drills").json()
    result = client.post(f"/writing/drills/{drill['run_id']}", json={"text": GOOD}).json()

    assert drill["task"] == "EE1"
    assert (drill["min_words"], drill["max_words"]) == (60, 120)
    assert datetime.fromisoformat(drill["deadline"]) > datetime.now(UTC) + timedelta(minutes=9)
    assert result["level"]["evidence_count"] == 1
    assert client.get("/skills").json()["EE"]["score"] == result["score"]
    assert client.post(f"/writing/drills/{drill['run_id']}", json={"text": GOOD}).status_code == 403


def test_budget_cap_defers_grading_and_the_job_catches_up(
    client: TestClient, seeded: Session
) -> None:
    user = get_or_create_learner(seeded)
    month = budget.current_window().key
    # Development grading costs nothing, so only a below-zero cap can block it.
    budget.set_caps(
        seeded,
        user.id,
        month,
        {"openai": Decimal("-0.01"), "speech": Decimal(1), "total": Decimal(1)},
    )

    deferred = client.post(f"{LESSON}/writing", json={"text": GOOD}).json()
    assert deferred["status"] == "pending"
    assert seeded.get_one(WritingSubmission, deferred["id"]).text == GOOD

    budget.set_caps(
        seeded, user.id, month, {"openai": Decimal(5), "speech": Decimal(1), "total": Decimal(6)}
    )
    assert grade_pending(seeded) == 1
    assert seeded.get_one(WritingSubmission, deferred["id"]).status == "graded"


class _DownGrader:
    model = "fake-text"

    def grade_writing(self, task: WritingTask, text: str) -> Metered[RubricPass]:
        raise ProviderUnavailableError("azure down")

    def grade_speaking(self, task: SpokenTask, transcript: str) -> Metered[RubricPass]:
        raise ProviderUnavailableError("azure down")


def test_provider_outage_leaves_the_submission_queued(seeded: Session) -> None:
    user = get_or_create_learner(seeded)
    task = WritingTask("EE1", "Présentez-vous.", 40, 60)
    submission = WritingSubmission(
        user_id=user.id, task="EE1", prompt=task.prompt, text=GOOD, word_count=50
    )
    seeded.add(submission)
    seeded.flush()

    assert grading.try_grade(seeded, submission, task, _DownGrader()) is False
    assert submission.status == "pending"
