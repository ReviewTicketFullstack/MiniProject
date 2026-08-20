import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          800: "#1F2937",
        },
        ink: {
          900: "#111827",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
