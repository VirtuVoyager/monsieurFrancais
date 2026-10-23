import hashlib
from dataclasses import dataclass
from xml.sax.saxutils import escape


@dataclass(frozen=True)
class Voice:
    name: str
    locale: str


# The TCF plays a range of francophone accents; the catalogue mixes France and Québec.
VOICES = (
    Voice("fr-FR-DeniseNeural", "fr-FR"),
    Voice("fr-FR-HenriNeural", "fr-FR"),
    Voice("fr-CA-SylvieNeural", "fr-CA"),
    Voice("fr-CA-AntoineNeural", "fr-CA"),
)
# Dialogues alternate a woman and a man, as in the exam's recordings. The woman always speaks
# first, so a writer can make each line agree with its speaker (« je suis contente »).
DIALOGUE_VOICES = (VOICES[0], VOICES[1])
TURN = "- "
EXAM_RATE = 1.0
PRACTICE_RATE = 0.9


@dataclass(frozen=True)
class AudioRequest:
    key: str
    text: str
    rate: float = EXAM_RATE

    @property
    def voice(self) -> Voice:
        # Stable per item, so regenerating never changes who speaks a given clip.
        digest = hashlib.sha256(self.key.encode()).digest()
        return VOICES[digest[0] % len(VOICES)]

    @property
    def ssml(self) -> str:
        turns = dialogue_turns(self.text)
        if not turns:
            voice = self.voice
            body = self._spoken(voice, self.text)
            return f'<speak version="1.0" xml:lang="{voice.locale}">{body}</speak>'
        voices = [DIALOGUE_VOICES[n % 2] for n in range(len(turns))]
        body = "".join(self._spoken(v, t) for v, t in zip(voices, turns, strict=True))
        return f'<speak version="1.0" xml:lang="{voices[0].locale}">{body}</speak>'

    def _spoken(self, voice: Voice, text: str) -> str:
        return (
            f'<voice name="{voice.name}"><prosody rate="{self.rate:.2f}">'
            f"{escape(text.strip())}</prosody></voice>"
        )

    def content_hash(self, engine: str) -> str:
        return hashlib.sha256(f"{engine}\n{self.ssml}".encode()).hexdigest()


def dialogue_turns(text: str) -> list[str]:
    """The turns of a dialogue written one per line with a leading dash; [] for anything else."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if len(lines) < 2 or not all(line.startswith(TURN) for line in lines):
        return []
    return [line.removeprefix(TURN) for line in lines]


def media_path(content_hash: str) -> str:
    return f"catalog/audio/{content_hash[:2]}/{content_hash[2:4]}/{content_hash}.ogg"


def spoken(text: str) -> str:
    """Pairs written with a slash ("le boulanger / la boulangère") are read with a pause."""
    return ", ".join(part.strip() for part in text.split("/") if part.strip())
