/** Spec/09 §8 palette tokens, mirrored to TS for components that
 * need a colour string (SVG strokes, ReactFlow custom nodes). */
export const C = {
  parchment: "#F4ECD8",
  vellum: "#E8DCC0",
  ink: "#1F1A14",
  inkFaded: "#6B5E48",
  gold: "#A48143",
  verdigris: "#3B5A3C",
  cinnabar: "#7A1F1F",
  blue: "#1F3D4A",
  wash: "#C8BFA5",
} as const;

/** Deterministic two-letter monogram for a pod's display-role or id.
 * Used as the heraldry mark inside Phylacteries and Pod-Cartouches. */
export function monogram(role: string): string {
  const cleaned = role.replace(/^pod-/, "").replace(/[^a-zA-Z0-9]/g, "");
  if (cleaned.length < 2) return cleaned.toUpperCase().padEnd(2, "·");
  // First letter + first letter after any separator-or-vowel
  const parts = role.split(/[-_ ]/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return (cleaned[0] + cleaned[Math.floor(cleaned.length / 2)]).toUpperCase();
}

/** Stable identity colour per pod_id — used as the monogram-fill
 * everywhere that pod is referenced. Derived from the id hash so it
 * survives renames. */
const POD_HUES = [
  "#5b6e3a", // moss
  "#7a4a2b", // ferrous bronze
  "#3d5566", // slate blue
  "#664a73", // muted aubergine
  "#7a5a3a", // sienna
  "#4d6b5e", // sage
  "#7a3a3a", // brick
  "#3a4f7a", // deep blue
];

export function podHue(podId: string): string {
  let h = 0;
  for (let i = 0; i < podId.length; i++) h = (h * 31 + podId.charCodeAt(i)) >>> 0;
  return POD_HUES[h % POD_HUES.length];
}
