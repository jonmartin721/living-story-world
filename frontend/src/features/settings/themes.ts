export const themes = [
  {
    id: "literary",
    name: "Warm literary",
    background: "#f4efe5",
    ink: "#302923",
    accent: "#2d4d41",
    scheme: "light",
  },
  {
    id: "sage",
    name: "Charcoal & sage",
    background: "#242624",
    ink: "#e2e1d7",
    accent: "#a8bba0",
    scheme: "dark",
  },
  {
    id: "sepia",
    name: "Sepia & copper",
    background: "#2b211d",
    ink: "#e6d8bd",
    accent: "#c18a6f",
    scheme: "dark",
  },
  {
    id: "rose",
    name: "Aubergine & rose",
    background: "#272229",
    ink: "#e9e1e5",
    accent: "#c6a1ad",
    scheme: "dark",
  },
] as const;

export type Theme = (typeof themes)[number]["id"];
export const themeStorageKey = "storyworld.theme";

export function readTheme(): Theme {
  try {
    const saved = window.localStorage.getItem(themeStorageKey);
    return themes.find((theme) => theme.id === saved)?.id ?? "literary";
  } catch {
    return "literary";
  }
}

export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = themes.find(
    (item) => item.id === theme,
  )!.scheme;
}
