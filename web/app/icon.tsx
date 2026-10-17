import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { ImageResponse } from "next/og";

export const size = { width: 512, height: 512 };
export const contentType = "image/png";

export default function Icon() {
  return markPng(size.width);
}

// The logo mark in public/ is the single source; phones and tabs get it as a PNG.
export async function markPng(px: number) {
  const svg = await readFile(join(process.cwd(), "public/mark.svg"), "base64");
  return new ImageResponse(
    // Square and opaque: phones apply their own rounded mask.
    <div style={{ display: "flex", width: "100%", height: "100%", background: "#fbf8ef" }}>
      <img src={`data:image/svg+xml;base64,${svg}`} width={px} height={px} alt="" />
    </div>,
    { width: px, height: px },
  );
}
