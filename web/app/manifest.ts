import type { MetadataRoute } from "next";

// Lets the phone install the app to the home screen and open it without browser chrome.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Monsieur Français",
    short_name: "Monsieur",
    description: "Exam-first French for TCF Canada",
    start_url: "/",
    display: "standalone",
    background_color: "#fbf8ef",
    theme_color: "#161d28",
    icons: [{ src: "/icon", sizes: "512x512", type: "image/png" }],
  };
}
