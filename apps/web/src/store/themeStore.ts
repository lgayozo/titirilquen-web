import { create } from "zustand";

import { applyTheme, getStoredTheme, storeTheme, type Theme } from "@/lib/theme";

interface ThemeState {
  theme: Theme;
  resolved: "light" | "dark";
  setTheme: (theme: Theme) => void;
  syncSystem: () => void;
}

const initial = getStoredTheme();

export const useThemeStore = create<ThemeState>((set) => ({
  theme: initial,
  resolved: typeof document === "undefined" ? "light" : applyTheme(initial),

  setTheme: (theme) => {
    storeTheme(theme);
    const resolved = applyTheme(theme);
    set({ theme, resolved });
  },

  syncSystem: () => {
    // Se llama cuando el usuario cambia la preferencia del SO y
    // theme === "system".
    set((s) => ({ resolved: applyTheme(s.theme) }));
  },
}));
