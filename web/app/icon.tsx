import { ImageResponse } from "next/og";

export const size = { width: 512, height: 512 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(<Mark fontSize={240} />, size);
}

export function Mark({ fontSize }: { fontSize: number }) {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#161d28",
        color: "#8ea2ff",
        fontSize,
        fontWeight: 700,
        letterSpacing: -4,
      }}
    >
      MF
    </div>
  );
}
