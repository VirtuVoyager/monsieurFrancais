import { describe, expect, it } from "vitest";

import { encodeWav } from "./wav";

describe("encodeWav", () => {
  it("writes a 16 kHz mono 16-bit PCM header", () => {
    const wav = new DataView(encodeWav(new Float32Array(16_000)).buffer);
    const text = (offset: number) =>
      String.fromCharCode(...[0, 1, 2, 3].map((i) => wav.getUint8(offset + i)));
    expect([text(0), text(8), text(36)]).toEqual(["RIFF", "WAVE", "data"]);
    expect(wav.getUint16(22, true)).toBe(1);
    expect(wav.getUint32(24, true)).toBe(16_000);
    expect(wav.getUint32(40, true)).toBe(32_000);
    expect(wav.byteLength).toBe(44 + 32_000);
  });

  it("clips samples outside -1..1", () => {
    const wav = new DataView(encodeWav(new Float32Array([2, -2, 0])).buffer);
    expect([wav.getInt16(44, true), wav.getInt16(46, true), wav.getInt16(48, true)]).toEqual([
      32767, -32768, 0,
    ]);
  });
});
