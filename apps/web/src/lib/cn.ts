import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// Sin esto, tailwind-merge toma `text-etiqueta` por un color y, junto a
// `text-muted`, descarta uno de los dos.
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [
        {
          text: [
            "titulo",
            "seccion",
            "dato",
            "figura",
            "cuerpo",
            "ayuda",
            "etiqueta",
          ],
        },
      ],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
