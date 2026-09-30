"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api, unwrap, type Schemas } from "./api/client";

export type CallState = "idle" | "connecting" | "live" | "ended";
export type Line = Schemas["TranscriptLine"];

type ServerEvent = {
  type: string;
  transcript?: string;
  response?: { usage?: Record<string, unknown> };
};

/**
 * A WebRTC call to the examiner. The API exchanges the SDP with Azure, so the browser never
 * holds a key; audio flows directly, and every response's usage is reported for metering.
 */
export function useExaminerCall(runId: number) {
  const [state, setState] = useState<CallState>("idle");
  const [deadline, setDeadline] = useState<string | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const peer = useRef<RTCPeerConnection | null>(null);
  const mic = useRef<MediaStream | null>(null);
  const transcript = useRef<Line[]>([]);
  const ended = useRef(false);

  const release = useCallback(() => {
    peer.current?.close();
    peer.current = null;
    mic.current?.getTracks().forEach((track) => track.stop());
    mic.current = null;
  }, []);

  const end = useCallback(async () => {
    if (ended.current) return;
    ended.current = true;
    release();
    setState("ended");
    await api.POST("/speaking/sessions/{run_id}/end", {
      params: { path: { run_id: runId } },
      body: { transcript: transcript.current },
    });
  }, [release, runId]);

  const onEvent = useCallback(
    async (event: ServerEvent) => {
      if (event.type === "response.output_audio_transcript.done" && event.transcript) {
        transcript.current = [...transcript.current, { role: "examiner", text: event.transcript }];
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
      // The examiner speaks first, as in the exam room.
      channel.onopen = () => channel.send(JSON.stringify({ type: "response.create" }));
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

  return { state, deadline, lines, error, start, end };
}
