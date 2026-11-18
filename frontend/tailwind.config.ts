import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        kkm: {
          navy: "#0f2744",
          blue: "#1d4ed8",
          teal: "#0d9488",
          gold: "#d97706",
        },
      },
    },
  },
  plugins: [],
};
export default config;
