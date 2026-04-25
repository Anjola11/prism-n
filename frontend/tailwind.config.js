/** @type {import('tailwindcss').Config} */
const colorVar = (name) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: ["DM Mono", "monospace"],
        heading: ["Space Grotesk", "sans-serif"],
        body: ["IBM Plex Sans", "sans-serif"],
        code: ["JetBrains Mono", "monospace"],
      },
      colors: {
        void: colorVar("--rgb-void"),
        navy: {
          DEFAULT: colorVar("--rgb-navy"),
          mid: colorVar("--rgb-navy-mid"),
          light: colorVar("--rgb-navy-light"),
        },
        border: {
          DEFAULT: colorVar("--rgb-border"),
          bright: colorVar("--rgb-border-bright"),
        },
        text: {
          primary: colorVar("--rgb-text-primary"),
          secondary: colorVar("--rgb-text-secondary"),
          muted: colorVar("--rgb-text-muted"),
          dim: colorVar("--rgb-text-dim"),
        },
        informed: {
          DEFAULT: colorVar("--rgb-informed"),
          bg: colorVar("--rgb-informed-bg"),
          border: colorVar("--rgb-informed-border"),
        },
        uncertain: {
          DEFAULT: colorVar("--rgb-uncertain"),
          bg: colorVar("--rgb-uncertain-bg"),
          border: colorVar("--rgb-uncertain-border"),
        },
        noise: {
          DEFAULT: colorVar("--rgb-noise"),
          bg: colorVar("--rgb-noise-bg"),
          border: colorVar("--rgb-noise-border"),
        },
        prism: {
          violet: colorVar("--rgb-prism-violet"),
          blue: colorVar("--rgb-prism-blue"),
          cyan: colorVar("--rgb-prism-cyan"),
          teal: colorVar("--rgb-prism-teal"),
          amber: colorVar("--rgb-prism-amber"),
        },
      },
      backgroundImage: {
        spectrum: "var(--g-spectrum)",
        page: "var(--g-page)",
        card: "var(--g-card)",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        modal: "var(--shadow-modal)",
        "glow-informed": "var(--shadow-glow-informed)",
        "glow-uncertain": "var(--shadow-glow-uncertain)",
        "glow-noise": "var(--shadow-glow-noise)",
        "glow-blue": "var(--shadow-glow-blue)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        pulseSlow: {
          "0%,100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
        scanLine: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        spectrumDrift: {
          "0%,100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        float: {
          "0%,100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        shimmer: "shimmer 2s linear infinite",
        "pulse-slow": "pulseSlow 2.8s ease-in-out infinite",
        "scan-line": "scanLine 2.2s linear infinite",
        spectrum: "spectrumDrift 6s ease-in-out infinite",
        float: "float 4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
