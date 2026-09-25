/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Cool neutral base + surfaces - deliberately not the warm-cream default.
        canvas: "#F7F8FA",
        surface: "#FFFFFF",
        ink: {
          DEFAULT: "#12161C", // primary text / sidebar background
          muted: "#5B6472",
          faint: "#9AA2AF",
        },
        line: "#E4E7EC",
        brand: {
          DEFAULT: "#3452E1",
          hover: "#2A42BE",
          light: "#EAEDFC",
        },
        status: {
          success: "#1A8754",
          "success-bg": "#E9F6EF",
          danger: "#D64545",
          "danger-bg": "#FCEAEA",
          warning: "#D68A1D",
          "warning-bg": "#FBF1DF",
          neutral: "#8B93A1",
          "neutral-bg": "#EEF0F3",
        },
      },
      fontFamily: {
        display: ["Space Grotesk", "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        xl: "12px",
        "2xl": "16px",
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(18 22 28 / 0.04), 0 1px 3px 0 rgb(18 22 28 / 0.06)",
      },
      keyframes: {
        "flash-success": {
          "0%": { backgroundColor: "#E9F6EF" },
          "100%": { backgroundColor: "transparent" },
        },
        "flash-danger": {
          "0%": { backgroundColor: "#FCEAEA" },
          "100%": { backgroundColor: "transparent" },
        },
      },
      animation: {
        "flash-success": "flash-success 1.8s ease-out",
        "flash-danger": "flash-danger 1.8s ease-out",
      },
    },
  },
  plugins: [],
};
