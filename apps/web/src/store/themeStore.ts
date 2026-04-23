import { create } from "zustand";

import {
  applyTheme,
  getStoredTheme,
  storeTheme,
  type ResolvedTheme,
  type Theme,
} from "@/lib/theme";

interface ThemeState {
  theme: Theme;
  resolved: ResolvedTheme;
  setTheme: (theme: Theme) => void;
  syncSystem: () => void;
}

const initial = getStoredTheme();

export const useThemeStore = create<ThemeState>((set) => ({
  theme: initial,
  resolved: typeof document === "undefined" ? "paper" : applyTheme(initial),

  setTheme: (theme) => {
    storeTheme(theme);
    const resolved = applyTheme(theme);
    set({ theme, resolved });
  },

  syncSystem: () => {
    set((s) => ({ resolved: applyTheme(s.theme) }));
  },
}));
