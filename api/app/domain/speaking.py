from collections.abc import Mapping
from typing import Any

from app.domain.cost import Units

# Realtime audio bills about 10 input tokens per second heard and 20 per second spoken.
AUDIO_IN_PER_SECOND = 10
AUDIO_OUT_PER_SECOND = 20
TURN_SECONDS = 15
INSTRUCTION_TOKENS = 1500
REPLY_TEXT_TOKENS = 150
# The browser may overrun the clock slightly before the server hangs up.
GRACE_SECONDS = 60

TITLES = {
    "EO1": "Entretien dirigé",
    "EO2": "Exercice en interaction",
    "EO3": "Expression d'un point de vue",
}

_ROLES = {
    "EO1": (
        "Run a guided interview. Open by greeting the candidate and asking them to introduce "
        "themselves, then ask one short question at a time about what they say."
    ),
    "EO2": (
        "Play the person in the scenario. The candidate must ask you questions to get the "
        "information. Answer only what is asked, briefly, from your private notes; never "
        "volunteer everything. If the candidate is silent, wait. Open with a one-line greeting "
        "in role."
    ),
    "EO3": (
        "Read the statement aloud, then let the candidate argue their view. Only when they "
        "pause, challenge their position with one short counter-argument at a time."
    ),
}


def examiner_instructions(task: str, prompt: str, notes: str | None) -> str:
    lines = [
        "You are a TCF Canada examiner for the expression orale test (task "
        f"{task}, {TITLES[task]}).",
        _ROLES[task],
        "Speak only French, at natural speed, in a neutral standard register. Keep every turn "
        "under 20 seconds: the candidate must do most of the talking.",
        "Never correct, teach, translate, praise or score the candidate during the test, and "
        "never switch to English, even if asked.",
        f"Task shown to the candidate: {prompt.strip()}",
    ]
    if notes:
        lines.append(f"Private notes, never read out: {notes.strip()}")
    return "\n\n".join(lines)


def worst_case_units(seconds: int) -> Units:
    # No-cache upper bound: every turn re-bills the whole conversation so far as input.
    turns = -(-(seconds + GRACE_SECONDS) // TURN_SECONDS)
    audio_per_turn = TURN_SECONDS * (AUDIO_IN_PER_SECOND + AUDIO_OUT_PER_SECOND) / 2
    return {
        "audio_input_tokens": audio_per_turn * turns * (turns + 1) / 2,
        "audio_output_tokens": float(AUDIO_OUT_PER_SECOND * TURN_SECONDS / 2 * turns),
        "text_input_tokens": float(INSTRUCTION_TOKENS * turns),
        "text_output_tokens": float(REPLY_TEXT_TOKENS * turns),
    }


def usage_units(usage: Mapping[str, Any]) -> Units:
    inputs: Mapping[str, Any] = usage.get("input_token_details") or {}
    cached: Mapping[str, Any] = inputs.get("cached_tokens_details") or {}
    outputs: Mapping[str, Any] = usage.get("output_token_details") or {}
    cached_text = float(cached.get("text_tokens") or 0)
    cached_audio = float(cached.get("audio_tokens") or 0)
    units = {
        "text_input_tokens": float(inputs.get("text_tokens") or 0) - cached_text,
        "cached_text_input_tokens": cached_text,
        "audio_input_tokens": float(inputs.get("audio_tokens") or 0) - cached_audio,
        "cached_audio_input_tokens": cached_audio,
        "text_output_tokens": float(outputs.get("text_tokens") or 0),
        "audio_output_tokens": float(outputs.get("audio_tokens") or 0),
    }
    return {name: value for name, value in units.items() if value > 0}
