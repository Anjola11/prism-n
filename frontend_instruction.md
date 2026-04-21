# PRISM — Frontend UI/UX Specification V2

### For AI Agent Implementation — Revised Product Structure

**Stack:** React JSX · Tailwind CSS · TanStack Query · TanStack Router · GSAP · D3 · Three.js  
**Auth:** Email & Password based · OTP for verification · HttpOnly Cookies · No localStorage  
**Product Structure:** Landing → Signup/Login → OTP (Verification) → Discovery → Tracker → Market Analysis  
**Approach:** Modular, mobile-first, component-driven  
**Version:** 2.0 — Clean Product Build

---

## TABLE OF CONTENTS

1. [Dependencies & Installation](#1-dependencies--installation)
2. [Design System & Global Tokens](#2-design-system--global-tokens)
3. [Logo & Brand Identity](#3-logo--brand-identity)
4. [App-Level Loader](#4-app-level-loader)
5. [Button & Inline Loaders](#5-button--inline-loaders)
6. [Project Folder Structure](#6-project-folder-structure)
7. [Routing Architecture](#7-routing-architecture)
8. [Global App Layout Shell](#8-global-app-layout-shell)
9. [Landing Page](#9-landing-page)
10. [Auth Flow — Email → OTP](#10-auth-flow--email--otp)
11. [Discovery Page](#11-discovery-page)
12. [Tracker Page](#12-tracker-page)
13. [Market Analysis Page](#13-market-analysis-page)
14. [Shared Component Library](#14-shared-component-library)
15. [Animation & Motion System](#15-animation--motion-system)
16. [API Integration & Cookie Auth](#16-api-integration--cookie-auth)
17. [Responsive Breakpoints & Mobile Rules](#17-responsive-breakpoints--mobile-rules)
18. [Page Flow & Button Navigation Map](#18-page-flow--button-navigation-map)

---

## 1. DEPENDENCIES & INSTALLATION

Run this in the project root after `npm create vite@latest prism-frontend -- --template react`:

```bash
# Core UI & routing
npm install @tanstack/react-query @tanstack/react-router axios

# Styling
npm install tailwindcss @tailwindcss/vite

# Animation
npm install gsap

# 3D (landing page hero)
npm install three @react-three/fiber @react-three/drei

# Data visualisation (charts inside analysis page)
npm install d3 recharts

# Icons
npm install lucide-react

# Fonts (via fontsource — no Google Fonts CDN dependency)
npm install @fontsource/dm-mono @fontsource/space-grotesk @fontsource/ibm-plex-sans @fontsource/jetbrains-mono

# Utility
npm install clsx tailwind-merge
```

**tailwind.config.js** — initialise after install:

```bash
npx tailwindcss init -p
```

**vite.config.js** — add Tailwind plugin:

```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
});
```

---

## 2. DESIGN SYSTEM & GLOBAL TOKENS

### Philosophy

Prism is a signal intelligence instrument — not a consumer app, not a social feed. The visual language is **precision minimalism with terminal authority**. It borrows the information density and monospaced rigour of a Bloomberg terminal but strips away the clutter, replacing it with deliberate negative space, a controlled dark palette, and a single accent system built entirely around the prism metaphor.

The prism metaphor governs every visual decision. A prism takes white light — mixed, undifferentiated, unclear — and splits it into its true components. Prism the product does the same to market data. This is expressed in the logo (geometric prism emitting a spectrum), in the classification color system (the spectrum resolves into red / amber / green), in the loader animation (light entering and dispersing), and in every gradient accent used across the product.

The product must feel like it was built by someone who understands quantitative finance. Not vibey. Not playful. Authoritative, fast, and precise.

---

### CSS Custom Properties

Place in `src/index.css` inside `:root`. Mirror in `tailwind.config.js`.

```css
:root {
  /* ── BASE SURFACES ─────────────────────────────── */
  --c-void: #04080f; /* page background — near-black deep space      */
  --c-navy: #0a1628; /* primary surface — cards, nav                 */
  --c-navy-mid: #0f2040; /* elevated surface — panels, input backgrounds */
  --c-navy-light: #163058; /* highest surface — hover states, tooltips     */
  --c-border: #1e3a5f; /* default border                               */
  --c-border-bright: #2a4e7a; /* hover / focus border                         */

  /* ── TEXT ──────────────────────────────────────── */
  --c-text-primary: #e8f0fe; /* headings, key data                           */
  --c-text-secondary: #8ba4c0; /* labels, descriptions                         */
  --c-text-muted: #4a6080; /* timestamps, hints, captions                  */
  --c-text-dim: #2a3d55; /* placeholder text inside inputs               */

  /* ── SIGNAL CLASSIFICATION ─────────────────────── */
  --c-informed: #10b981;
  --c-informed-bg: #052e1a;
  --c-informed-border: rgba(16, 185, 129, 0.35);
  --c-informed-glow: rgba(16, 185, 129, 0.2);

  --c-uncertain: #f59e0b;
  --c-uncertain-bg: #291a02;
  --c-uncertain-border: rgba(245, 158, 11, 0.35);
  --c-uncertain-glow: rgba(245, 158, 11, 0.2);

  --c-noise: #ef4444;
  --c-noise-bg: #2a0808;
  --c-noise-border: rgba(239, 68, 68, 0.35);
  --c-noise-glow: rgba(239, 68, 68, 0.2);

  /* ── BRAND SPECTRUM ─────────────────────────────── */
  --c-prism-violet: #7c3aed;
  --c-prism-blue: #2563eb;
  --c-prism-cyan: #06b6d4;
  --c-prism-teal: #10b981;
  --c-prism-amber: #f59e0b;

  /* The spectrum gradient — hero accents, logo underline, active states */
  --g-spectrum: linear-gradient(
    135deg,
    #7c3aed 0%,
    #2563eb 22%,
    #06b6d4 48%,
    #10b981 74%,
    #f59e0b 100%
  );

  /* ── SURFACE GRADIENTS ──────────────────────────── */
  --g-page: linear-gradient(160deg, #0a1628 0%, #04080f 60%);
  --g-card: linear-gradient(135deg, #0f2040 0%, #0a1628 100%);
  --g-nav: linear-gradient(
    180deg,
    rgba(10, 22, 40, 0.98) 0%,
    rgba(10, 22, 40, 0.85) 100%
  );

  /* ── SHADOWS ────────────────────────────────────── */
  --shadow-card: 0 4px 24px rgba(0, 0, 0, 0.45), 0 1px 4px rgba(0, 0, 0, 0.3);
  --shadow-modal: 0 16px 64px rgba(0, 0, 0, 0.6), 0 4px 16px rgba(0, 0, 0, 0.4);
  --shadow-glow-informed: 0 0 24px rgba(16, 185, 129, 0.28);
  --shadow-glow-uncertain: 0 0 24px rgba(245, 158, 11, 0.28);
  --shadow-glow-noise: 0 0 24px rgba(239, 68, 68, 0.28);
  --shadow-glow-blue: 0 0 32px rgba(37, 99, 235, 0.35);

  /* ── RADII ──────────────────────────────────────── */
  --r-sm: 4px;
  --r-md: 8px;
  --r-lg: 12px;
  --r-xl: 16px;
  --r-2xl: 24px;
}
```

---

### Tailwind Config

```js
// tailwind.config.js
const { fontFamily } = require("tailwindcss/defaultTheme");

module.exports = {
  content: ["./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: ["DM Mono", "monospace"],
        heading: ["Space Grotesk", "sans-serif"],
        body: ["IBM Plex Sans", "sans-serif"],
        code: ["JetBrains Mono", "monospace"],
      },
      colors: {
        void: "#04080F",
        navy: {
          DEFAULT: "#0A1628",
          mid: "#0F2040",
          light: "#163058",
        },
        border: {
          DEFAULT: "#1E3A5F",
          bright: "#2A4E7A",
        },
        text: {
          primary: "#E8F0FE",
          secondary: "#8BA4C0",
          muted: "#4A6080",
          dim: "#2A3D55",
        },
        informed: {
          DEFAULT: "#10B981",
          bg: "#052E1A",
          border: "rgba(16,185,129,0.35)",
        },
        uncertain: {
          DEFAULT: "#F59E0B",
          bg: "#291A02",
          border: "rgba(245,158,11,0.35)",
        },
        noise: {
          DEFAULT: "#EF4444",
          bg: "#2A0808",
          border: "rgba(239,68,68,0.35)",
        },
        prism: {
          violet: "#7C3AED",
          blue: "#2563EB",
          cyan: "#06B6D4",
          teal: "#10B981",
          amber: "#F59E0B",
        },
      },
      backgroundImage: {
        spectrum:
          "linear-gradient(135deg,#7C3AED 0%,#2563EB 22%,#06B6D4 48%,#10B981 74%,#F59E0B 100%)",
        page: "linear-gradient(160deg,#0A1628 0%,#04080F 60%)",
        card: "linear-gradient(135deg,#0F2040 0%,#0A1628 100%)",
      },
      boxShadow: {
        card: "0 4px 24px rgba(0,0,0,0.45),0 1px 4px rgba(0,0,0,0.3)",
        modal: "0 16px 64px rgba(0,0,0,0.6),0 4px 16px rgba(0,0,0,0.4)",
        "glow-informed": "0 0 24px rgba(16,185,129,0.28)",
        "glow-uncertain": "0 0 24px rgba(245,158,11,0.28)",
        "glow-noise": "0 0 24px rgba(239,68,68,0.28)",
        "glow-blue": "0 0 32px rgba(37,99,235,0.35)",
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
};
```

---

### Typography System

```
Display font:  DM Mono         — scores, key numbers, data values, wordmark
Heading font:  Space Grotesk   — h1–h3, section titles, card titles
Body font:     IBM Plex Sans   — paragraphs, descriptions, labels, form text
Code font:     JetBrains Mono  — formula display, raw values, developer-facing text
```

**Import in `src/main.jsx`:**

```js
import "@fontsource/dm-mono/400.css";
import "@fontsource/dm-mono/700.css";
import "@fontsource/space-grotesk/400.css";
import "@fontsource/space-grotesk/600.css";
import "@fontsource/space-grotesk/700.css";
import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/jetbrains-mono/400.css";
```

**Type scale rules:**

- All scores and key numbers: `font-mono font-bold`
- All page/section headings: `font-heading`
- All body copy, descriptions, form labels: `font-body`
- All raw data values inline with text (liquidity, volume, probability): `font-mono text-sm`
- All timestamps, helper text, captions: `font-mono text-xs text-text-muted`

---

## 3. LOGO & BRAND IDENTITY

### Concept

The Prism logo is a **precision-engineered geometric triangular prism** viewed from a slight isometric-left angle. It is not an illustration. It is a technical mark — clean enough to feel like it belongs next to a Bloomberg ticker or a quant fund's letterhead.

**The visual logic of the mark:**

- The left edge of the prism receives a **single white beam** — representing raw, undifferentiated market data entering the instrument.
- The right face emits **five diverging colored lines** — the spectrum output, representing the signal components Prism separates: violet, blue, cyan, teal, amber. Each color corresponds to one of the five signal qualities (price movement, liquidity, volume, order depth, AI interpretation).
- The triangular body itself is rendered in dark navy with a subtle glass/translucent feel — it is a tool that transforms inputs, not a black box.

**The wordmark** "PRISM" sits to the right of the icon. It uses `DM Mono`, all-caps, `letter-spacing: 0.18em`. A 1.5px spectrum gradient line runs beneath the wordmark from left to right — not centered, but spanning the exact character width of the text. This is the only decorative element on the wordmark.

---

### SVG Implementation

**File:** `src/components/brand/PrismLogo.jsx`

```jsx
/**
 * PrismLogo
 * Props:
 *   size        {number}  — icon height in px. Default: 32
 *   showWordmark {bool}   — show/hide "PRISM" text. Default: true
 *   className   {string}  — additional classes on the wrapper
 *
 * The icon width is always size * 0.857 (aspect ratio of the equilateral triangle)
 */
export function PrismLogo({ size = 32, showWordmark = true, className = "" }) {
  return (
    <div className={`flex items-center gap-3 select-none ${className}`}>
      {/* ── ICON MARK ─────────────────────────── */}
      <svg
        width={size * 0.857}
        height={size}
        viewBox="0 0 30 35"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          {/* White input beam — fades from bright to dim top-to-bottom */}
          <linearGradient id="lg-beam" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#C8D8F0" stopOpacity="0.5" />
          </linearGradient>

          {/* Triangular face — dark glass fill */}
          <linearGradient id="lg-face" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0F2040" />
            <stop offset="100%" stopColor="#0A1628" />
          </linearGradient>

          {/* Optional: soft inner glow on the face */}
          <radialGradient id="lg-inner" cx="55%" cy="45%" r="50%">
            <stop offset="0%" stopColor="#1E3A5F" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#0A1628" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* ── PRISM BODY ── */}
        {/* Triangular front face: apex top-center, base bottom */}
        <polygon
          points="15,2 28,32 2,32"
          fill="url(#lg-face)"
          stroke="#1E3A5F"
          strokeWidth="0.75"
          strokeLinejoin="round"
        />
        {/* Inner soft highlight */}
        <polygon points="15,2 28,32 2,32" fill="url(#lg-inner)" />

        {/* ── LEFT EDGE — white input beam ── */}
        <line
          x1="15"
          y1="2.5"
          x2="2.5"
          y2="31.5"
          stroke="url(#lg-beam)"
          strokeWidth="2.2"
          strokeLinecap="round"
        />

        {/* ── RIGHT FACE — spectrum output lines ── */}
        {/* Five rays fanning out from apex, each progressively wider angle */}
        {/* They trace the right edge and then fan beyond it */}
        <line
          x1="15"
          y1="2.5"
          x2="28"
          y2="32"
          stroke="#7C3AED"
          strokeWidth="1.4"
          strokeLinecap="round"
          opacity="0.95"
        />
        <line
          x1="15"
          y1="2.5"
          x2="26"
          y2="32"
          stroke="#2563EB"
          strokeWidth="1.3"
          strokeLinecap="round"
          opacity="0.9"
        />
        <line
          x1="15"
          y1="2.5"
          x2="23.5"
          y2="32"
          stroke="#06B6D4"
          strokeWidth="1.3"
          strokeLinecap="round"
          opacity="0.9"
        />
        <line
          x1="15"
          y1="2.5"
          x2="21"
          y2="32"
          stroke="#10B981"
          strokeWidth="1.2"
          strokeLinecap="round"
          opacity="0.85"
        />
        <line
          x1="15"
          y1="2.5"
          x2="18.5"
          y2="32"
          stroke="#F59E0B"
          strokeWidth="1.2"
          strokeLinecap="round"
          opacity="0.8"
        />

        {/* ── BASE LINE ── */}
        <line
          x1="2.5"
          y1="32"
          x2="28"
          y2="32"
          stroke="#1E3A5F"
          strokeWidth="0.75"
          strokeLinecap="round"
        />
      </svg>

      {/* ── WORDMARK ──────────────────────────── */}
      {showWordmark && (
        <div className="flex flex-col gap-[3px]">
          <span
            className="font-mono font-bold text-text-primary tracking-[0.18em] uppercase leading-none"
            style={{ fontSize: `${size * 0.5}px` }}
          >
            PRISM
          </span>
          {/* Spectrum underline — matches text width exactly */}
          <div
            className="h-[1.5px] rounded-full"
            style={{
              background:
                "linear-gradient(90deg,#7C3AED,#2563EB,#06B6D4,#10B981,#F59E0B)",
              width: "100%",
            }}
          />
        </div>
      )}
    </div>
  );
}
```

**Size reference:**
| Context | size prop | showWordmark |
|---|---|---|
| Landing navbar | 28 | true |
| App topbar (desktop) | 26 | true |
| App topbar (mobile) | 22 | true |
| Landing hero | 56 | true |
| Loader animation | 68 | false (wordmark animated separately) |
| Auth card header | 36 | true |
| Favicon (standalone SVG) | — | false |

---

## 4. APP-LEVEL LOADER

### Purpose

Shown on initial app boot — while the session cookie is being validated and the first route resolves. Also shown on the transition from any auth page into the authenticated app (email → OTP → discovery). Duration is always tied to actual data readiness, never a fixed fake timer.

### Visual Concept

Full-screen `#04080F` background. The prism icon is centered. The animation tells the prism story in sequence:

1. **The prism fades in** — icon appears, opacity 0 → 1
2. **The white beam draws in** — left edge stroke animates top-to-bottom via `stroke-dashoffset`
3. **The spectrum fans out** — five colored lines animate out from the apex, staggered by 65ms each, same technique
4. **The wordmark appears letter by letter** — "P R I S M" each letter fades up from `translateY(10px)`, stagger 80ms per letter
5. **The tagline fades in** — "Separating Signal from Noise" appears below in `text-text-muted font-mono text-xs tracking-[0.25em] uppercase`
6. **A scanning line** sweeps once across the bottom of the screen — a thin `2px` horizontal line, spectrum gradient fill, sweeps left to right using CSS `animation: scan-line`
7. **Loader fades out** — entire container opacity 0 over 400ms, then `display:none`, page content fades in

**File:** `src/components/brand/PrismLoader.jsx`

```jsx
import { useEffect, useRef } from "react";
import { gsap } from "gsap";

export function PrismLoader({ onComplete }) {
  const wrapRef = useRef(null);
  const beamRef = useRef(null);
  const raysRef = useRef([]); // array of 5 ray <line> elements
  const lettersRef = useRef([]); // array of 5 letter spans
  const taglineRef = useRef(null);
  const scanRef = useRef(null);

  useEffect(() => {
    // Beam and ray paths are ~31px long — set strokeDasharray equal to length
    const BEAM_LEN = 31;
    const RAY_LEN = 31;

    const tl = gsap.timeline({
      defaults: { ease: "power2.out" },
      onComplete: () => {
        // Fade out entire loader, then call onComplete so router renders page
        gsap.to(wrapRef.current, {
          opacity: 0,
          duration: 0.45,
          delay: 0.25,
          onComplete,
        });
      },
    });

    // Phase 1 — loader fades in
    tl.fromTo(wrapRef.current, { opacity: 0 }, { opacity: 1, duration: 0.3 });

    // Phase 2 — white beam draws in (stroke-dashoffset: BEAM_LEN → 0)
    tl.fromTo(
      beamRef.current,
      { strokeDashoffset: BEAM_LEN },
      { strokeDashoffset: 0, duration: 0.55 },
      "+=0.1",
    );

    // Phase 3 — spectrum rays fan out, staggered
    tl.fromTo(
      raysRef.current,
      { strokeDashoffset: RAY_LEN, opacity: 0 },
      { strokeDashoffset: 0, opacity: 1, duration: 0.45, stagger: 0.065 },
      "-=0.2",
    );

    // Phase 4 — wordmark letters stagger up
    tl.fromTo(
      lettersRef.current,
      { opacity: 0, y: 10 },
      { opacity: 1, y: 0, duration: 0.35, stagger: 0.08 },
      "-=0.1",
    );

    // Phase 5 — tagline fade in
    tl.fromTo(
      taglineRef.current,
      { opacity: 0 },
      { opacity: 1, duration: 0.4 },
      "-=0.05",
    );

    // Phase 6 — scan line fires once (CSS animation handles the sweep)
    tl.fromTo(
      scanRef.current,
      { opacity: 0 },
      { opacity: 1, duration: 0.1 },
      "-=0.3",
    );

    return () => tl.kill();
  }, []);

  const LETTERS = ["P", "R", "I", "S", "M"];
  const RAYS = [
    { x2: 28, color: "#7C3AED" },
    { x2: 26, color: "#2563EB" },
    { x2: 23.5, color: "#06B6D4" },
    { x2: 21, color: "#10B981" },
    { x2: 18.5, color: "#F59E0B" },
  ];
  const BEAM_LEN = 31;
  const RAY_LEN = 31;

  return (
    <div
      ref={wrapRef}
      className="fixed inset-0 z-[9999] flex flex-col items-center justify-center gap-8"
      style={{ background: "#04080F", opacity: 0 }}
      aria-label="Loading Prism"
      role="status"
    >
      {/* ── PRISM ICON (enlarged for loader) ── */}
      <svg width="78" height="91" viewBox="0 0 30 35" fill="none">
        <defs>
          <linearGradient id="ll-beam" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#C8D8F0" stopOpacity="0.5" />
          </linearGradient>
          <linearGradient id="ll-face" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0F2040" />
            <stop offset="100%" stopColor="#0A1628" />
          </linearGradient>
        </defs>

        {/* Body */}
        <polygon
          points="15,2 28,32 2,32"
          fill="url(#ll-face)"
          stroke="#1E3A5F"
          strokeWidth="0.75"
        />

        {/* Animated beam */}
        <line
          ref={beamRef}
          x1="15"
          y1="2.5"
          x2="2.5"
          y2="31.5"
          stroke="url(#ll-beam)"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeDasharray={BEAM_LEN}
          strokeDashoffset={BEAM_LEN}
        />

        {/* Animated spectrum rays */}
        {RAYS.map((ray, i) => (
          <line
            key={i}
            ref={(el) => (raysRef.current[i] = el)}
            x1="15"
            y1="2.5"
            x2={ray.x2}
            y2="32"
            stroke={ray.color}
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeDasharray={RAY_LEN}
            strokeDashoffset={RAY_LEN}
            opacity={0}
          />
        ))}

        {/* Base */}
        <line
          x1="2.5"
          y1="32"
          x2="28"
          y2="32"
          stroke="#1E3A5F"
          strokeWidth="0.75"
        />
      </svg>

      {/* ── WORDMARK LETTERS ── */}
      <div className="flex items-end gap-[3px]" aria-label="PRISM">
        {LETTERS.map((l, i) => (
          <span
            key={i}
            ref={(el) => (lettersRef.current[i] = el)}
            className="font-mono font-bold text-text-primary"
            style={{ fontSize: "2.75rem", letterSpacing: "0.1em", opacity: 0 }}
          >
            {l}
          </span>
        ))}
      </div>

      {/* ── TAGLINE ── */}
      <p
        ref={taglineRef}
        className="font-mono text-xs text-text-muted tracking-[0.28em] uppercase"
        style={{ opacity: 0 }}
      >
        Separating Signal from Noise
      </p>

      {/* ── SCANNING LINE ── */}
      <div
        ref={scanRef}
        className="absolute bottom-0 left-0 w-full overflow-hidden"
        style={{ height: "2px", opacity: 0 }}
      >
        <div
          className="h-full w-1/3 animate-scan-line"
          style={{
            background:
              "linear-gradient(90deg,transparent,#2563EB,#06B6D4,transparent)",
          }}
        />
      </div>
    </div>
  );
}
```

**When the loader shows:**

- Initial app boot while `useAuth()` is resolving (`isLoading === true`)
- After OTP verification succeeds — plays while session cookie is being set and route redirects to `/discover`
- NOT on navigation between authenticated pages — use skeleton states there instead

---

## 5. BUTTON & INLINE LOADERS

Every button in the app has exactly one loading state. There are no disabled grey buttons without visual feedback. When an async action is in progress, the button shows a spinner and changes its label. The button width is locked at the pre-click width (use `min-w` calculated from the text) to prevent layout shift.

### Spinner Component

**File:** `src/components/ui/Spinner.jsx`

```jsx
/**
 * Spinner
 * A thin circular arc that rotates. Uses SVG + CSS rotation (no GSAP needed).
 * Props:
 *   size  {number} — diameter in px. Default: 16
 *   color {string} — stroke color. Default: 'currentColor'
 */
export function Spinner({ size = 16, color = "currentColor" }) {
  const r = (size - 2) / 2; // radius leaves 1px gap each side
  const circ = 2 * Math.PI * r; // full circumference

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="animate-spin"
      style={{ animationDuration: "0.75s", animationTimingFunction: "linear" }}
      aria-hidden="true"
    >
      {/* Track */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        opacity="0.2"
      />
      {/* Arc — 25% of circumference */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeDasharray={`${circ * 0.25} ${circ * 0.75}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
    </svg>
  );
}
```

### Button Component

**File:** `src/components/ui/Button.jsx`

```jsx
import { Spinner } from "./Spinner";
import { clsx } from "clsx";

/**
 * Button
 * Props:
 *   variant   {'primary'|'ghost'|'danger'|'outline'|'spectrum'}
 *   size      {'sm'|'md'|'lg'}
 *   loading   {bool}   — shows spinner, locks width, disables interaction
 *   disabled  {bool}
 *   icon      {ReactNode} — Lucide icon component
 *   iconPos   {'left'|'right'} — default 'left'
 *   loadingText {string} — optional label during loading (e.g. "Sending…")
 *   onClick, children, className, type
 */
export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  icon,
  iconPos = "left",
  loadingText,
  onClick,
  children,
  className = "",
  type = "button",
}) {
  const base = [
    "relative inline-flex items-center justify-center gap-2",
    "font-body font-medium rounded-lg",
    "transition-all duration-200",
    "focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-navy",
    "select-none",
  ];

  const variants = {
    primary: [
      "bg-prism-blue text-white",
      "hover:bg-blue-500 focus-visible:ring-prism-blue",
      "active:scale-[0.98]",
      "disabled:opacity-50 disabled:cursor-not-allowed",
      "shadow-glow-blue/0 hover:shadow-glow-blue",
    ],
    ghost: [
      "bg-transparent text-text-secondary",
      "border border-border",
      "hover:border-border-bright hover:text-text-primary",
      "focus-visible:ring-border-bright",
      "active:scale-[0.98]",
    ],
    danger: [
      "bg-noise text-white",
      "hover:bg-red-600 focus-visible:ring-noise",
      "active:scale-[0.98]",
    ],
    outline: [
      "bg-transparent text-prism-blue",
      "border border-prism-blue/50",
      "hover:bg-prism-blue/10 hover:border-prism-blue",
      "focus-visible:ring-prism-blue",
    ],
    spectrum: [
      "text-white font-semibold",
      "bg-spectrum bg-[length:200%_200%] animate-spectrum",
      "hover:opacity-90 focus-visible:ring-prism-cyan",
      "active:scale-[0.98]",
    ],
  };

  const sizes = {
    sm: "px-3 py-1.5 text-xs min-h-[32px]",
    md: "px-4 py-2.5 text-sm min-h-[40px]",
    lg: "px-6 py-3 text-base min-h-[48px]",
  };

  const isDisabled = disabled || loading;

  return (
    <button
      type={type}
      onClick={!isDisabled ? onClick : undefined}
      disabled={isDisabled}
      aria-disabled={isDisabled}
      aria-busy={loading}
      className={clsx(base, variants[variant], sizes[size], className)}
    >
      {/* Loading state: spinner left + optional loadingText */}
      {loading ? (
        <>
          <Spinner
            size={size === "sm" ? 13 : size === "lg" ? 18 : 15}
            color="currentColor"
          />
          {loadingText && <span>{loadingText}</span>}
          {!loadingText && children}
        </>
      ) : (
        <>
          {icon && iconPos === "left" && (
            <span className="flex-shrink-0">{icon}</span>
          )}
          {children}
          {icon && iconPos === "right" && (
            <span className="flex-shrink-0">{icon}</span>
          )}
        </>
      )}
    </button>
  );
}
```

**Loading state examples across the app:**
| Button | Default label | Loading label | Spinner size |
|---|---|---|---|
| "Send OTP" | "Send OTP" | "Sending…" | 15px |
| "Verify Code" | "Verify Code" | "Verifying…" | 15px |
| "+ Track Market" | "+ Track Market" | "Adding…" | 15px |
| "Remove" | "Remove" | spinner only (no text) | 13px |
| Search submit | icon only | spinner (replaces icon) | 15px |

---

## 6. PROJECT FOLDER STRUCTURE

```
prism-frontend/
├── public/
│   └── favicon.svg                ← standalone prism triangle SVG, no wordmark
├── index.html
├── vite.config.js
├── tailwind.config.js
└── src/
    ├── main.jsx                   ← fonts, QueryClient, RouterProvider, global CSS
    ├── App.jsx                    ← root provider tree
    ├── router.jsx                 ← TanStack Router route tree + guards
    │
    ├── lib/
    │   ├── api.js                 ← Axios instance (withCredentials: true)
    │   ├── utils.js               ← cn(), formatScore(), formatNGN(), formatDelta(), timeAgo()
    │   └── constants.js           ← route paths, signal thresholds, source labels
    │
    ├── hooks/
    │   ├── useAuth.js             ← session state from cookie, login(), logout()
    │   ├── useMarkets.js          ← GET /markets?tab=trending|popular (Discovery)
    │   ├── useMarketSearch.js     ← GET /markets?q= (keyword search)
    │   ├── useTrackedMarkets.js   ← GET /tracker (user's tracked list)
    │   ├── useTrackMutation.js    ← POST /tracker/:marketId + DELETE /tracker/:marketId
    │   └── useMarketAnalysis.js   ← GET /markets/:id/analysis (full analysis page)
    │
    ├── components/
    │   ├── brand/
    │   │   ├── PrismLogo.jsx
    │   │   └── PrismLoader.jsx
    │   │
    │   ├── layout/
    │   │   ├── AppLayout.jsx      ← topbar + page slot, wraps Discovery + Tracker
    │   │   ├── Topbar.jsx
    │   │   └── MobileNav.jsx      ← bottom nav bar for mobile
    │   │
    │   ├── ui/
    │   │   ├── Button.jsx
    │   │   ├── Spinner.jsx
    │   │   ├── Input.jsx
    │   │   ├── OTPInput.jsx
    │   │   ├── ScoreBadge.jsx
    │   │   ├── ClassificationChip.jsx
    │   │   ├── DirectionArrow.jsx ← ⬆ ⬇ → with color
    │   │   ├── SourceBadge.jsx    ← "Polymarket" / "Bayse" pill
    │   │   ├── MarketCard.jsx     ← used on Discovery page
    │   │   ├── TrackerCard.jsx    ← used on Tracker page
    │   │   ├── LivePulse.jsx      ← "● LIVE Updated Xs ago"
    │   │   ├── StatTile.jsx
    │   │   ├── Skeleton.jsx
    │   │   ├── EmptyState.jsx
    │   │   ├── ErrorState.jsx
    │   │   ├── Toast.jsx          ← success/error toast notifications
    │   │   └── Tooltip.jsx
    │   │
    │   ├── charts/
    │   │   ├── ProbabilityLine.jsx   ← D3 line chart (probability over time)
    │   │   ├── ScoreGauge.jsx        ← D3 arc gauge for signal score
    │   │   ├── FactorBars.jsx        ← factor contribution bar chart
    │   │   └── VolumeSpike.jsx       ← volume history bar chart
    │   │
    │   └── landing/
    │       ├── LandingNav.jsx
    │       ├── HeroScene.jsx         ← Three.js / R3F 3D prism scene
    │       ├── SignalFeedPreview.jsx  ← animated mock of tracker cards
    │       ├── HowItWorksFlow.jsx    ← animated step diagram
    │       └── ScoringDemoWidget.jsx ← interactive formula sliders
    │
    └── pages/
        ├── LandingPage.jsx
        ├── auth/
        │   ├── EmailPage.jsx         ← step 1: enter email
        │   └── OTPPage.jsx           ← step 2: enter OTP
        └── app/
            ├── DiscoveryPage.jsx
            ├── TrackerPage.jsx
            └── MarketAnalysisPage.jsx
```

---

## 7. ROUTING ARCHITECTURE

**File:** `src/router.jsx`

```js
import {
  createRouter,
  createRoute,
  createRootRoute,
} from "@tanstack/react-router";

// Root — wraps everything, handles session check + loader
const rootRoute = createRootRoute({ component: RootLayout });

// ── PUBLIC ROUTES ──
const landingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: LandingPage,
});

// Signup Flow
const signupRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/auth/signup",
  component: SignupPage,
});

// Login Flow
const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/auth/login",
  component: LoginPage,
});

// OTP Verification (Required after signup or for password reset)
const otpRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/auth/otp",
  component: OTPPage,
});

// Password Recovery
const forgotPasswordRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/auth/forgot-password",
  component: ForgotPasswordPage,
});

const resetPasswordRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/auth/reset-password",
  component: ResetPasswordPage,
});

// ── PROTECTED ROUTES (require valid session cookie) ──
// AppLayout wraps all authenticated pages
const appRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app",
  component: AppLayout,
});
const discoverRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/",
  component: DiscoveryPage,
});
const trackerRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/tracker",
  component: TrackerPage,
});
const analysisRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/markets/$marketId",
  component: MarketAnalysisPage,
});
```

**Route Guards:**

- In `AppLayout.jsx`: call `useAuth()`. While `isLoading`, render the `<PrismLoader />` inline. If `!isAuthenticated`, call `router.navigate({ to: '/auth/login' })`. If authenticated, render children.
- Public routes (`/`, `/auth/signup`, `/auth/login`, `/auth/otp`): if user IS authenticated, redirect to `/app`.

**OTP route state:** The user identifier (`uid`) and `email` are passed to OTPPage via TanStack Router's search params: `/auth/otp?email=user@example.com&uid=xyz&type=signup`. Never via localStorage.

```js
// SignupPage — on submit success:
router.navigate({ to: "/auth/otp", search: { email: emailValue, uid: response.data.uid, type: 'signup' } });

// OTPPage — reading it:
const { email, uid, type } = Route.useSearch();
```

---

## 8. GLOBAL APP LAYOUT SHELL

### AppLayout.jsx

Wraps all three authenticated pages (Discovery, Tracker, Analysis). Contains the topbar and the mobile bottom nav. Does not contain a sidebar — the nav is handled differently for desktop (topbar links) and mobile (bottom tab bar).

**Desktop Layout (≥768px):**

```
┌───────────────────────────────────────────────────────────┐
│ TOPBAR  h-14  sticky top-0 z-50                           │
│ [PrismLogo]     [Discover] [Tracker]      [LivePulse] [⊙] │
├───────────────────────────────────────────────────────────┤
│                                                            │
│  PAGE CONTENT AREA                                         │
│  max-w-6xl mx-auto px-6 py-6                              │
│  (scrollable)                                              │
│                                                            │
└───────────────────────────────────────────────────────────┘
```

**Mobile Layout (<768px):**

```
┌────────────────────────────────┐
│ TOPBAR  h-14  sticky           │
│ [PrismLogo]             [⊙]   │
├────────────────────────────────┤
│  PAGE CONTENT                  │
│  px-4 py-4  full-width         │
│                                │
├────────────────────────────────┤
│ BOTTOM NAV  h-16  fixed bottom │
│  [🔍 Discover]  [📋 Tracker]   │
└────────────────────────────────┘
```

---

### Topbar.jsx

**Styling:**

- `bg-navy/95 backdrop-blur-md border-b border-border`
- `sticky top-0 z-50 h-14`
- `px-6 flex items-center justify-between gap-6`

**Left section:**

- `<PrismLogo size={26} />` — clicking navigates to `/app`

**Center section (desktop only, hidden on mobile):**

- Two nav links: "Discover" and "Tracker"
- Each: `font-body text-sm text-text-secondary hover:text-text-primary transition-colors px-2 py-1`
- Active route: `text-text-primary` + a `2px` underline using the spectrum gradient, `absolute bottom-0 left-0 right-0` (position relative on parent)
- Active underline animates position with GSAP when tab switches: `gsap.to(underline, { x: newX, width: newWidth, duration: 0.25, ease: 'power2.out' })`

**Right section:**

- `<LivePulse />` — visible on desktop only
- User avatar circle: `w-8 h-8 rounded-full bg-prism-blue/20 border border-prism-blue/40 flex items-center justify-center`
  - Shows user initials in `font-mono text-xs text-prism-cyan`
  - Clicking opens a tiny dropdown:
    - `bg-navy-mid border border-border rounded-xl p-2 shadow-modal absolute top-full right-0 mt-2 w-40`
    - Single item: "Sign Out" — `text-text-secondary text-sm font-body hover:text-noise flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-noise-bg transition-colors`
    - Clicking calls `logout()` mutation → redirect to `/`
  - Dropdown animates in: `gsap.fromTo(dropdown, {opacity:0, y:-8, scale:0.96}, {opacity:1, y:0, scale:1, duration:0.18, ease:'power2.out'})`
  - Dropdown closes on outside click via `useEffect` with `mousedown` listener

---

### MobileNav.jsx

**Styling:**

- `fixed bottom-0 left-0 right-0 h-16 z-50`
- `bg-navy/95 backdrop-blur-md border-t border-border`
- `flex items-center`

**Two equal-width tab buttons:**

```
[🔍 icon]     [📋 icon]
Discover      Tracker
```

Each button:

- `flex-1 flex flex-col items-center justify-center gap-1 h-full`
- Icon: Lucide `Search` (Discover) / `BookMarked` (Tracker), size 20
- Label: `font-body text-xs`
- Inactive: `text-text-muted`
- Active: `text-prism-blue`
- Active indicator: `2px` wide, `24px` long bar above the button, `bg-spectrum rounded-full`, positioned `top-0`
- GSAP: indicator slides horizontally to active tab on route change, `duration: 0.25, ease: power2.out`
- Minimum touch target: entire `flex-1` area (guaranteed ≥44px × 64px)

---

## 9. LANDING PAGE

**File:** `src/pages/LandingPage.jsx`
**Route:** `/`
**Layout:** No AppLayout — standalone page

---

### Section 1 — Landing Navbar

**File:** `src/components/landing/LandingNav.jsx`

**Positioning:** `fixed top-0 left-0 right-0 z-50`

**Initial state:** `background: transparent`

**On scroll past 72px:** Transitions to `bg-navy/92 backdrop-blur-lg border-b border-border` via a `scroll` event listener. The transition uses CSS `transition: background 0.3s ease, border-color 0.3s ease` on the element — not GSAP (CSS is sufficient here).

**Height:** `h-16`

**Padding:** `px-6 md:px-12 lg:px-20`

**Structure — `flex items-center justify-between`:**

Left: `<PrismLogo size={28} />`

Center (desktop only — `hidden md:flex items-center gap-8`):

- "How It Works" — anchor `href="#how-it-works"`, smooth scroll
- "Signal Scoring" — anchor `href="#scoring"`
- "Performance" — anchor `href="#performance"`

All nav links: `font-body text-sm text-text-secondary hover:text-text-primary transition-colors duration-150`

Right:

- "Sign In" — ghost button, size sm, `onClick → router.navigate('/auth')`
- "Get Access" — primary button, size sm, `onClick → router.navigate('/auth')`

Mobile: center nav links hidden. Right shows only "Get Access" (primary button, size sm). No hamburger needed — the two CTAs reduce to a single "Get Access" button on mobile if space is tight (`hidden sm:block` on Sign In).

---

### Section 2 — Hero

The hero section is the most complex element in the product. It must immediately communicate the prism concept: chaos enters, clarity exits.

**Min-height:** `100vh`
**Background:** `#04080F`
**Position:** `relative overflow-hidden`

---

#### 2a — Three.js Scene (HeroScene.jsx)

**File:** `src/components/landing/HeroScene.jsx`

This component fills the entire hero section as an `absolute inset-0` canvas behind the text content. It uses `@react-three/fiber` and `@react-three/drei` for React integration.

**Scene composition:**

**Camera:**

- Position: `[0, 0.5, 6]`
- FOV: 50
- Slight downward angle looking at origin

**The Prism Mesh:**

- Geometry: Custom `THREE.BufferGeometry` — a triangular prism (two triangular faces + three rectangular lateral faces). Vertices: apex at top `[0, 2, 0]`, base-left `[-1.5, -1, 0.6]`, base-right `[1.5, -1, 0.6]`, and the three mirrored points at `z = -0.6`.
- Material: `THREE.MeshPhysicalMaterial` with:
  - `color: '#0F2040'`
  - `transmission: 0.85` (glass-like transparency)
  - `roughness: 0.05`
  - `metalness: 0.1`
  - `ior: 1.52` (glass refractive index)
  - `transparent: true`
  - `opacity: 0.92`
  - `side: THREE.DoubleSide`
- Auto-rotation: `mesh.rotation.y += 0.0012` per frame in `useFrame`

**Input Beam:**

- A thin `THREE.CylinderGeometry` (radiusTop: 0.015, radiusBottom: 0.015, height: 2.5)
- Positioned to the left of the prism, slightly angled to intersect the left face
- Material: `THREE.MeshBasicMaterial({ color: '#FFFFFF', transparent: true, opacity: 0.75 })`
- Emissive: `#FFFFFF` at intensity 0.5

**Output Spectrum Rays (5 rays):**

- Same cylinder geometry, height 2.2 each
- Colors: `['#7C3AED','#2563EB','#06B6D4','#10B981','#F59E0B']`
- Positioned emerging from the right face of the prism, each angled outward at increasing Y rotation (fan pattern, 8° spread between each)
- Material: `THREE.MeshBasicMaterial` with `color` + `transparent: true`, `opacity: 0.8`
- Each ray has a slight `animate-float` offset applied via `useFrame` — `ray.position.y = Math.sin(clock.elapsedTime * 0.6 + index * 0.4) * 0.04`

**Background Particles:**

- 180 particles: `THREE.SphereGeometry(0.012, 4, 4)` instances scattered in `radius: 10` sphere
- Material: `THREE.MeshBasicMaterial({ color: '#1E3A5F', transparent: true, opacity: 0.6 })`
- Each particle drifts using `useFrame`: `particle.position.y += Math.sin(clock.elapsedTime + i) * 0.0004`
- Use `THREE.InstancedMesh` for performance

**Lighting:**

- `<ambientLight intensity={0.4} />`
- `<directionalLight position={[4, 6, 3]} intensity={2.2} color="#FFFFFF" />`
- `<pointLight position={[0, 0, 2]} intensity={1.8} color="#2563EB" />`
- `<pointLight position={[-3, 0, 1]} intensity={1.0} color="#7C3AED" />`

**Mouse parallax:**

- `useEffect` on `mousemove` → move camera `x` and `y` by `(mouseX - 0.5) * 0.4` and `(mouseY - 0.5) * -0.2`
- Smoothed with `gsap.to(camera.position, { x: targetX, y: targetY, duration: 1.4, ease: 'power2.out' })`

**Mobile optimization:**

- Detect `window.innerWidth < 768` before mounting
- On mobile: reduce particle count to 60, disable mouse parallax, set `pixelRatio: 1` on renderer
- Or: on mobile, replace Three.js scene entirely with a static SVG background of the prism icon at large scale with a soft radial glow — saves mobile battery

**Canvas configuration:**

```jsx
<Canvas
  camera={{ position: [0, 0.5, 6], fov: 50 }}
  dpr={[1, 1.5]} // max 1.5x pixel ratio for performance
  style={{ position: "absolute", inset: 0 }}
  gl={{ antialias: true, alpha: true }}
>
  <HeroScene />
</Canvas>
```

---

#### 2b — Hero Text Content

**Position:** `relative z-10` — floats above the canvas
**Layout desktop:** Left-aligned, `max-w-[580px]`, `pl-6 md:pl-12 lg:pl-20`, `pt-40`
**Layout mobile:** Centered, `px-6 pt-32 pb-20 text-center`

All text elements are GSAP-animated on mount (after loader exits). Timeline starts with 0.3s delay to let the Three.js scene settle.

**Element 1 — Eyebrow chip:**

```
Text:    "Real-Time Signal Intelligence"
Style:   border border-prism-blue/40 bg-prism-blue/8 text-prism-cyan
         rounded-full px-3 py-1 font-mono text-xs tracking-[0.2em] uppercase
         inline-flex items-center gap-2
         A small animated dot before text: w-1.5 h-1.5 rounded-full bg-prism-cyan animate-pulse-slow
GSAP:    fromTo { opacity:0, y:14 } → { opacity:1, y:0, duration:0.5, ease:'power3.out' }
Delay:   0.3s after mount
```

**Element 2 — H1 Headline (two lines):**

```
Line 1:  "Filter the Noise."
Style:   font-heading font-bold text-text-primary
         font-size: clamp(2.8rem, 5vw, 4.5rem)
         line-height: 1.05
         letter-spacing: -0.025em

Line 2:  "Trade the Signal."
Style:   Same font settings.
         Text is a spectrum gradient:
           background: var(--g-spectrum)
           -webkit-background-clip: text
           -webkit-text-fill-color: transparent
           background-clip: text
           background-size: 200% 200%
           animation: spectrumDrift 6s ease-in-out infinite

GSAP:    Each line: fromTo { opacity:0, y:20 } → { opacity:1, y:0, duration:0.6, ease:'power3.out' }
Stagger: 0.15s between Line 1 and Line 2
Delay:   0.5s
```

**Element 3 — Subheadline:**

```
Text:    "Prism applies institutional-grade market microstructure analysis to prediction
          markets — quantifying whether a price movement is driven by informed traders
          or just noise."
Style:   font-body text-text-secondary
         font-size: clamp(0.9rem, 1.5vw, 1.0625rem)
         line-height: 1.7
         max-w: 460px (desktop), 100% (mobile)
GSAP:    fromTo { opacity:0 } → { opacity:1, duration:0.6 }
Delay:   0.85s
```

**Element 4 — CTA Buttons:**

```
Flex row (desktop), flex col (mobile), gap-3, mt-8

Button A: "Start Analyzing Markets"
  variant: primary, size: lg
  onClick → router.navigate('/auth')
  On hover: box-shadow transitions to shadow-glow-blue

Button B: "See How It Works"
  variant: ghost, size: lg
  icon: ChevronDown (Lucide), iconPos: right
  onClick → smooth scroll to #how-it-works
    gsap.to(window, { scrollTo: '#how-it-works', duration: 0.8, ease: 'power2.inOut' })
    (install gsap ScrollToPlugin for this)

GSAP:    fromTo { opacity:0, y:16 } → { opacity:1, y:0, duration:0.5 }
Delay:   1.05s
Both buttons animate together (no stagger)
```

**Element 5 — Source credibility line:**

```
Text:    "Live data from Polymarket · Bayse · Powered by Google Gemini AI"
Style:   font-mono text-xs text-text-muted tracking-wide mt-5
         Each source separated by " · "
GSAP:    fromTo { opacity:0 } → { opacity:1, duration:0.6 }
Delay:   1.3s
```

---

#### 2c — Floating Market Card Preview

**Desktop only (`hidden xl:block`):** Positioned `absolute right-[6%] top-1/2 -translate-y-1/2`, width `340px`.

Shows 2 stacked `TrackerCard` components (the actual component, with static mock data). These represent what the user will see inside the app.

```
Card 1 (top, z-10):
  rotate-[-1.5deg]
  Market: "Will Tinubu win re-election?"
  Score: 84 — INFORMED MOVE
  Source: Bayse
  Direction: ⬆ Rising (+7 pts)
  Shadow: shadow-glow-informed

Card 2 (behind, z-0):
  rotate-[2deg] translate-y-3 translate-x-4 scale-[0.96] opacity-80
  Market: "BTC above $100k by Dec 2025?"
  Score: 31 — NOISE
  Source: Polymarket
  Direction: ↓ Falling

"LIVE" floating chip above Card 1:
  "● LIVE" — font-mono text-xs text-noise bg-noise-bg border border-noise/30 rounded-full px-2 py-0.5
  The dot uses animate-pulse-slow
  Positioned absolute -top-3 -right-2

GSAP on mount:
  Both cards: fromTo { opacity:0, x:50 } → { opacity:1, x:0, duration:0.7, ease:'power3.out' }
  Stagger: 0.2s
  Delay: 1.4s
  Then: cards breathing — gsap.to(card1, { y: -4, duration: 3, yoyo: true, repeat: -1, ease: 'sine.inOut' })
```

---

#### 2d — Scroll Indicator

**Position:** `absolute bottom-8 left-1/2 -translate-x-1/2`

```
Flex col items-center gap-2:
  A vertical line: w-px h-8 bg-gradient-to-b from-border to-transparent
  A dot: w-1.5 h-1.5 rounded-full bg-prism-blue
    GSAP: dot moves from top to bottom of line in loop
    gsap.fromTo(dot, {y:-16}, {y:16, duration:1.2, repeat:-1, ease:'sine.inOut'})
  Text: "scroll" font-mono text-[10px] text-text-dim tracking-[0.2em] uppercase

Fade out on scroll: useEffect watches scrollY, when scrollY > 100 → opacity 0
```

---

### Section 3 — The Problem (Stats)

**ID:** `how-it-works`
**Background:** `bg-navy border-y border-border`
**Padding:** `py-20 px-6 md:px-12 lg:px-20`

**Section label (eyebrow):**

```
"THE PROBLEM" — font-mono text-xs text-prism-cyan tracking-[0.25em] uppercase text-center
```

**Heading:**

```
"One Move. Two Very Different Realities."
font-heading h2 text-text-primary text-center
Below: 2px spectrum gradient line, 100px wide, mx-auto, rounded-full, mt-4
```

**Two-column comparison grid (desktop side-by-side / mobile stacked):**

```
Left card — MANIPULATION TRAP:
  bg-noise-bg border border-noise/30 rounded-2xl p-6
  Top: "❌ Manipulation Trap" — text-noise font-mono text-sm font-bold
  Data rows (4):
    "Price Jump"  "→ +20%"
    "Liquidity"   "→ ₦40,000"
    "Orders"      "→ 3"
    "Volume"      "→ 0.9× avg"
  Each row: flex justify-between, label text-text-muted text-sm, value font-mono text-sm text-text-primary
  Divider border-t border-noise/20 my-4
  Score row: "Prism Score" label + <ScoreBadge score={22} size="sm" />
  Footer: "Signal: NOISE — price move is likely artificial"
    text-noise text-xs font-body italic mt-3

Right card — INFORMED MOVE:
  bg-informed-bg border border-informed/30 rounded-2xl p-6
  Top: "✓ Informed Move" — text-informed font-mono text-sm font-bold
  Same data rows:
    "Price Jump"  "→ +8%"
    "Liquidity"   "→ ₦2,100,000"
    "Orders"      "→ 842"
    "Volume"      "→ 3.2× avg"
  Divider border-t border-informed/20
  Score: <ScoreBadge score={84} size="sm" />
  Footer: "Signal: INFORMED — strong participation confirms the move"
    text-informed text-xs font-body italic mt-3

GSAP ScrollTrigger:
  Left card:  fromTo { opacity:0, x:-40 } → { opacity:1, x:0, duration:0.55, ease:'power2.out' }
  Right card: fromTo { opacity:0, x:+40 } → { opacity:1, x:0, duration:0.55, ease:'power2.out' }
  Trigger: when section enters viewport at 75%
  once: true
```

**Stat strip (below cards):**

```
4-item flex row (desktop) / 2×2 grid (mobile)
border-t border-border pt-12 mt-12

Items:
  "80%"    "of sudden moves on prediction markets are noise"
  "4"      "market microstructure factors per signal"
  "30s"    "detection latency from price change to signal"
  "0–100"  "signal strength score — one number, instant clarity"

Each:
  Number: font-mono font-bold text-h2 text-prism-cyan  (text-4xl)
  Label:  font-body text-sm text-text-secondary mt-1 max-w-[160px]

GSAP: numbers count up from 0 on scroll enter
  gsap.to(numEl, { textContent: targetValue, duration: 1.2, snap: { textContent: 1 }, ease: 'power2.out' })
  The "80%" and "0–100" are text — animate opacity only
```

---

### Section 4 — How It Works

**ID:** `how-it-works` (landing anchor)
**Background:** `bg-void`
**Padding:** `py-24 px-6 md:px-12 lg:px-20`

**Eyebrow:** "METHODOLOGY"
**Heading:** "Four Factors. One Score. Instant Clarity."

**Flow diagram (HowItWorksFlow.jsx):**

```
Desktop: horizontal left → right
Mobile:  vertical top → bottom

Nodes: Price Delta → Liquidity → Volume Velocity → Order Depth → [PRISM ENGINE] → Score 0-100 → Classification → AI Insight

Each node is a styled box:
  bg-navy-mid border border-border rounded-xl px-4 py-3
  Label: font-mono text-xs text-text-secondary
  Icon:  Lucide icon, text-prism-blue w-4 h-4

Connecting arrows: SVG <line> elements with an arrowhead marker
  Stroke: border-bright, strokeWidth 1, strokeDasharray 4 3

The PRISM ENGINE node is larger:
  bg-navy-light border border-prism-blue/40 rounded-xl px-5 py-4 shadow-glow-blue
  "PRISM" font-mono font-bold text-text-primary
  "ENGINE" font-mono text-xs text-text-muted
  A subtle spectrum gradient border-top 2px

Animation (GSAP ScrollTrigger):
  On scroll enter: each node fades in left-to-right with 0.15s stagger
  Connecting lines draw in after nodes: stroke-dashoffset animation
```

**4 factor cards below diagram:**

```
Grid: 2-col (mobile) / 4-col (desktop), gap-4, mt-12

Each card:
  bg-navy-mid border border-border rounded-xl p-5
  hover: border-border-bright transition-all duration-200

  Icon: rounded-lg bg-navy w-9 h-9 flex items-center justify-center + Lucide icon text-prism-blue
  Weight tag: "40% WEIGHT" / "25%" etc. — font-mono text-xs bg-prism-blue/10 text-prism-blue rounded px-2 py-0.5 mt-3
  Name: font-heading font-semibold text-text-primary text-base mt-2
  Desc: font-body text-sm text-text-secondary mt-1
  Example: font-mono text-xs text-text-muted mt-3 border-t border-border pt-3

Factors:
  1. TrendingUp   — 40% — "Price Delta"       — "How large is the probability jump?"     — "10% move = max strength"
  2. Droplets     — 25% — "Liquidity Depth"   — "How deep is the market? Easy to move?"  — "₦1M+ = reliable signal"
  3. Zap          — 20% — "Volume Velocity"   — "Is trading volume spiking vs baseline?" — "3× avg = max confirmation"
  4. Users        — 15% — "Order Depth"       — "How many independent orders drove it?"  — "1000 orders = max depth"

GSAP: y:30→0, opacity:0→1, stagger 0.12s on scroll enter
```

---

### Section 5 — Product Preview

**ID:** `product`
**Background:** `bg-navy border-y border-border`
**Padding:** `py-24 px-6 md:px-12 lg:px-20`

**Eyebrow:** "PRODUCT PREVIEW"
**Heading:** "Your Personal Market Intelligence Feed"
**Sub:** "Track the markets you care about. Get instant clarity on every movement."
`font-body text-text-secondary text-body max-w-lg mx-auto text-center mt-4`

**SignalFeedPreview (SignalFeedPreview.jsx):**

```
A simulated Tracker page in a browser-chrome wrapper.
Max-w: 680px, mx-auto, mt-12

Outer container:
  bg-void border border-border rounded-2xl overflow-hidden shadow-modal

Browser chrome bar:
  bg-navy-mid h-10 flex items-center px-4 gap-2 border-b border-border
  Three window dots: w-2.5 h-2.5 rounded-full — bg-noise, bg-uncertain, bg-informed
  Center: URL pill — "app.prism.io/tracker" font-mono text-xs text-text-muted bg-navy rounded px-3 py-1

Inner content (the mock tracker):
  Mini topbar replica: PrismLogo size=18 + "Tracker" text-text-muted text-xs font-mono
  Three TrackerCard components (compact, static mock data):
    Card 1: "Will Tinubu win re-election?" — Score 84 — INFORMED — Bayse — ⬆ Rising
    Card 2: "BTC above $100k by Dec?" — Score 56 — UNCERTAIN — Polymarket — → Stable
    Card 3: "Nigeria beats Ghana AFCON?" — Score 19 — NOISE — Bayse — ⬇ Falling

  GSAP loop: every 4 seconds, the topmost card "refreshes":
    Card border flashes once (opacity 0.5 → 1, 0.3s)
    Score number ticks up or down by 1–3 points (simulating real data)
    Direction arrow may change color
    A "Updated just now" text replaces the timestamp for 2 seconds then reverts

Bottom bar of mock:
  "● LIVE  Refreshing in {countdown}s" font-mono text-xs text-text-muted px-4 py-2 border-t border-border
  countdown ticks from 30 → 0 using setInterval in component state

Gradient fade at bottom of cards:
  absolute bottom-0 h-20 w-full
  bg-gradient-to-t from-void to-transparent pointer-events-none

GSAP on scroll enter: entire preview block → fromTo { opacity:0, y:30 } { opacity:1, y:0, duration:0.6 }
```

---

### Section 6 — Interactive Scoring Demo

**ID:** `scoring`
**Background:** `bg-void`
**Padding:** `py-24 px-6 md:px-12 lg:px-20`

**Eyebrow:** "INTERACTIVE DEMO"
**Heading:** "See the Score Come to Life"
**Sub:** "Drag the sliders. Watch Prism compute the signal in real time."

**Component:** `src/components/landing/ScoringDemoWidget.jsx`

```
Two-column layout (desktop stacked on mobile):
  Left: 4 labeled range sliders
  Right: Live score output

─── LEFT — SLIDERS ───

Each slider group:
  Label row: flex justify-between
    Left: "Price Delta" font-mono text-xs text-text-secondary uppercase tracking-wide
    Right: current value — font-mono text-xs font-bold text-text-primary
  Range input:
    type="range", fully custom styled:
      appearance: none, h-1 rounded-full bg-navy-mid cursor-pointer
      ::-webkit-slider-thumb: w-4 h-4 rounded-full bg-prism-blue border-2 border-navy cursor-grab
    value: controlled via useState

4 sliders:
  Price Delta:    min=0 max=25 step=1  → label "{value}% probability change"
  Liquidity:      min=0 max=100 step=1 → maps to log scale ₦10k–₦2M → label "₦{formattedValue}"
  Volume Ratio:   min=0 max=40 step=1  → real value = value/10 (0.0–4.0) → label "{value}× avg"
  Orders:         min=1 max=100 step=1 → maps log to 1–1000 → label "{formattedOrders} orders"

─── RIGHT — LIVE OUTPUT ───

Score display:
  <ScoreGauge score={computedScore} />  ← D3 arc gauge, 200×200px
  Below gauge: <ClassificationChip /> + <DirectionArrow />

4 factor contribution bars (FactorBars component, compact):
  MoveFactor, LiquidityFactor, VolumeFactor, OrderFactor
  Each: label left + animated bar + percentage right
  Bar color: text-prism-blue

Live AI insight simulation:
  Based on classification, shows a static context-appropriate insight:
    INFORMED: "Strong order depth and volume spike suggests institutional-level participation."
    UNCERTAIN: "Moderate activity — not enough confirmation to classify confidently."
    NOISE: "Thin liquidity means this move can be explained by a single large order."
  Appears/changes with a quick cross-fade (opacity 0→1, 0.3s) when classification changes

GSAP: When score crosses 70 → ScoreBadge does scale pulse: gsap.fromTo(badge, {scale:1},{scale:1.08,yoyo:true,repeat:1,duration:0.25})
GSAP: When classification changes → chip does a brief opacity flash
```

---

### Section 7 — CTA Footer

**Background:** `bg-navy border-t border-border`
**Padding:** `py-24 px-6 md:px-12 lg:px-20`

**Content (centered, flex flex-col items-center):**

```
PrismLogo size=44 (icon only, animate-float)
Heading: "Ready to See What Markets Are Really Saying?"
  font-heading font-bold text-center text-text-primary
  font-size: clamp(1.75rem, 3vw, 2.5rem)
Sub: "Join traders already using Prism to cut through market noise."
  font-body text-text-secondary text-center mt-3 max-w-md
Buttons (mt-8 flex gap-4):
  "Create Free Account" — primary, lg — onClick → /auth
  "Read the Methodology" — ghost, lg — onClick → smooth scroll #scoring

GSAP ScrollTrigger:
  Logo: scale 0.85→1, opacity 0→1, duration 0.5
  Heading: y:20→0, opacity 0→1, duration 0.5, delay 0.1
  Sub: opacity 0→1, delay 0.25
  Buttons: y:12→0, opacity 0→1, delay 0.4
```

**Page Footer (below CTA):**

```
border-t border-border mt-16 pt-8 pb-12
3-col grid (desktop) / 1-col (mobile) gap-8

Col 1: PrismLogo size=22 + "Filter the Noise. Trade the Signal." text-text-muted text-sm font-body mt-2
Col 2: Links — Home · Discover · Tracker · Methodology — font-body text-sm text-text-secondary hover:text-text-primary
Col 3: "Built on Polymarket & Bayse · Powered by Google Gemini AI" text-text-muted text-xs font-body

Bottom: "© 2025 Prism · Signal Intelligence Engine" text-text-muted text-xs font-mono text-center mt-8
```

---

## 10. AUTH FLOW — SIGNUP / LOGIN / VERIFY

### Overview

Prism uses a secure, multi-stage authentication system powered by Email and Passwords, enforced by OTP (One-Time Password) verification for critical actions (first-time signup and password recovery).

1. **Signup**: `/auth/signup` — Create account with Email/Password → OTP sent to inbox.
2. **Verification**: `/auth/otp` — Enter 6-digit code to activate account.
3. **Login**: `/auth/login` — Enter credentials → HttpOnly session cookies set → Redirect to `/app`.
4. **Password Recovery**: `/auth/forgot-password` → OTP → `/auth/reset-password`.

Success is always defined by the presence of a double HttpOnly cookie set (`access_token` and `refresh_token`).

---

### Common Auth Shell

**Background:** Full-screen `bg-void`. No topbar, no nav.

**Background decoration:** A large, low-opacity prism SVG (the logo icon, `size=480`, `opacity-[0.03]`) positioned `absolute -right-40 top-1/2 -translate-y-1/2` — visible only on desktop.

**Card wrapper:**
```
min-h-screen flex items-center justify-center px-4
Card: bg-navy border border-border rounded-2xl p-8 md:p-10
      w-full max-w-[420px] shadow-modal
```

---

### Phase 1: SignupPage.jsx

**Route:** `/auth/signup`

**Purpose:** Initial onboarding.
**Form Inputs:**
- Email (`type="email"`)
- Password (`type="password"`)
- Confirm Password (`type="password"`)

**Logic:**
1. Call `POST /api/v1/auth/signup`.
2. On success, backend sends a verification OTP to the email.
3. API returns `{ success: true, message: "...", data: { uid: "...", email: "..." } }`.
4. Frontend logic: `router.navigate({ to: '/auth/otp', search: { email, uid: response.data.uid, type: 'signup' } })`.

---

### Phase 2: OTPPage.jsx (Verification)

**Route:** `/auth/otp?email=...&uid=...&type=signup`

**Purpose:** Verify the user identity via the 6-digit code sent to their inbox.

**UI:** 
- A custom 6-box numeric input.
- "Verified" welcome email is triggered by the backend upon successful verification code entry.

**Logic:**
1. Call `POST /api/v1/auth/verify-otp`.
2. Payload: `{ uid, otp, otp_type: 'signup' }`. (Pass the correct type from URL).
3. On success: Verification complete. The user account is now "Verified".
4. Frontend logic: Redirect to `/auth/login` with a success toast: "Account verified! Please sign in."

---

### Phase 3: LoginPage.jsx

**Route:** `/auth/login`

**Purpose:** Authenticate an existing, verified user.
**Form Inputs:**
- Email
- Password

**Logic:**
1. Call `POST /api/v1/auth/login`.
2. Success: The backend sets two HttpOnly cookies (`access_token`, `refresh_token`).
3. Payload: Returns basic user data in `data`.
4. Frontend logic:
   - Call `queryClient.setQueryData(['session'], response.data.data)`.
   - `router.navigate({ to: '/app' })`.

---

### Phase 4: Password Recovery

**Flow:**
1. **Request**: `/auth/forgot-password` → `POST /api/v1/auth/forgot-password` with `{ email }`.
2. **Verify**: User redirected back to `/auth/otp` with `type=forgotpassword`.
3. **Reset Token**: On successful OTP verification (`otp_type: 'forgotpassword'`), the backend returns a `reset_token` in the data object.
4. **Update**: Redirect to `/auth/reset-password?token=...`.
5. **Execute**: Submit `new_password` and `reset_token` to `POST /api/v1/auth/reset-password`.
6. **Finish**: Return to Login.

---

## 11. DISCOVERY PAGE

**File:** `src/pages/app/DiscoveryPage.jsx`
**Route:** `/app`
**Layout:** AppLayout

### Purpose

First page users see after authentication. Find markets, understand them at a glance via light signal intelligence, add them to the Tracker. The hook: even the browse cards show Prism's intelligence — a score, a classification, a direction arrow — so the product has identity before the user has tracked anything.

---

### Page Header

```
Positioned directly below topbar, inside max-w-6xl mx-auto px-6 pt-6

"Discover Markets" — font-heading h2 text-text-primary
"Find markets worth tracking. Signal intelligence shown for each." — font-body text-sm text-text-secondary mt-1

GSAP on mount:
  Heading: fromTo { opacity:0, y:10 } → { opacity:1, y:0, duration:0.35 }
  Sub: fromTo { opacity:0 } → { opacity:1, duration:0.3, delay:0.1 }
```

---

### Search Bar

```
Container: mt-6 relative max-w-2xl

Input:
  bg-navy-mid border border-border rounded-xl px-4 py-3.5 pl-12 w-full
  font-body text-sm text-text-primary
  placeholder: "Search markets or paste a Polymarket / Bayse link…" text-text-dim
  focus: border-border-bright ring-1 ring-prism-blue/25 outline-none
  transition-all duration-200

Left icon: Search (Lucide) — absolute left-4 top-1/2 -translate-y-1/2 — text-text-muted w-4 h-4
  On focus: color transitions to text-prism-blue

Right: when input has value → clear button (X icon, Lucide XCircle, text-text-muted hover:text-text-primary)
       when input is empty + not focused → nothing

Right: when loading a search → Spinner size=16, absolute right-4 top-1/2 -translate-y-1/2

Behavior:
  - Debounce input 350ms before firing useMarketSearch query
  - If input matches a URL pattern (contains "polymarket.com" or "bayse.io") → treat as paste-link mode:
      Show a different placeholder above results: "Adding market from link…"
      Call a different API endpoint: POST /markets/import?url=...
      On success: market is fetched, pre-ingested, and shown as the top result with "+ Track" CTA
  - If plain keyword → GET /markets?q=keyword (searches pre-ingested pool)
  - If input is empty → show default tabs below

GSAP:
  On focus: subtle border glow, gsap.to(container, { boxShadow: 'var(--shadow-glow-blue)', duration:0.2 })
  On blur: gsap.to(container, { boxShadow: 'none', duration:0.2 })
```

---

### Feed Tabs

```
Shown when search input is empty. Hidden when search results are active.
Container: mt-6 flex items-center gap-1 border-b border-border

Two tabs:
  "🔥 Trending Signals"
  "📈 Popular Markets"

Each tab:
  font-body text-sm px-4 py-2.5 cursor-pointer transition-colors
  Inactive: text-text-secondary hover:text-text-primary
  Active: text-text-primary border-b-2 border-prism-blue (border sits on the border-b of the container)
         The active border is a 2px line, color prism-blue, sits flush with container bottom border

Active tab state: useState('trending') — default to trending
Tab switch:
  GSAP: content area crossfades — outgoing opacity 0 (0.15s), incoming fades in (0.2s)
  Active tab underline slides: gsap.to(indicator, { x: newX, duration:0.2, ease:'power2.out' })

"Trending Signals" tab:
  Data: GET /markets?tab=trending → markets where a signal was detected in the last 6 hours, sorted by score desc
  These already have signal data pre-computed

"Popular Markets" tab:
  Data: GET /markets?tab=popular → sorted by liquidity or volume, broader pool
  These may not have recent signals — show "No recent signal" state on cards
```

---

### Market Cards Grid (SignalCard.jsx)

```
Grid layout:
  Mobile:  1 column, full width
  Tablet:  2 columns, gap-4
  Desktop: 3 columns, gap-4 (or 2 wide columns if wide cards preferred)

mt-6 for the grid
```

**SignalCard.jsx/tsx:**

```jsx
/**
 * SignalCard
 * Universal card component used on Discovery and Tracker pages.
 * Handles both Single Markets (Yes/No) and Combined Markets (Multiple candidates).
 *
 * Props:
 *   event {object}   — umbrella event data including type and highest scoring market
 *   onTrack {fn}     — called when "+ Track" is clicked (tracks event_id)
 *   isTracked {bool} — if user already tracks this event
 *   isAdding {bool}  — loading state for track mutation
 */
```

**Card structure:**

```
Container:
  bg-navy-mid border border-border rounded-xl p-5
  hover: border-border-bright shadow-card cursor-pointer
  transition-all duration-200
  If event.signal.classification === 'INFORMED_MOVE': border-l-[3px] border-l-informed
  If event.signal.classification === 'NOISE':         border-l-[3px] border-l-noise
  If event.signal.classification === 'UNCERTAIN':     border-l-[3px] border-l-uncertain
  If no signal: no left border override

  onClick → router.navigate({ to: '/app/events/$eventId', params: { eventId: event.id } })
  Note: clicking the Track button does NOT navigate — e.stopPropagation() on button

─── TOP ROW ───
flex justify-between items-start gap-3

  Left:
    SourceBadge (Polymarket / Bayse)
    Event title: font-heading font-semibold text-text-primary text-sm leading-snug mt-1.5
      max 2 lines: overflow-hidden, display: -webkit-box, -webkit-line-clamp: 2
    
    Target Subtitle (Conditional rendering):
      If event.event_type === 'combined': 
        "↳ Spiking on: {event.highest_scoring_market_name} (Score: {event.highest_scoring_market_score})"
        font-mono text-xs text-prism-teal mt-1
      If event.event_type === 'single':
        Render hidden or subtle "↳ Moving on: YES"

  Right:
    If signal exists: <ScoreBadge score={event.highest_scoring_market_score} size="sm" />
    If no signal: empty, no placeholder

─── MIDDLE ROW (signal data, only if signal exists) ───
mt-3 pt-3 border-t border-border flex items-center justify-between

  Left:
    Probability: "{market.currentProb}%" — font-mono font-bold text-text-primary text-lg
    Delta arrow row:
      <DirectionArrow direction="up|down|stable" delta={market.signal.deltaP} />
      e.g. "⬆ +12%" in text-informed font-mono text-xs

  Right:
    <ClassificationChip classification={market.signal.classification} size="sm" />

─── SIGNAL DETAIL ROW ───
mt-2 flex gap-4 flex-wrap

  Three data pills (font-mono text-xs):
    [Droplets icon 12px text-text-muted] "₦{liquidity}"
    [Users icon] "{orders} orders"
    [Zap icon] "{volRatio}× vol"

─── AI SNIPPET (only if INFORMED_MOVE and ai_insight exists) ───
mt-3 pt-3 border-t border-border/50

  [Sparkles icon 12px text-informed]
  Short ai_insight text: italic, text-text-secondary text-xs
  max 2 lines: webkit-line-clamp: 2

─── BOTTOM ROW ───
mt-4 flex justify-between items-center

  Left: "Updated {timeAgo}" — font-mono text-xs text-text-muted

  Right:
    If isTracked:
      "✓ Tracked" — text-informed font-mono text-xs flex items-center gap-1.5
      CheckCircle icon 12px text-informed
    If not tracked:
      <Button variant="outline" size="sm" loading={isAdding} loadingText="Adding…" onClick={handleTrack}>
        + Track Market
      </Button>

─── NO SIGNAL STATE ───
When market has no recent signal (Popular tab):
  Middle row replaced with:
    "No recent signal detected" — font-mono text-xs text-text-muted italic
    "Market data collecting…" if market was recently added via paste-link
```

**GSAP entrance (on page load):**

```
Grid cards: fromTo { opacity:0, y:16 } → { opacity:1, y:0, duration:0.3, stagger:0.06 }
On tab switch: new cards fade + slide in
On track success: card right side transitions — button disappears, "✓ Tracked" fades in
  gsap.to(button, { opacity:0, scale:0.9, duration:0.2 })
  gsap.fromTo(trackedLabel, { opacity:0, x:-8 }, { opacity:1, x:0, duration:0.3 })
  A tiny success particle burst from the button position (optional polish):
    3–4 small dots (w-1.5 h-1.5, colors informed/prism-blue) shoot outward and fade
    gsap.to(dots, { x: random(-20,20), y: random(-20,20), opacity:0, duration:0.5, stagger:0.05 })
```

---

### Search Results State

```
When search query is active (input has value):

  If loading (debounce in progress or API pending):
    Show 3 × MarketCardSkeleton
    Search icon in input transitions to Spinner

  If results exist:
    Grid of MarketCard components with the matching markets
    Above results: "{n} results for "{query}"" — text-text-muted text-xs font-mono

  If no results (keyword search):
    EmptyState:
      icon: SearchX (Lucide)
      message: "No markets found for "{query}""
      subtext: "Try a different keyword, or paste a Polymarket/Bayse market link above."

  If URL detected and market successfully imported:
    The imported market appears as a single card at top with a subtle highlight:
      border border-prism-blue/40 bg-prism-blue/5
      "Imported from link" label at top in font-mono text-xs text-prism-cyan
    Below it, normal search results if any

  If URL import fails:
    Toast (error variant): "Could not import market. Check the link and try again."
```

---

### Empty & Loading States

```
Initial load (first time page opens after login):
  Show 6 × MarketCardSkeleton (2 rows of 3 on desktop, 3 on mobile)
  With shimmer animation

Error state (API down):
  <ErrorState
    icon="WifiOff"
    message="Unable to load markets"
    subtext="Check your connection or try again shortly."
    action={{ label: 'Retry', onClick: refetch }}
  />
```

---

## 12. TRACKER PAGE

**File:** `src/pages/app/TrackerPage.jsx`
**Route:** `/app/tracker`
**Layout:** AppLayout

### Purpose

The user's personal market intelligence feed. A list of the markets they've chosen to follow. This page is the daily-return hook — it must feel alive, dense with signal, and worth checking. Cards update via 30-second polling. Score changes animate. Direction arrows shift.

---

### Page Header

```
flex justify-between items-start
  Left:
    "My Tracker" — font-heading h2 text-text-primary
    "{n} markets tracked" — font-body text-sm text-text-secondary mt-1

  Right:
    <LivePulse lastUpdated={data?.fetchedAt} refetchInterval={30000} />
    "Manage" text button — font-body text-xs text-text-muted hover:text-text-secondary
      Toggles a "remove mode" where cards show a remove button
```

---

### New Signal Alert Banner

```
When a tracked market's score jumps ≥15 points between polling cycles:
  A banner slides in from the top (below topbar, above page content):
    bg-informed-bg border-b border-informed/30
    px-6 py-3 flex items-center gap-3 justify-between

  Left: [TrendingUp icon text-informed] "Signal jumped on "{marketTitle}": 45 → 82 (INFORMED MOVE)"
         font-body text-sm text-text-primary

  Right: "View →" — text-prism-blue text-sm font-mono hover:underline
         onClick → navigate to /app/markets/{marketId}
         Also: dismiss X button, text-text-muted

  GSAP: banner slides down from y:-100% → y:0, duration:0.4, ease:'power3.out'
  Auto-dismiss after 8 seconds: GSAP.to(banner, {y:'-100%', opacity:0, duration:0.3, delay:8})
  Also dismiss on X click or "View →" click

  One banner at a time — if multiple markets alert simultaneously, queue them
```

---

### Empty State (no tracked markets)

```
Shown when user has 0 tracked markets — likely just signed up.

Centered content, py-20:
  PrismLogo size=44, opacity-40, animate-float
  "Your tracker is empty"
    font-heading text-h3 text-text-secondary text-center mt-6
  "Go to Discover to add markets worth watching."
    font-body text-sm text-text-muted text-center mt-2
  <Button variant="primary" size="md" onClick → navigate('/app')} mt-6>
    Discover Markets
  </Button>

GSAP on mount: fromTo {opacity:0, y:20} → {opacity:1, y:0, duration:0.4}
```

---

### Tracker Cards List

```
flex flex-col gap-3

Data: useTrackedMarkets() — GET /tracker, refetchInterval: 30_000, staleTime: 25_000

On refetch, if score changed for any card:
  - Score number animates to new value (GSAP gsap.to textContent)
  - If direction changed: DirectionArrow re-animates (brief scale bounce)
  - If classification changed: ClassificationChip crossfades to new color
  - Card's left border color transitions to match new classification

Loading (initial): 3 × TrackerCardSkeleton
Error: ErrorState with retry
```

---

### TrackerCard.jsx -> Now Reuses SignalCard.jsx

The Tracker page functions identically to the Discovery Page feed but acts as the user's customized radar.
Instead of a separate TrackerCard, use the EXACT conditional `<SignalCard />` component from above.

Data logic: Ensure TanStack Query is actively polling the backend for these specific tracked events every 30-60 seconds.

─── REMOVE MODE (when removeMode === true) ───
Overlay appears on card (position absolute inset-0 bg-navy/80 backdrop-blur-sm rounded-xl):
  Centered content:
    "Remove from Tracker?" font-body text-sm text-text-primary text-center
    Two buttons: "Keep" (ghost sm) + "Remove" (danger sm, loading={isRemoving})

─── FOOTER (always present) ───
mt-4 flex justify-between items-center

  Left: "Last signal: {timeAgo}" font-mono text-xs text-text-muted
  Right: "View Full Analysis →" font-mono text-xs text-prism-blue hover:underline
         (this is redundant with card click but serves as a clear affordance)
```

**GSAP behaviors on TrackerCard:**

```
On mount (first load): stagger fromTo {opacity:0, y:16} → {opacity:1, y:0}
On score update:
  New score ≠ old score →
    gsap.fromTo(scoreEl, {scale:1.15, color:'#E8F0FE'}, {scale:1, color: classificationColor, duration:0.4, ease:'back.out(2)'})
On classification change:
  Left border: gsap animates border-color transition (GSAP can animate CSS vars)
  ClassificationChip: opacity 0 → 1 crossfade with new chip
On remove mode toggle:
  Overlay: fromTo {opacity:0} → {opacity:1, duration:0.2}
On successful remove:
  Card: gsap.to(card, {height:0, opacity:0, marginBottom:0, paddingTop:0, paddingBottom:0, duration:0.35, ease:'power2.in', onComplete: removeFromDom})
```

---

### Sort Controls

```
Above the card list, flex justify-between items-center:

  Left: "{n} markets" text-text-muted text-sm font-mono

  Right: sort select:
    "Sort: Highest Score ▾" / "Lowest Score" / "Most Recent"
    bg-navy-mid border border-border rounded-lg px-3 py-1.5 text-text-secondary text-sm font-body
    Appearance: none + custom chevron-down icon positioned right
    onChange → sort tracked markets client-side (no re-fetch)
```

---

## 13. EVENT ANALYSIS PAGE

**File:** `src/pages/app/EventDetail.tsx`
**Route:** `/app/events/$eventId`
**Layout:** AppLayout

### Purpose

The quantitative dashboard. By using a tabbed layout, this single page template seamlessly handles both Single and Combined markets automatically.

---

### Section A: The Header (Aggregate View)

```
max-w-4xl mx-auto px-6 pt-6

Breadcrumb:
  "Tracker → {event.title truncated to 30 chars}" — font-mono text-xs text-text-muted
  "/" separator: text-text-dim
  "← Back" on the left: font-mono text-xs text-text-muted hover:text-text-secondary
    onClick → router.history.back()

Event Title:
  font-heading font-bold text-text-primary
  font-size: clamp(1.4rem, 2.5vw, 2rem)
  line-height: 1.2
  mt-3

Meta row (flex items-center gap-4 mt-2 flex-wrap):
  <SourceBadge source={event.source} />
  Event Heat Score: <ScoreBadge score={event.highest_scoring_market.score} size="md" /> (Max score of all children)
  "Total Pool: ₦{totalLiquidity}" — font-mono text-xs text-text-muted
  "Updated {timeAgo}" — font-mono text-xs text-text-muted
```

---

### Section B: The AI Insight (Conditional Context)

```
mt-4 bg-navy-mid border border-prism-blue/25 rounded-2xl p-6
A 1px left border in gradient: linear-gradient(#7C3AED, #06B6D4) — 3px width

Section header:
  [Sparkles icon text-prism-cyan] "AI INTERPRETATION" font-mono xs uppercase tracking-wide
  Right: "Powered by Google Gemini" — font-mono text-[10px] text-text-dim

Insight text:
  blockquote style — pl-4 border-l-2 border-prism-blue/40
  font-body italic text-text-primary text-[0.9375rem] line-height 1.75
  
  If Combined Market: The AI describes the relationship/tug-of-war (e.g., "Money is rapidly exiting France and flowing into Argentina with heavy volume...").
  If Single Market: The AI describes the directional momentum (e.g., "Heavy institutional volume is accumulating on the YES contract...").
```

---

### Section C: The Outcomes Navigation (The Universal Tab Bar)

```
Implement a horizontal, scrollable tab menu below the AI insight.

If Combined Market: The tabs are the candidates. 
  [ Argentina (88) ] [ France (42) ] [ England (12) ]
If Single Market: The tabs are the two sides of the contract.
  [ YES (79) ] [ NO (12) ]

Auto-Select Logic: On page load, React automatically sets the "Active Tab" to the outcome with the highest score.
```

---

### Section D: The Outcome Details (Dynamic Panel)

Everything below the tab bar is a dynamic panel controlled entirely by the selected tab. When a user clicks "France" or "YES", this section instantly swaps data.

```
mt-6 bg-card border border-border rounded-2xl p-6 md:p-8
If INFORMED_MOVE: border-informed/30 bg-informed-bg/20 shadow-glow-informed
If UNCERTAIN: border-uncertain/30 bg-uncertain-bg/20
If NOISE: border-noise/30 bg-noise-bg/20

Layout: flex flex-col md:flex-row gap-6 items-center md:items-start

─── LEFT — SCORE GAUGE ───
<ScoreGauge score={selectedTab.signal.score} size={180} />
Below gauge: <ClassificationChip size="md" /> centered

─── RIGHT — SIGNAL SUMMARY ───
flex flex-col gap-4

Probability movement:
  "{selectedTab.prevProb}% → {selectedTab.currProb}%" — font-mono font-bold text-text-primary text-3xl
  Delta: "+{deltaP}% change" — font-mono text-sm, colored by direction

Three quick metrics (flex row):
  "Liquidity" | "Volume" | "Orders"
  Value: font-mono font-bold text-text-primary text-xl
  Label: font-mono text-xs text-text-muted
```

---

### Section 2 — What's Happening

```
mt-4 bg-navy-mid border border-border rounded-2xl p-6

Section header:
  flex items-center gap-2:
    [BarChart3 icon 16px text-prism-blue]
    "WHAT'S HAPPENING" — font-mono text-xs text-text-muted uppercase tracking-wide

Three labeled metric rows:

Row 1 — Price Movement:
  Left: "Price Movement" — font-body text-sm text-text-secondary
  Center: A horizontal magnitude bar
    bg-navy border border-border rounded-full h-2 w-full max-w-[200px]
    Inner fill: width = (deltaP / 0.25) * 100 clamp 100%, color by classification
    Animated: width expands from 0 on mount (GSAP, 0.5s ease-out)
  Right: "+{deltaP * 100}% spike" — font-mono text-sm font-bold text-text-primary

Row 2 — Volume Activity:
  Left: "Volume Activity"
  Center: Same bar, fill = (volRatio / 4) * 100 clamped, color prism-blue
  Right: "{volRatio}× normal activity" — colored amber if >2×, green if >3×

Row 3 — Liquidity:
  Left: "Market Liquidity"
  Center: Same bar, fill = liquidityFactor * 100
  Right: "₦{formattedLiquidity}" + strength label:
    <₦100k: "Thin — easily moved" text-noise
    ₦100k–₦1M: "Moderate" text-uncertain
    >₦1M: "Strong" text-informed

Below the 3 rows, a Probability History chart:
  Title: "Probability over time" — font-mono text-xs text-text-muted uppercase mt-5 mb-3
  <ProbabilityLine marketId={marketId} />
    D3 or Recharts line chart
    X: timestamps of last 20 snapshots
    Y: probability 0%–100%
    Line: smooth monotone curve, color prism-blue, strokeWidth 2
    Signal detection point: vertical dashed line at signal.detected_at
      A colored dot on the line at that point (color by classification)
    Custom axes: text-text-muted text-xs font-mono, no gridlines except y=50%
    Tooltip: bg-navy border border-border rounded-lg px-3 py-2 shadow-card
              "{probability}% · {timestamp}" font-mono text-xs
    Height: 200px desktop / 160px mobile
    Animate on mount: line draws in via stroke-dashoffset (D3 path length technique)
```

---

### Section 3 — Smart Money Analysis

```
mt-4 bg-navy-mid border border-border rounded-2xl p-6

Section header:
  [Wallet icon text-prism-cyan] "SMART MONEY" font-mono xs uppercase

Two-column grid (desktop) / single col (mobile):

Left: "Order Pattern"
  Whale vs Crowd indicator:
    A donut chart (D3, small — 80px diameter)
    Segment 1: "Large Orders" — prism-violet, percentage based on order depth score
    Segment 2: "Small Orders" — prism-blue
    Center: dominant label — "Crowd" or "Institutional"
  Below: interpretation text
    If orders < 20 and score > 60:
      "Move driven by {orders} orders — possible whale activity"
      text-uncertain font-body text-sm
    If orders > 200 and score > 60:
      "Broad-based participation — crowd conviction"
      text-informed font-body text-sm
    Else:
      "Mixed order pattern — no dominant participant type"
      text-text-secondary font-body text-sm

Right: "Order Depth Score"
  Factor breakdown mini-bars (compact, no labels):
    MoveFactor, LiquidityFactor, VolumeFactor, OrderFactor
    Each: thin bar (h-1.5) + factor name + contribution value
    All 4 in a vertical stack, gap-2
  Below: "Composite Score: {score}/100" font-mono text-xl font-bold text-text-primary
```

---

### Section 4 — Trap Analysis

```
mt-4 rounded-2xl p-6 border
  If trap risk is HIGH (low liquidity + high delta):
    bg-noise-bg border-noise/30
  If MEDIUM:
    bg-uncertain-bg border-uncertain/30
  If LOW:
    bg-informed-bg border-informed/30

Section header:
  [AlertTriangle icon, colored by risk level] "TRAP ANALYSIS" font-mono xs uppercase

Trap Risk indicator:
  Large label: "LOW / MEDIUM / HIGH TRAP RISK"
    font-mono font-bold text-[1.75rem], color by level
  GSAP on mount: number/label scales in fromTo {scale:0.8, opacity:0} → {scale:1, opacity:1, duration:0.4, ease:'back.out(1.5)'}

Explanation (1–2 sentences, dynamically generated from data):
  Templates:
    HIGH:   "Low liquidity (₦{liq}) with a {delta}% price spike. A single large order may have caused this move. Proceed with significant caution."
    MEDIUM: "Moderate liquidity with unusual volume. The signal shows some manipulation risk but is not conclusive."
    LOW:    "Strong liquidity and diverse order flow reduce manipulation risk significantly. This move is harder to fake."
  font-body text-sm text-text-primary line-height 1.7

Trap risk is computed client-side from the signal data:
  HIGH if liquidityFactor < 0.3 AND moveFactor > 0.5
  MEDIUM if liquidityFactor < 0.6 AND moveFactor > 0.3
  LOW otherwise
```

---

### Section 5 — Momentum

```
mt-4 bg-navy-mid border border-border rounded-2xl p-6

Section header:
  [TrendingUp/TrendingDown icon colored by momentum] "MOMENTUM" font-mono xs uppercase

Momentum assessment (derived from classification + score trend):
  <VolumeSpike /> chart:
    Bar chart, D3
    X: last 10 snapshot timestamps
    Y: volume at each snapshot
    Most recent bars highlighted (opacity 1.0), older bars dimmer (opacity 0.4)
    If volume is increasing → bars progressively taller, color prism-blue
    If volume is decreasing → bars shorter
    Height: 120px
    No axes, just bars — minimalist sparkline style

Below chart, a momentum verdict row:
  Large label: "Likely to Continue" or "Likely to Reverse" or "Inconclusive"
  font-mono font-bold text-xl
  Color: text-informed for Continue, text-noise for Reverse, text-text-secondary for Inconclusive

  Logic:
    "Likely to Continue" if: score ≥ 70 AND volRatio > 2
    "Likely to Reverse"  if: score < 40 OR (volRatio < 1.2 AND liquidityFactor < 0.4)
    "Inconclusive"       otherwise

  Confidence bar:
    A simple progress bar showing confidence %
    Computed: if Continue, confidence = score%; if Reverse, confidence = (100 - score)%
    bg-navy h-1.5 rounded-full with inner fill, color by verdict

GSAP: verdict label types in character-by-character using textContent update loop
      or simpler: fromTo {opacity:0, x:-10} → {opacity:1, x:0, duration:0.4}
```

---

### Section 6 — AI Interpretation

```
Only rendered if signal.classification === 'INFORMED_MOVE' && signal.ai_insight

mt-4 bg-navy-mid border border-prism-blue/25 rounded-2xl p-6
A 1px left border in gradient: linear-gradient(#7C3AED, #06B6D4) — 3px width

Section header:
  [Sparkles icon text-prism-cyan] "AI INTERPRETATION" font-mono xs uppercase tracking-wide
  Right: "Powered by Google Gemini" — font-mono text-[10px] text-text-dim

Insight text:
  blockquote style — pl-4 border-l-2 border-prism-blue/40
  font-body italic text-text-primary text-[0.9375rem] line-height 1.75
  signal.ai_insight (2–3 sentences from Gemini)

GSAP: text types in word by word using a split-text technique:
  Split ai_insight by " " → array of span elements
  gsap.fromTo(spans, {opacity:0}, {opacity:1, duration:0.03, stagger:0.04})
  This creates a fast typewriter word-reveal effect (not character by character — too slow)

Footer:
  "AI reasons over quantitative data, not news headlines." — font-mono text-[10px] text-text-dim mt-4
```

---

### Section 7 — Action Guidance

```
mt-4 bg-navy-mid border border-border rounded-2xl p-6

Section header:
  [Crosshair icon text-prism-blue] "WHAT THIS MEANS" font-mono xs uppercase

Guidance text (templated by classification):
  INFORMED_MOVE:
    "Signal is strong and backed by meaningful participation. This move is worth attention — but Prism does not predict outcomes. Verify independently before acting."
  UNCERTAIN:
    "Signal shows some activity but lacks sufficient confirmation. Monitor this market for further development before drawing conclusions."
  NOISE:
    "This move has characteristics of a noise artifact or thin-market manipulation. High caution is recommended. Do not act on this signal alone."

  font-body text-text-primary text-sm line-height 1.8
  Each guidance text is preceded by a colored icon row matching classification

Legal disclaimer (smaller, below):
  "Prism provides analytical tools, not financial advice. All trading decisions are your own responsibility."
  font-mono text-[10px] text-text-dim mt-4 pt-4 border-t border-border

View on Source button:
  mt-4
  <Button variant="ghost" size="sm" icon={<ExternalLink size={14}/>} iconPos="right">
    View on {market.source}
  </Button>
  onClick → window.open(market.sourceUrl, '_blank')
```

---

### Analysis Page GSAP Entrance

```
All sections enter sequentially as user scrolls:
  GSAP ScrollTrigger on each section container
  start: 'top 82%'
  Effect: fromTo {opacity:0, y:20} → {opacity:1, y:0, duration:0.45, ease:'power2.out'}
  Each section triggers independently (not all at once on page load)
  once: true

First section (Main Signal) — no scroll trigger needed, plays on mount:
  ScoreGauge arc draws in
  Classification banner slides in from left
  Probability display counts up from 0
```

---

## 14. SHARED COMPONENT LIBRARY

### ScoreBadge.jsx

```
A circular badge showing the signal score number.

Props: score (0-100), size ('xs'|'sm'|'md'|'lg'|'xl'), showRing (bool)

Sizes:
  xs: w-8 h-8   text-xs   ring strokeWidth 2
  sm: w-12 h-12 text-sm   ring strokeWidth 2.5
  md: w-16 h-16 text-lg   ring strokeWidth 3
  lg: w-20 h-20 text-2xl  ring strokeWidth 3.5
  xl: w-24 h-24 text-3xl  ring strokeWidth 4

Colors (by score):
  ≥70: text-informed bg-informed-bg border-informed/50 shadow-glow-informed
  ≥40: text-uncertain bg-uncertain-bg border-uncertain/50 shadow-glow-uncertain
  <40: text-noise bg-noise-bg border-noise/50 shadow-glow-noise

Container: rounded-full border-2 flex items-center justify-center flex-shrink-0

If showRing:
  SVG circle overlaid (absolute inset-0):
    Track circle: full circumference, opacity-20, same color
    Progress arc: stroke-dasharray = circumference, stroke-dashoffset = (1 - score/100) * circumference
    Animates on mount: gsap.fromTo(arc, {strokeDashoffset: circumference}, {strokeDashoffset: final, duration:0.8, ease:'power2.out'})

Score number: font-mono font-bold, centered
```

### ClassificationChip.jsx

```
Props: classification, size ('sm'|'md')

INFORMED_MOVE: bg-informed-bg text-informed border border-informed/40
               icon: TrendingUp (Lucide 12px)  label: "Informed Move"
UNCERTAIN:     bg-uncertain-bg text-uncertain border border-uncertain/40
               icon: Minus                     label: "Uncertain"
NOISE:         bg-noise-bg text-noise border border-noise/40
               icon: TrendingDown              label: "Noise"

Container: rounded-full inline-flex items-center gap-1.5
  sm: px-2 py-0.5 text-xs font-mono
  md: px-3 py-1 text-xs font-mono font-semibold tracking-wide
```

### DirectionArrow.jsx

```
Props: direction ('up'|'down'|'stable'), delta (number), compact (bool)

up:     [ArrowUp icon] "+{delta}%" — text-informed
down:   [ArrowDown icon] "-{delta}%" — text-noise
stable: [Minus icon] "Stable" — text-text-muted

Icon size: 12px (compact=true) or 14px
Font: font-mono text-xs (compact) or text-sm

If compact: icon only, no label (used in TrackerCard top row)
If not compact: icon + text (used in analysis page)
```

### SourceBadge.jsx

```
Props: source ('Polymarket'|'Bayse')

A pill badge identifying the data source.

Polymarket: bg-prism-violet/15 text-prism-violet border border-prism-violet/30
Bayse:      bg-prism-teal/15  text-prism-teal  border border-prism-teal/30

Content: source name in font-mono text-[10px] uppercase tracking-wide
Size: px-2 py-0.5 rounded-full
```

### LivePulse.jsx

```
Props: lastUpdated (Date), refetchInterval (number ms)

Shows: [●] "Updated {n}s ago"

Dot: w-1.5 h-1.5 rounded-full bg-informed animate-pulse-slow
Text: font-mono text-xs text-text-secondary

Counter: counts up seconds since lastUpdated via useEffect + setInterval(1000)
When lastUpdated changes (new data arrives): counter resets to 0, text briefly shows "Updated now" in text-informed for 1.5s then reverts to counter
```

### Input.jsx

```
Props: label, type, placeholder, value, onChange, error, hint, leftIcon, rightIcon, ...props

Wrapper: flex flex-col gap-1.5

Label: font-mono text-xs text-text-secondary uppercase tracking-wide

Input container: relative

Input element:
  w-full bg-navy-mid border border-border rounded-xl px-4 py-2.5
  font-body text-sm text-text-primary placeholder-text-dim
  transition-all duration-150
  focus: outline-none border-border-bright ring-1 ring-prism-blue/25
  error: border-noise ring-noise/25
  If leftIcon: pl-10

Left icon: absolute left-3 top-1/2 -translate-y-1/2 text-text-muted w-4 h-4
Right slot: absolute right-3 (for things like clear button, eye toggle)

Error: text-noise text-xs font-body flex items-center gap-1 mt-1
       [AlertCircle icon 12px] "{error message}"
Hint:  text-text-muted text-xs font-body mt-1
```

### Skeleton.jsx

```
Shimmer animation:
  background: linear-gradient(90deg, #0F2040 25%, #163058 50%, #0F2040 75%)
  background-size: 200% 100%
  animation: shimmer 2s linear infinite

MarketCardSkeleton:
  Mocks MarketCard layout — top row (title rect + score circle), data pills, bottom row
  Height: ~180px, rounded-xl

TrackerCardSkeleton:
  Mocks TrackerCard — taller due to more sections, ~200px

StatSkeleton: Simple rect block
```

### EmptyState.jsx

```
Props: icon (Lucide component), title, message, action {label, onClick}

Centered: py-16 flex flex-col items-center gap-3 text-center

Icon: w-10 h-10 text-text-muted (passed as Lucide component)
Title: font-heading font-semibold text-text-secondary text-base
Message: font-body text-sm text-text-muted max-w-[280px]
Action (optional): <Button variant="ghost" size="sm"> {action.label} </Button>
```

### Toast.jsx

```
Fixed position: top-4 right-4 (desktop) / bottom-[76px] left-4 right-4 (mobile, above bottom nav)
z-[9000]
max-w: 360px desktop

Variants:
  success: bg-informed-bg border border-informed/40 text-informed
  error:   bg-noise-bg border border-noise/40 text-noise
  info:    bg-navy-mid border border-border text-text-primary

Structure: flex items-start gap-3 px-4 py-3 rounded-xl shadow-modal
  Icon (CheckCircle / XCircle / Info) 16px
  Message: font-body text-sm text-text-primary (or variant color)
  Close (X, 14px) right-aligned, onClick → dismiss

GSAP:
  Enter: fromTo {opacity:0, x:20} → {opacity:1, x:0, duration:0.3, ease:'power2.out'}
  Exit:  to {opacity:0, x:20, duration:0.25, ease:'power2.in'}
  Auto-dismiss after 4000ms

Toast queue: managed via a context (ToastContext.jsx)
  const { showToast } = useToast()
  showToast({ type: 'success', message: 'Market added to Tracker' })
```

---

## 15. ANIMATION & MOTION SYSTEM

### Core Principles

1. **Purposeful** — every animation conveys state, reveals information, or guides attention. No decoration for decoration's sake.
2. **Fast** — interaction feedback: 150–200ms. Reveals and entrances: 300–600ms. Never slow.
3. **Non-blocking** — animation never prevents interaction. No waiting for animations to finish before clicking again.
4. **Respectful** — wrap all GSAP timelines in a `prefersReducedMotion` check:
   ```js
   const prefersReduced = window.matchMedia(
     "(prefers-reduced-motion: reduce)",
   ).matches;
   if (!prefersReduced) {
     /* run GSAP */
   }
   ```
5. **Cleanup always** — every GSAP timeline/tween created in `useEffect` must be killed in the cleanup function.

---

### GSAP Plugin Setup

```js
// src/main.jsx or a dedicated src/lib/gsap.js
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ScrollToPlugin } from "gsap/ScrollToPlugin";

gsap.registerPlugin(ScrollTrigger, ScrollToPlugin);

// Global GSAP defaults
gsap.defaults({
  ease: "power2.out",
  duration: 0.35,
});
```

---

### Animation Catalog

| Element               | Trigger                 | GSAP Config                                                                                              |
| --------------------- | ----------------------- | -------------------------------------------------------------------------------------------------------- |
| Page mount (any page) | On mount                | `fromTo(page, {opacity:0, y:8}, {opacity:1, y:0, duration:0.3})`                                         |
| Card grid entrance    | On mount                | `fromTo(cards, {opacity:0, y:16}, {opacity:1, y:0, stagger:0.06, duration:0.3})`                         |
| Section reveal        | ScrollTrigger (top 82%) | `fromTo(section, {opacity:0, y:20}, {opacity:1, y:0, duration:0.45})`                                    |
| ScoreBadge ring       | On mount                | SVG stroke-dashoffset: full → final, 0.8s ease-out                                                       |
| ScoreBadge on update  | Score changes           | `fromTo(el, {scale:1.15}, {scale:1, duration:0.4, ease:'back.out(2)'})`                                  |
| Score number count-up | On mount                | `gsap.to(el, {textContent: score, snap:1, duration:0.9})`                                                |
| Factor bars           | On mount                | `fromTo(bar, {scaleX:0}, {scaleX:1, duration:0.5, stagger:0.08, transformOrigin:'left'})`                |
| Arc gauge draw        | On mount                | SVG stroke-dashoffset animation, 0.9s ease-out                                                           |
| Probability line draw | On mount                | D3 path stroke-dashoffset, 1.0s ease-out                                                                 |
| OTP box shake         | On error                | `gsap.fromTo(boxes, {x:0}, {x:[-5,5,-4,4,-2,2,0], duration:0.35, stagger:0.02})`                         |
| Input error shake     | On validation fail      | `gsap.fromTo(input, {x:0}, {x:[-6,6,-4,4,-2,2,0], duration:0.4})`                                        |
| Toast enter           | On show                 | `fromTo(toast, {opacity:0, x:20}, {opacity:1, x:0, duration:0.3})`                                       |
| Toast exit            | On dismiss              | `to(toast, {opacity:0, x:20, duration:0.25})`                                                            |
| TrackerCard remove    | On remove               | `to(card, {height:0, opacity:0, marginBottom:0, padding:0, duration:0.35, ease:'power2.in'})`            |
| Alert banner enter    | On alert                | `fromTo(banner, {y:'-100%'}, {y:'0%', duration:0.4, ease:'power3.out'})`                                 |
| Alert banner exit     | On dismiss              | `to(banner, {y:'-100%', duration:0.3, ease:'power2.in'})`                                                |
| Modal/dropdown enter  | On open                 | `fromTo(el, {opacity:0, y:-8, scale:0.96}, {opacity:1, y:0, scale:1, duration:0.18, ease:'power2.out'})` |
| Track success         | On track                | Button → "✓ Tracked": button opacity 0, label fades in from x:-8                                         |
| Landing hero text     | On mount                | Stagger fromTo {opacity:0, y:20} → {opacity:1, y:0}, 0.12s stagger                                       |
| Loader letters        | Loader phase            | `fromTo(letters, {opacity:0, y:10}, {opacity:1, y:0, stagger:0.08})`                                     |
| Nav underline         | On route change         | `gsap.to(underline, {x:newX, width:newWidth, duration:0.25})`                                            |
| AI text reveal        | On render               | Word-by-word opacity stagger, 0.04s each                                                                 |

---

### ScrollTrigger Standard Setup

```js
// Used inside useEffect for all landing page sections
useEffect(() => {
  const ctx = gsap.context(() => {
    gsap.fromTo(
      ".reveal-item",
      { opacity: 0, y: 20 },
      {
        opacity: 1,
        y: 0,
        duration: 0.45,
        stagger: 0.1,
        scrollTrigger: {
          trigger: sectionRef.current,
          start: "top 82%",
          once: true, // don't re-trigger on scroll back up
        },
      },
    );
  }, sectionRef);

  return () => ctx.revert(); // cleans up all animations inside this context
}, []);
```

---

## 16. API INTEGRATION & COOKIE AUTH

### Axios Instance

**File:** `src/lib/api.js`

**Main Endpoint:** `https://prism-60b21aab4083.herokuapp.com/api/v1`

```js
import axios from "axios";

const api = axios.create({
  baseURL: "https://prism-60b21aab4083.herokuapp.com/api/v1",
  withCredentials: true, // ← CRITICAL: sends httpOnly session cookies
  headers: { "Content-Type": "application/json" },
  timeout: 15_000,
});

// Global 401 handler — session expired or not authenticated
api.interceptors.response.use(
  (res) => res,
  (err) => {
    // If not on an auth page and we get a 401, the session is dead
    if (err.response?.status === 401 && !window.location.pathname.startsWith('/auth')) {
      window.location.href = "/auth/login";
    }
    return Promise.reject(err);
  },
);

export default api;
```

---

### Auth Hook

```js
// src/hooks/useAuth.js
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../lib/api";

// Validates session cookie with backend
export function useAuth() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["session"],
    queryFn: () => api.get("/auth/me").then((r) => r.data),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
  return {
    user: data?.data ?? null,
    isAuthenticated: !!data?.data,
    isLoading,
    isError,
  };
}
```

### Auth Flow API Calls

```js
// SignupPage:
api.post("/auth/signup", { email, password, confirm_password });
// → returns { success: true, data: { uid: "..." } }

// OTPPage (Verification):
api.post("/auth/verify-otp", { uid, otp, otp_type: type });
// → If signup: returns { success: true }. 
// → If forgotpassword: returns { success: true, data: { reset_token: "..." } }

// LoginPage:
api.post("/auth/login", { email, password });
// → Sets cookies, returns { success: true, data: { ...user } }

// Logout:
api.post("/auth/logout");
// → server clears cookies, returns 200
```

### No localStorage Rule

Audit checklist — none of these should appear anywhere in the codebase:

- `localStorage`
- `sessionStorage`
- `document.cookie` (client-side cookie read/write — cookies are httpOnly, JS cannot read them)
- Token strings in any `useState` or component-level variable

All ephemeral state: `useState` inside components.
All server cache: TanStack Query in-memory.
Auth: server-side httpOnly cookie only.

### TanStack Query Global Config

```js
// src/main.jsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
});
```

---

## 17. RESPONSIVE BREAKPOINTS & MOBILE RULES

```
xs:  0–479px    Samsung Galaxy S8, iPhone SE
sm:  480–639px  Standard mobile
md:  640–767px  Large mobile, landscape
lg:  768–1023px Tablet, small laptop
xl:  1024–1279px Laptop — full layout
2xl: 1280px+    Desktop — landing hero cards visible
```

### Mobile-First Rules Per Page

**Landing Page:**

- Hero text: `text-center` mobile → `text-left` lg+
- Floating card preview: `hidden 2xl:block`
- Three.js canvas: full screen both, but reduce scene complexity (fewer particles) on mobile via width check
- Section grids: `grid-cols-1 md:grid-cols-2 xl:grid-cols-4`
- Navbar: hide center links below `md`, reduce to single "Get Access" CTA

**Auth Pages:**

- Card: `max-w-[420px] w-full` — full width on xs with `px-4`
- OTP boxes: `w-10 h-12 md:w-12 md:h-14`
- Background prism decoration: `hidden md:block`

**Discovery Page:**

- Market grid: `grid-cols-1 sm:grid-cols-2 xl:grid-cols-3`
- Search bar: full width always
- Tabs: full width, equal-split on mobile

**Tracker Page:**

- Card list: always single column, full width
- Alert banner: full width, slightly shorter on mobile (truncate market title)
- Sort control: dropdown collapses to icon-only on xs

**Analysis Page:**

- All sections: single column, full width — `max-w-4xl mx-auto`
- Hero panel: stacked (score gauge centered above signal summary)
- ScoreGauge size: `180px` desktop → `140px` mobile
- Two-column sections: stack on mobile
- Probability chart: `height: 200px` → `140px` mobile

**Touch Targets:**

- All buttons: minimum `min-h-[44px]` or wrapped in 44px container
- Bottom nav: `h-16` (64px) with icon+label — meets touch target requirement
- OTP boxes: `w-10 h-12` minimum — 40×48px meets touch guidelines
- Card tap areas: entire card surface

---

## 18. PAGE FLOW & BUTTON NAVIGATION MAP

### Full User Journey

```
                    ┌───────────────┐
                    │   LANDING  /  │
                    └───────┬───────┘
                            │
             ┌──────────────┴──────────────┐
             │ "Sign In" OR "Get Access"   │
             │ OR any auth CTA             │
             ▼                             │
    ┌─────────────────┐                   │
    │  EMAIL  /auth   │                   │
    │ Enter email     │                   │
    │ → Send OTP btn  │                   │
    └────────┬────────┘                   │
             │ On OTP sent                │
             ▼                            │
    ┌──────────────────────┐              │
    │  OTP  /auth/otp      │              │
    │ Enter 6-digit code   │              │
    │ → Verify & Sign In   │              │
    └──────────┬───────────┘              │
               │ On verified              │
               │ (cookie set)             │
               ▼                          │
    ┌──────────────────────────────────────────────────┐
    │              APP LAYOUT /app                      │
    │ [Topbar: Logo · Discover · Tracker · Pulse · ⊙]  │
    │ [Mobile Bottom Nav: Discover | Tracker]           │
    └──────────────────────────────────────────────────┘
               │
    ┌──────────┴──────────────────────────────┐
    ▼                                         ▼
┌────────────────┐                   ┌────────────────────┐
│  DISCOVERY     │                   │  TRACKER           │
│  /app          │                   │  /app/tracker      │
│                │                   │                    │
│  Search bar    │                   │  Alert banner      │
│  Tabs:         │                   │  (on score jump)   │
│   Trending     │                   │                    │
│   Popular      │                   │  TrackerCard list  │
│                │                   │                    │
│  MarketCard    │──── "+ Track" ──▶ │  (cards added here)│
│  grid          │                   │                    │
└───────┬────────┘                   └────────┬───────────┘
        │                                     │
        │ Click card                          │ Click card
        ▼                                     ▼
┌──────────────────────────────────────────────────────┐
│              MARKET ANALYSIS                          │
│              /app/markets/:marketId                   │
│                                                       │
│  Section 1: Main Signal (ScoreGauge + Summary)        │
│  Section 2: What's Happening (bars + prob chart)      │
│  Section 3: Smart Money (order pattern + breakdown)   │
│  Section 4: Trap Analysis                             │
│  Section 5: Momentum (volume chart + verdict)         │
│  Section 6: AI Interpretation (if INFORMED_MOVE)      │
│  Section 7: Action Guidance + "View on Source" btn    │
└──────────────────────────────────────────────────────┘
```

---

### Complete Button → Action Map

| Page                | Element                              | Action                                      | Destination / Effect                       |
| ------------------- | ------------------------------------ | ------------------------------------------- | ------------------------------------------ |
| Landing Navbar      | "Sign In"                            | navigate                                    | `/auth/login`                              |
| Landing Navbar      | "Get Access"                         | navigate                                    | `/auth/signup`                             |
| Landing Hero        | "Start Analyzing Markets"            | navigate                                    | `/auth/signup`                             |
| Landing Hero        | "See How It Works"                   | smooth scroll                               | `#how-it-works` on same page               |
| Landing CTA section | "Create Free Account"                | navigate                                    | `/auth/signup`                             |
| Landing CTA section | "Read the Methodology"               | smooth scroll                               | `#scoring`                                 |
| Landing Footer      | "Home"                               | navigate                                    | `/`                                        |
| Landing Footer      | "Discover"                           | navigate                                    | `/app`                                     |
| Landing Footer      | "Tracker"                            | navigate                                    | `/app/tracker`                             |
| SignupPage          | "Get Started" / "Sign Up"            | POST `/auth/signup` → navigate              | `/auth/otp?email=...&uid=...`              |
| LoginPage           | "Sign In"                            | POST `/auth/login` → navigate               | `/app`                                     |
| OTPPage             | "← Back"                             | navigate                                    | `/auth/signup`                             |
| OTPPage             | 6th digit entry                      | auto-trigger verify                         | POST `/auth/verify-otp`                    |
| OTPPage             | "Verify Account"                     | POST `/auth/verify-otp` → navigate          | `/auth/login`                              |
| OTPPage             | "Resend" (after countdown)           | POST `/auth/resend-otp`                     | resets countdown, shows toast              |
| Topbar              | PrismLogo                            | navigate                                    | `/app`                                     |
| Topbar              | "Discover" nav link                  | navigate                                    | `/app`                                     |
| Topbar              | "Tracker" nav link                   | navigate                                    | `/app/tracker`                             |
| Topbar              | User avatar                          | toggle                                      | opens user dropdown                        |
| Topbar dropdown     | "Sign Out"                           | POST `/auth/logout` → navigate              | `/`                                        |
| Mobile Bottom Nav   | "Discover" tab                       | navigate                                    | `/app`                                     |
| Mobile Bottom Nav   | "Tracker" tab                        | navigate                                    | `/app/tracker`                             |
| Discovery           | Search input clear (×)               | setState                                    | clears query, shows tabs                   |
| Discovery           | Tab "Trending Signals"               | setState + query                            | refetches `/markets?tab=trending`          |
| Discovery           | Tab "Popular Markets"                | setState + query                            | refetches `/markets?tab=popular`           |
| Discovery           | MarketCard (anywhere except button)  | navigate                                    | `/app/markets/${market.id}`                |
| Discovery           | "+ Track Market" button              | POST `/tracker/${market.id}`                | card updates to "✓ Tracked", toast success |
| Tracker             | "Manage" text button                 | setState                                    | toggles removeMode on all cards            |
| Tracker             | Alert banner "View →"                | navigate                                    | `/app/markets/${market.id}`                |
| Tracker             | Alert banner dismiss (×)             | setState                                    | dismisses banner                           |
| Tracker             | TrackerCard (anywhere except remove) | navigate                                    | `/app/markets/${market.id}`                |
| Tracker             | "Remove" (in remove mode, confirmed) | DELETE `/tracker/${market.id}`              | card animates out, toast                   |
| Tracker             | "Keep" (in remove mode)              | setState                                    | cancels remove overlay                     |
| Tracker             | Sort dropdown                        | setState                                    | sorts card list client-side                |
| Tracker             | "Discover Markets" (empty state)     | navigate                                    | `/app`                                     |
| Analysis            | "← Back" / breadcrumb                | router.history.back()                       | previous page                              |
| Analysis            | "+ Track Market" button              | POST `/tracker/${market.id}`                | button → "✓ Tracked"                       |
| Analysis            | "✓ Tracked" → confirm remove         | DELETE `/tracker/${market.id}`              | button → "+ Track Market"                  |
| Analysis            | "View on Polymarket / Bayse"         | window.open                                 | external URL in new tab                    |

---

### Implementation Notes for AI Agent

**Build order:**

1. Design tokens (CSS vars + Tailwind config) + fonts
2. Brand components: PrismLogo → PrismLoader → Button + Spinner
3. Auth pages: SignupPage → OTPPage → LoginPage (establish cookie flow)
4. App layout: Topbar → MobileNav → AppLayout
5. Shared UI: ScoreBadge, ClassificationChip, DirectionArrow, SourceBadge, MarketCard, TrackerCard
6. Discovery page (no chart dependencies, tests the market API)
7. Tracker page (tests polling + mutation + animation)
8. Market Analysis page (most complex — save for last)
9. Charts: ProbabilityLine, ScoreGauge, FactorBars, VolumeSpike
10. Landing page (Three.js scene, GSAP ScrollTrigger, landing components)

**Non-negotiable rules:**

- `withCredentials: true` on every Axios request — never remove this
- Zero localStorage or sessionStorage — all state is React state or TanStack Query cache
- All GSAP inside `useEffect` with cleanup (`tl.kill()` or `ctx.revert()`)
- Three.js: always call `renderer.dispose()` and cancel `animationFrameId` in cleanup
- All interactive elements: `min-h-[44px]` for touch targets
- Error boundaries on each page-level component
- `VITE_API_URL` is the only env variable — never commit secrets

**Cookie auth mental model:**
The browser sends the httpOnly cookie automatically on every request to the API domain because `withCredentials: true` is set. The client-side code never reads the cookie. The only way the client knows a user is logged in is by calling `GET /auth/me` — if it returns a user, they're in. If it returns 401, the interceptor redirects to `/auth`. That's the entire auth system from the frontend's perspective.

**D3 + React pattern:**
Use D3 only for calculations (scales, paths, arc geometry). React renders the actual SVG DOM. Never use `d3.select` on React-rendered elements — it breaks React's reconciliation.

**OTP auto-submit UX:**
When the 6th box is filled, trigger submission immediately (no button click required). This is faster and more delightful. The manual "Verify & Sign In" button is the fallback for users who autofilled or pasted.

---

_End of Prism Frontend Specification — V2.0_
_Confidential — Prism Hackathon Team_
_Product structure: Landing → Signup → OTP → Login → Discover → Tracker → Market Analysis_
