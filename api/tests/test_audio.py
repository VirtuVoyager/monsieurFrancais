import csv
import shutil

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import UsageEvent
from app.services import audio
from app.services.users import get_or_create_learner


def _generate(session: Session) -> audio.AudioReport:
    return audio.generate_missing(session, get_or_create_learner(session).id)


def test_every_clip_is_generated_once_and_logged(seeded: Session) -> None:
    first = _generate(seeded)
    second = _generate(seeded)

    expected = len(audio.catalogue_requests(seeded))
    assert (first.generated, second.generated, second.existing) == (expected, 0, expected)
    events = seeded.scalars(select(UsageEvent).where(UsageEvent.feature == "tts_listening")).all()
    assert len(events) == expected
    with get_settings().media_manifest.open() as f:
        hashes = [row["hash"] for row in csv.DictReader(f)]
    assert len(hashes) == len(set(hashes)) >= expected


def _manifest_hashes() -> list[str]:
    with get_settings().media_manifest.open() as f:
        return [row["hash"] for row in csv.DictReader(f)]


def test_a_fresh_checkout_never_lists_a_clip_twice(seeded: Session) -> None:
    _generate(seeded)
    listed = _manifest_hashes()
    # A new machine has the committed manifest but none of the clips, which are not in git.
    shutil.rmtree(get_settings().media_dir / "catalog")

    again = _generate(seeded)

    assert again.generated == len(listed)
    assert _manifest_hashes() == listed


def test_clips_missing_from_the_manifest_are_added_without_paying_again(seeded: Session) -> None:
    _generate(seeded)
    listed = _manifest_hashes()
    get_settings().media_manifest.unlink()

    again = _generate(seeded)

    assert again.generated == 0
    assert sorted(_manifest_hashes()) == sorted(listed)


def test_lessons_and_words_point_to_generated_audio(client: TestClient, seeded: Session) -> None:
    before = client.get("/lessons/a1-01-se-presenter/ecoute").json()["content"]
    _generate(seeded)
    after = client.get("/lessons/a1-01-se-presenter/ecoute").json()["content"]
    word = client.get("/lessons/a1-01-se-presenter/vocabulaire").json()["content"]["words"][0]

    assert before["audio_url"] is None
    assert after["audio_url"].startswith("/media/catalog/audio/")
    assert word["audio_url"].endswith(".ogg")
    served = client.get(after["audio_url"])
    assert served.status_code == 200 and served.content.startswith(b"OggS")


def test_timed_listening_hides_the_script_once_audio_exists(
    client: TestClient, seeded: Session
) -> None:
    _generate(seeded)

    drill = client.post("/drills", json={"skill": "CO", "count": 3}).json()

    exercise = drill["items"][0]["exercise"]
    assert exercise["audio_url"] and exercise["audio_text"] is None


def test_learner_recordings_are_not_publicly_served(client: TestClient) -> None:
    recording = get_settings().media_dir / "users" / "1" / "secret.ogg"
    recording.parent.mkdir(parents=True, exist_ok=True)
    recording.write_bytes(b"OggS")

    assert client.get("/media/users/1/secret.ogg").status_code == 404
