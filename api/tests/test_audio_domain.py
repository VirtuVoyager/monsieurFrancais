from app.domain.audio import VOICES, AudioRequest, media_path


def test_voice_is_stable_per_item_and_mixes_accents() -> None:
    requests = [AudioRequest(f"bank/co/item-{i}", "Bonjour.") for i in range(40)]

    assert AudioRequest("bank/co/item-1", "x").voice == requests[1].voice
    assert {r.voice.locale for r in requests} == {"fr-FR", "fr-CA"}
    assert {r.voice for r in requests} == set(VOICES)


def test_ssml_escapes_text_and_sets_pace() -> None:
    ssml = AudioRequest("k", "Tom & Léa <3", rate=0.9).ssml

    assert "Tom &amp; Léa &lt;3" in ssml
    assert 'rate="0.90"' in ssml


def test_hash_changes_with_engine_text_and_pace() -> None:
    base = AudioRequest("k", "Bonjour.")

    assert base.content_hash("azure") == AudioRequest("k", "Bonjour.").content_hash("azure")
    assert base.content_hash("azure") != base.content_hash("fake")
    assert base.content_hash("azure") != AudioRequest("k", "Bonjour !").content_hash("azure")
    assert base.content_hash("azure") != AudioRequest("k", "Bonjour.", 0.9).content_hash("azure")


def test_media_path_shards_by_hash() -> None:
    assert media_path("abcdef") == "catalog/audio/ab/cd/abcdef.ogg"
