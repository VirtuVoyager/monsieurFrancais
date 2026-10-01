"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api, unwrap, type Schemas } from "./api/client";

export type CallState = "idle" | "connecting" | "live" | "grading" | "ended";
export type Line = Schemas["TranscriptLine"];

type ServerEvent = {
  type: string;
  transcript?: string;
  response?: { usage?: Record<string, unknown> };
};

// Opus in WebM (Chrome, Firefox) or MP4 (Safari); the server keeps whichever it receives.
const RECORDING_TYPES = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"];

/**
 * A WebRTC call to the examiner. The API exchanges the SDP with Azure, so the browser never
 * holds a key; audio flows directly, and every response's usage is reported for metering.
 * The learner's microphone is recorded alongside, then transcribed and graded on the server.
 */
export function useExaminerCall(runId: number) {
  const [state, setState] = useState<CallState>("idle");
  const [deadline, setDeadline] = useState<string | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [result, setResult] = useState<Schemas["SpeakingResult"] | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const peer = useRef<RTCPeerConnection | null>(null);
  const mic = useRef<MediaStream | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const startedAt = useRef(0);
  const transcript = useRef<Line[]>([]);
  const ended = useRef(false);

  const release = useCallback(() => {
    peer.current?.close();
    peer.current = null;
    mic.current?.getTracks().forEach((track) => track.stop());
    mic.current = null;
  }, []);

  const stopRecording = useCallback(async (): Promise<Blob | null> => {
    const rec = recorder.current;
    if (!rec || rec.state === "inactive") return null;
    const stopped = new Promise<void>((resolve) => rec.addEventListener("stop", () => resolve()));
    rec.stop();
    await stopped;
    return new Blob(chunks.current, { type: rec.mimeType });
  }, []);

  const end = useCallback(async () => {
    if (ended.current) return;
    ended.current = true;
    const audio = await stopRecording();
    release();
    setState("grading");
    try {
      if (audio && audio.size > 0) {
        const upload = await fetch(`/api/speaking/sessions/${runId}/recording`, {
          method: "POST",
          headers: { "Content-Type": audio.type },
          body: audio,
        });
        if (!upload.ok) throw new Error("Your recording could not be saved.");
      }
      const graded = await unwrap(
        api.POST("/speaking/sessions/{run_id}/end", {
          params: { path: { run_id: runId } },
          body: { transcript: transcript.current },
        }),
      );
      setResult(graded);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    }
    setState("ended");
  }, [release, runId, stopRecording]);

  const onEvent = useCallback(
    async (event: ServerEvent) => {
      if (event.type === "response.output_audio_transcript.done" && event.transcript) {
        const line: Line = {
          role: "examiner",
          text: event.transcript,
          at_ms: Math.max(Math.round(performance.now() - startedAt.current), 0),
        };
        transcript.current = [...transcript.current, line];
        setLines(transcript.current);
      }
      if (event.type === "response.done" && event.response?.usage) {
        const verdict = await unwrap(
          api.POST("/speaking/sessions/{run_id}/usage", {
            params: { path: { run_id: runId } },
            body: { usage: event.response.usage },
          }),
        );
        if (verdict.stop) await end();
      }
    },
    [end, runId],
  );

  const start = useCallback(async () => {
    setState("connecting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mic.current = stream;
      const pc = new RTCPeerConnection();
      peer.current = pc;
      const speaker = new Audio();
      speaker.autoplay = true;
      pc.ontrack = (e) => {
        speaker.srcObject = e.streams[0] ?? null;
      };
      pc.onconnectionstatechange = () => {
        if (pc.connectionState !== "failed") return;
        setError(new Error("Lost the connection to the examiner. Check your network and retry."));
        void end();
      };
      stream.getTracks().forEach((track) => pc.addTrack(track, stream));
      const channel = pc.createDataChannel("oai-events");
      // The examiner speaks first, as in the exam room; the clock for timestamps starts here.
      channel.onopen = () => {
        const mimeType = RECORDING_TYPES.find((type) => MediaRecorder.isTypeSupported(type));
        const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
        chunks.current = [];
        rec.ondataavailable = (e) => chunks.current.push(e.data);
        rec.start(1000);
        recorder.current = rec;
        startedAt.current = performance.now();
        channel.send(JSON.stringify({ type: "response.create" }));
      };
      channel.onmessage = (e: MessageEvent<string>) =>
        void onEvent(JSON.parse(e.data) as ServerEvent);

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      const call = await unwrap(
        api.POST("/speaking/sessions/{run_id}/call", {
          params: { path: { run_id: runId } },
          body: { sdp: offer.sdp ?? "" },
        }),
      );
      await pc.setRemoteDescription({ type: "answer", sdp: call.sdp });
      setDeadline(call.deadline);
      setState("live");
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
      await end();
    }
  }, [end, onEvent, runId]);

  useEffect(() => release, [release]);

  return { state, deadline, lines, result, error, start, end };
}
