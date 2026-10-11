import struct
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.cost import Metered
from app.domain.pronunciation import Assessment, WordScore, finished, flagged, passed
from app.llm.coach import FakeCoach, evidence
from app.llm.grader import ProviderUnavailableError
from app.models import RepeatAttempt, UsageEvent
from app.services import repeat
from app.speech.assessor import FakeAssessor, parse, wav_seconds


def _wav(seconds: float, silent: bool = False) -> bytes:
    rate, samples = 16_000, int(16_000 * seconds)
    header = b"RIFF" + struct.pack("<I", 36 + 2 * samples) + b"WAVEfmt "
    header += struct.pack("<IHHIIHH", 16, 1, 1, rate, 2 * rate, 2, 16)
    header += b"data" + struct.pack("<I", 2 * samples)
    return header + (b"\0\0" if silent else b"\x10\0") * samples


def _assessment(*words: WordScore) -> Assessment:
    return Assessment(True, 80.0, 90.0, 100.0, words)


def _word(word: str, accuracy: float = 96.0, *sounds: float, error: str | None = None) -> WordScore:
    return WordScore(word, accuracy, error, sounds or (96.0, 96.0))


def test_correct_speech_passes_despite_noisy_sound_scores() -> None:
    # Measured on correct speech: a liaison zeroes sounds of a well-scored word, and some words
    # score in the 70s with no sound out of place.
    clean = _assessment(_word("enfant", 97, 0, 6, 0, 87), _word("cours", 69, 69, 69, 69))
    assert passed(clean)


def test_azure_errors_and_low_words_with_a_collapsed_sound_are_flagged() -> None:
    result = _assessment(
        _word("C'est", 52, 100, 1, error="Mispronunciation"),
        _word("utile", 76, 0, 0, 54, 100),
        _word("pour", 0, error="Omission"),
        _word("euh", 0, error="Insertion"),
        _word("ma", 97),
    )
    assert [w.word for w in flagged(result)] == ["C'est", "utile", "pour"]
    assert not passed(result)


def test_a_mostly_missed_sentence_counts_as_not_heard() -> None:
    half = Assessment(True, 40.0, 50.0, 30.0, (_word("La", 0, error="Omission"),))
    assert not half.heard
    assert not passed(half)


def test_three_attempts_then_move_on() -> None:
    assert (finished(1, False), finished(2, True), finished(3, False)) == (False, True, True)


def test_azure_detailed_results_are_parsed() -> None:
    def scored(accuracy: float, error: str = "None") -> dict[str, object]:
        return {"PronunciationAssessment": {"AccuracyScore": accuracy, "ErrorType": error}}

    body = {
        "RecognitionStatus": "Success",
        "Duration": 31_000_000,
        "NBest": [
            {
                "PronunciationAssessment": {
                    "AccuracyScore": 84,
                    "FluencyScore": 82,
                    "CompletenessScore": 83,
                },
                "Words": [
                    {"Word": "C'est", **scored(52, "Mispronunciation"), "Phonemes": [scored(100)]},
                    {"Word": "utile", **scored(76), "Phonemes": [scored(0), scored(54)]},
                ],
            }
        ],
    }

    result = parse(body)

    assert (result.heard, result.accuracy, result.fluency) == (True, 84, 82)
    assert result.words[0] == WordScore("C'est", 52, "Mispronunciation", (100,))
    assert result.words[1] == WordScore("utile", 76, None, (0, 54))
    assert not parse({"RecognitionStatus": "InitialSilenceTimeout"}).heard


def test_wav_length_comes_from_the_header() -> None:
    assert wav_seconds(_wav(2.5)) == 2.5
    assert wav_seconds(b"not a wav") == 0


def test_the_coach_sees_only_the_marked_words_and_where_they_went_wrong() -> None:
    weak = [_word("utile", 76, 0, 0, 54, 100)]
    text = evidence("C'est utile.", "u in utile", weak, 3)
    assert "- utile: 76; weak sounds: 1, 2, 3" in text
    assert "Attempt 3 of 3." in text


def test_sets_are_seeded_with_their_sentences(client: TestClient, seeded: Session) -> None:
    sets = client.get("/repeat/sets").json()
    assert [s["id"] for s in sets] == ["u-ou", "voyelles-nasales", "r-et-liaisons"]
    assert all(s["sentences"] == 10 for s in sets)

    detail = client.get("/repeat/sets/u-ou").json()
    assert detail["max_attempts"] == 3
    assert detail["sentences"][0]["fr"] == "Tu as vu la statue au bout de la rue ?"
    assert client.get("/repeat/sets/nope").status_code == 404


def _first_sentence(client: TestClient) -> str:
    sentence_id: str = client.get("/repeat/sets/u-ou").json()["sentences"][0]["id"]
    return sentence_id


def _post(client: TestClient, sentence_id: str, attempt: int, wav: bytes) -> dict[str, Any]:
    response = client.post(
        f"/repeat/sentences/{sentence_id}/attempts",
        params={"attempt": attempt},
        content=wav,
        headers={"content-type": "audio/wav"},
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def test_a_good_attempt_passes_without_paying_for_a_coach(
    client: TestClient, seeded: Session
) -> None:
    result = _post(client, _first_sentence(client), 1, _wav(3))

    assert (result["status"], result["feedback"]) == ("passed", "")
    assert all(not w["weak"] for w in result["words"])
    features = seeded.scalars(select(UsageEvent.model).where(UsageEvent.feature == "pronunciation"))
    assert list(features) == ["fake-stt"]


class _Mispronounced(FakeAssessor):
    def assess(self, wav: bytes, reference: str) -> Metered[Assessment]:
        words = tuple(
            _word(w, 52, error="Mispronunciation") if w == "rue" else _word(w)
            for w in reference.rstrip(" ?").split()
        )
        return Metered(_assessment(*words), {"audio_seconds": 3.0})


def test_a_weak_word_is_coached_three_times_then_the_learner_moves_on(
    client: TestClient, seeded: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(repeat, "get_assessor", _Mispronounced)
    sentence = _first_sentence(client)

    results = [_post(client, sentence, n, _wav(3)) for n in (1, 2, 3)]

    assert [r["status"] for r in results] == ["retry", "retry", "next"]
    assert "« rue »" in str(results[0]["feedback"])
    assert [w["word"] for w in results[0]["words"] if w["weak"]] == ["rue"]
    saved = seeded.scalars(select(RepeatAttempt).order_by(RepeatAttempt.attempt)).all()
    assert [(a.attempt, a.passed) for a in saved] == [(1, False), (2, False), (3, False)]
    fourth = client.post(
        f"/repeat/sentences/{sentence}/attempts",
        params={"attempt": 4},
        content=_wav(3),
        headers={"content-type": "audio/wav"},
    )
    assert fourth.status_code == 403


class _CoachDown(FakeCoach):
    def coach(self, sentence: str, tip: str, weak: list[WordScore], attempt: int) -> Metered[str]:
        raise ProviderUnavailableError("down")


def test_without_a_coach_the_learner_still_hears_where_to_look(
    client: TestClient, seeded: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(repeat, "get_assessor", _Mispronounced)
    monkeypatch.setattr(repeat, "get_coach", _CoachDown)

    result = _post(client, _first_sentence(client), 1, _wav(3))

    assert result["feedback"] == "Listen to the slow version again and focus on « rue »."


def test_silence_is_not_scored_and_does_not_use_up_an_attempt(
    client: TestClient, seeded: Session
) -> None:
    result = _post(client, _first_sentence(client), 1, _wav(2, silent=True))

    assert result["status"] == "unheard"
    assert seeded.scalars(select(RepeatAttempt)).all() == []


def test_only_wav_recordings_are_accepted(client: TestClient, seeded: Session) -> None:
    response = client.post(
        f"/repeat/sentences/{_first_sentence(client)}/attempts",
        params={"attempt": 1},
        content=b"webm",
        headers={"content-type": "audio/webm"},
    )
    assert response.status_code == 403
