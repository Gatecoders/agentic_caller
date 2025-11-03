export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      minHeight: {
        "screen-minus-5.3rem": "calc(100vh - 5.3rem)",
      },
      fontFamily: {
        body: [
          "Open Sans",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "Noto Sans",
          "sans-serif",
          "Apple Color Emoji",
          "Segoe UI Emoji",
          "Segoe UI Symbol",
          "Noto Color Emoji",
        ],
        sans: [
          "Open Sans",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "Noto Sans",
          "sans-serif",
          "Apple Color Emoji",
          "Segoe UI Emoji",
          "Segoe UI Symbol",
          "Noto Color Emoji",
        ],
        poppins: ["Poppins", "sans-serif"],
        roboto: ["Roboto", "sans-serif"],
      },
      boxShadow: {
        "right-lg": "4px 0 10px rgba(0, 0, 0, 0.1)",
      },
      gridTemplateColumns: {
        "70/30": "70% 30%",
      },
      colors: {
        primary: {
          light: "#3763ae",
          dark: "#305697",
          new: "#4091cc",
          DEFAULT: "#305697",
        },
        customGray: "rgb(110, 111, 119)",
        customBlue: "rgb(249,248,255)",
        customBg: "rgb(241, 245, 249)",
      },
    },
  },
};
