from dataclasses import dataclass

MAX_ATTEMPTS = 3
# Azure accuracy is 0-100. Measured on correct French: words score 69-100 and a single sound can
# read 0 next to a liaison (« mon‿enfant »), so neither number alone is trusted. A word needs work
# when Azure itself calls it mispronounced or missing, or when it is below WORD_PASS *and* one of
# its sounds collapses (« utile » with a « eu »: 76 with a sound at 0).
WORD_PASS = 80.0
SOUND_FAIL = 25.0
MISSED = ("Mispronunciation", "Omission")
# Below this share of the sentence recognised, the recording is treated as not heard: scoring it
# would mark every word wrong for what is usually a microphone or recogniser problem.
MIN_COMPLETENESS = 50.0


@dataclass(frozen=True)
class WordScore:
    word: str
    accuracy: float
    error: str | None
    sounds: tuple[float, ...]


@dataclass(frozen=True)
class Assessment:
    recognised: bool
    accuracy: float
    fluency: float
    completeness: float
    words: tuple[WordScore, ...]

    @property
    def heard(self) -> bool:
        return self.recognised and self.completeness >= MIN_COMPLETENESS


def is_weak(word: WordScore) -> bool:
    collapsed = any(s < SOUND_FAIL for s in word.sounds)
    return word.error in MISSED or (word.accuracy < WORD_PASS and collapsed)


def marked(assessment: Assessment) -> list[tuple[WordScore, bool]]:
    """Each word of the reference with whether it needs work; extra words are left out."""
    return [(w, is_weak(w)) for w in assessment.words if w.error != "Insertion"]


def flagged(assessment: Assessment) -> list[WordScore]:
    return [word for word, weak in marked(assessment) if weak]


def passed(assessment: Assessment) -> bool:
    return assessment.heard and not flagged(assessment)


def finished(attempt: int, ok: bool) -> bool:
    return ok or attempt >= MAX_ATTEMPTS


def weak_sounds(word: WordScore) -> list[int]:
    """1-based positions of the weak sounds, for the coach to map onto letters."""
    return [i for i, score in enumerate(word.sounds, start=1) if score < WORD_PASS]
