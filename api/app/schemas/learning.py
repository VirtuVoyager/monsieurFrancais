from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from app.domain.coverage import Status


class CoverageOut(BaseModel):
    covered: int
    total: int
    percent: float


class ModuleSummary(BaseModel):
    id: str
    order: int
    title: str
    theme: str
    status: Status
    lessons_total: int
    lessons_done: int
    check_score: float | None


class LevelOut(BaseModel):
    id: str
    covered: int
    total: int
    modules: list[ModuleSummary]


class NextLesson(BaseModel):
    module_id: str
    module_title: str
    lesson_id: str
    lesson_title: str


class PathOut(BaseModel):
    coverage: CoverageOut
    levels: list[LevelOut]
    next_lesson: NextLesson | None


class LessonSummary(BaseModel):
    id: str
    kind: str
    title: str
    done: bool


class ModuleDetail(ModuleSummary):
    level: str
    summary: str
    lessons: list[LessonSummary]
    can_take_check: bool


class ExerciseOut(BaseModel):
    kind: Literal["mcq", "cloze", "order"]
    prompt: str | None = None
    options: list[str] | None = None
    words: list[str] | None = None
    passage: str | None = None
    audio_text: str | None = None
    audio_url: str | None = None


class WordOut(BaseModel):
    id: str
    lemma: str
    pos: str
    gender: str | None
    en: str
    example_fr: str
    example_en: str
    audio_url: str | None = None


class SentenceOut(BaseModel):
    id: str
    fr: str
    en: str
    audio_url: str | None = None


class GrammarContent(BaseModel):
    kind: Literal["grammar"] = "grammar"
    concept_title: str
    concept_md: str
    exercises: list[ExerciseOut]


class VocabContent(BaseModel):
    kind: Literal["vocab"] = "vocab"
    words: list[WordOut]


class SentencesContent(BaseModel):
    kind: Literal["sentences"] = "sentences"
    sentences: list[SentenceOut]


class ListeningContent(BaseModel):
    kind: Literal["listening"] = "listening"
    transcript: str
    audio_url: str | None
    exercises: list[ExerciseOut]


class ReadingContent(BaseModel):
    kind: Literal["reading"] = "reading"
    text: str
    exercises: list[ExerciseOut]


class WritingContent(BaseModel):
    kind: Literal["writing"] = "writing"
    task: str
    prompt: str
    min_words: int
    max_words: int


class SpeakingContent(BaseModel):
    kind: Literal["speaking"] = "speaking"
    task: str
    prompt: str
    seconds: int


LessonContent = Annotated[
    GrammarContent
    | VocabContent
    | SentencesContent
    | ListeningContent
    | ReadingContent
    | WritingContent
    | SpeakingContent,
    Field(discriminator="kind"),
]


class LessonOut(BaseModel):
    id: str
    module_id: str
    title: str
    done: bool
    content: LessonContent


class ExerciseAnswer(BaseModel):
    index: int = Field(ge=0)
    response: dict[str, Any]


class CheckResultOut(BaseModel):
    correct: bool
    expected: str
    explanation: str | None


class LessonCompleted(BaseModel):
    module: ModuleSummary
    cards_added: int


class CheckItemOut(BaseModel):
    id: str
    skill: str
    exercise: ExerciseOut


class ModuleCheckOut(BaseModel):
    run_id: int
    items: list[CheckItemOut]


class ItemAnswer(BaseModel):
    item_id: str
    response: dict[str, Any]
    time_ms: int | None = None


class CheckSubmission(BaseModel):
    answers: list[ItemAnswer]


class ItemResult(CheckResultOut):
    item_id: str


class CheckOutcome(BaseModel):
    score: float
    passed: bool
    results: list[ItemResult]
    module: ModuleSummary


class ConceptOut(BaseModel):
    id: str
    title: str
    body_md: str


class ReviewCard(BaseModel):
    id: int
    item_type: str
    prompt_en: str
    answer_fr: str
    gender: str | None
    example_fr: str | None
    audio_url: str | None
    due_at: datetime
    reviews: int


class ReviewRating(BaseModel):
    rating: int = Field(ge=1, le=4)


class DrillStart(BaseModel):
    skill: Literal["CO", "CE"]
    count: int = Field(default=10, ge=3, le=39)


class DrillOut(BaseModel):
    run_id: int
    skill: str
    deadline: datetime
    items: list[CheckItemOut]


class SkillLevelOut(BaseModel):
    skill: str
    score: float
    se: float
    cefr: str
    nclc: int | None
    evidence_count: int
    last_at: datetime
    stale: bool


class DrillOutcome(BaseModel):
    score: float
    results: list[ItemResult]
    level: SkillLevelOut | None


class WritingText(BaseModel):
    text: str = Field(max_length=5000)


class FixOut(BaseModel):
    excerpt: str
    correction: str
    explanation: str


class TaggedErrorOut(BaseModel):
    tag: str
    excerpt: str
    correction: str


class WritingResult(BaseModel):
    id: int
    status: Literal["pending", "graded"]
    task: str
    word_count: int
    score: float | None
    criteria: dict[str, float]
    evidence: dict[str, str]
    fixes: list[FixOut]
    errors: list[TaggedErrorOut]
    level: SkillLevelOut | None = None


class WritingDrillOut(BaseModel):
    run_id: int
    task: str
    prompt: str
    min_words: int
    max_words: int
    deadline: datetime


class ErrorFingerprintOut(BaseModel):
    tag: str
    count: int
    example: str
    correction: str


class PlacementOutcome(BaseModel):
    score: float
    placed_level: str
    modules_placed: int
    levels: dict[str, SkillLevelOut | None]


class SearchHit(BaseModel):
    key: str
    kind: str
    title: str
    text: str
    source_ref: str
    cefr: str | None
    personal: bool


class SpeakingTaskOut(BaseModel):
    code: str
    title: str
    prep_seconds: int
    seconds: int


class SpeakingStart(BaseModel):
    task: str


class SpeakingSessionOut(BaseModel):
    run_id: int
    task: SpeakingTaskOut
    prompt: str


class SdpOffer(BaseModel):
    sdp: str = Field(max_length=20000)


class SpeakingCallOut(BaseModel):
    sdp: str
    deadline: datetime


class RealtimeUsage(BaseModel):
    usage: dict[str, Any]


class UsageVerdict(BaseModel):
    stop: bool


class TranscriptLine(BaseModel):
    role: Literal["examiner", "candidate"]
    text: str = Field(max_length=4000)


class SpeakingEnd(BaseModel):
    transcript: list[TranscriptLine] = Field(default_factory=list, max_length=200)
