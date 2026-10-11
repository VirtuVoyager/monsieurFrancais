"use client";

import { useCallback, useRef, useState } from "react";

/** One short microphone take at a time; stops on demand or after `maxSeconds`. */
export function useRecorder(maxSeconds: number) {
  const [recording, setRecording] = useState(false);
  const stopper = useRef<() => void>(() => {});

  const record = useCallback(async (): Promise<Blob> => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true },
    });
    const recorder = new MediaRecorder(stream);
    const chunks: Blob[] = [];
    recorder.ondataavailable = (e) => chunks.push(e.data);
    const stopped = new Promise<Blob>((resolve) => {
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        resolve(new Blob(chunks, { type: recorder.mimeType }));
      };
    });
    const stop = () => recorder.state !== "inactive" && recorder.stop();
    stopper.current = stop;
    const timer = setTimeout(stop, maxSeconds * 1000);
    recorder.start();
    setRecording(true);
    try {
      return await stopped;
    } finally {
      clearTimeout(timer);
      setRecording(false);
    }
  }, [maxSeconds]);

  return { recording, record, stop: () => stopper.current() };
}
