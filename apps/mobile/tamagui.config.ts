import { createTamagui } from "tamagui";

const config = createTamagui({
  tokens: {
    color: {
      background: "#f6f8fb",
      surface: "#ffffff",
      ink: "#182230",
      muted: "#667085",
      border: "#d0d5dd",
      brand: "#0f766e",
      danger: "#b42318",
      warning: "#b54708",
      success: "#027a48"
    },
    radius: {
      2: 6,
      3: 8
    },
    space: {
      2: 8,
      3: 12,
      4: 16,
      5: 20,
      6: 24
    },
    size: {
      3: 36,
      4: 44,
      5: 52
    },
    zIndex: {
      1: 1
    }
  },
  themes: {
    light: {
      background: "#f6f8fb",
      color: "#182230"
    }
  },
  shorthands: {
    px: "paddingHorizontal",
    py: "paddingVertical",
    bg: "backgroundColor"
  } as const
});

export type AppTamaguiConfig = typeof config;

declare module "tamagui" {
  interface TamaguiCustomConfig extends AppTamaguiConfig {}
}

export default config;
