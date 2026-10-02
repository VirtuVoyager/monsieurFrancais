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
        voice = self.voice
        return (
            f'<speak version="1.0" xml:lang="{voice.locale}">'
            f'<voice name="{voice.name}"><prosody rate="{self.rate:.2f}">'
            f"{escape(self.text.strip())}</prosody></voice></speak>"
        )

    def content_hash(self, engine: str) -> str:
        return hashlib.sha256(f"{engine}\n{self.ssml}".encode()).hexdigest()


def media_path(content_hash: str) -> str:
    return f"catalog/audio/{content_hash[:2]}/{content_hash[2:4]}/{content_hash}.ogg"


def spoken(text: str) -> str:
    """Pairs written with a slash ("le boulanger / la boulangère") are read with a pause."""
    return ", ".join(part.strip() for part in text.split("/") if part.strip())
