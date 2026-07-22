import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        background: "#0B0B0C",
        card: "#151517",
        border: "#2A2A2E",
        "text-primary": "#FFFFFF",
        "text-muted": "#8A8A90",
        green: "#22C55E",
        red: "#EF4444",
        gold: "#F5B301",
      },
    },
  },
  plugins: [],
};

export default config;
