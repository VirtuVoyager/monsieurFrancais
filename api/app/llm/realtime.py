import contextlib
import uuid
from dataclasses import dataclass
from typing import Protocol

import openai

# Short-lived: the server exchanges the SDP offer with it immediately and never hands it out.
SECRET_SECONDS = 30
VOICE = "marin"
MAX_REPLY_TOKENS = 600


@dataclass(frozen=True)
class Call:
    call_id: str
    answer_sdp: str


class Realtime(Protocol):
    model: str

    def connect(self, offer_sdp: str, instructions: str) -> Call: ...

    def hangup(self, call_id: str) -> None: ...


class FakeRealtime:
    model = "fake-realtime"

    def __init__(self) -> None:
        self.hung_up: list[str] = []

    def connect(self, offer_sdp: str, instructions: str) -> Call:
        return Call(f"rtc_fake_{uuid.uuid4().hex}", "v=0\r\ns=fake-examiner\r\n")

    def hangup(self, call_id: str) -> None:
        self.hung_up.append(call_id)


class AzureRealtime:
    def __init__(self, client: openai.OpenAI, deployment: str) -> None:
        self._client = client
        self.model = deployment

    def connect(self, offer_sdp: str, instructions: str) -> Call:
        # Azure only accepts WebRTC offers signed with an ephemeral token, never the API key.
        secret = self._client.realtime.client_secrets.create(
            expires_after={"anchor": "created_at", "seconds": SECRET_SECONDS},
            session={
                "type": "realtime",
                "model": self.model,
                "instructions": instructions,
                "max_output_tokens": MAX_REPLY_TOKENS,
                "audio": {
                    "input": {"turn_detection": {"type": "semantic_vad", "eagerness": "low"}},
                    "output": {"voice": VOICE},
                },
            },
        )
        caller = self._client.with_options(api_key=secret.value)
        response = caller.realtime.calls.with_raw_response.create(sdp=offer_sdp)
        call_id = response.headers["location"].rsplit("/", 1)[-1]
        return Call(call_id, response.http_response.text)

    def hangup(self, call_id: str) -> None:
        # The learner may already have closed it.
        with contextlib.suppress(openai.NotFoundError):
            self._client.realtime.calls.hangup(call_id)
