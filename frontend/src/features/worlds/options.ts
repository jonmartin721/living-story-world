export const styles = [
  "storybook-ink",
  "watercolor-dream",
  "pixel-rpg",
  "comic-book",
  "noir-sketch",
  "art-nouveau",
  "oil-painting",
  "lowpoly-iso",
];
export const presets = [
  "cozy-adventure",
  "noir-mystery",
  "epic-fantasy",
  "solarpunk-explorer",
  "gothic-horror",
  "space-opera",
  "slice-of-life",
  "cosmic-horror",
  "cyberpunk-noir",
  "whimsical-fairy-tale",
  "post-apocalyptic",
  "historical-intrigue",
];
export const displayName = (value: string) =>
  ({
    "pixel-rpg": "Pixel RPG",
    "lowpoly-iso": "Low-poly isometric",
    "slice-of-life": "Slice of life",
    "whimsical-fairy-tale": "Whimsical fairy tale",
  })[value] ??
  value
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
