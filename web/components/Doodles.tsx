"use client";

/**
 * Ilustracoes 2D do app. Sao SVG inline (sem lib, sem imagem externa) para
 * herdarem a cor do tema e ficarem nitidas em qualquer zoom.
 */

export function BackdropShapes({ tone = "math" }: { tone?: "math" | "rw" | "mix" }) {
  const a = tone === "rw" ? "var(--rw)" : "var(--math)";
  const b = tone === "mix" ? "var(--rw)" : "var(--accent)";
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <svg
        className="absolute -left-24 -top-24 h-80 w-80 animate-float opacity-[0.13]"
        viewBox="0 0 200 200"
        style={{ animationDelay: "-2s" }}
      >
        <circle cx="100" cy="100" r="88" fill={a} />
      </svg>
      <svg
        className="absolute -right-20 top-40 h-64 w-64 animate-float opacity-[0.12]"
        viewBox="0 0 200 200"
      >
        <rect x="20" y="20" width="160" height="160" rx="28" fill={b} transform="rotate(14 100 100)" />
      </svg>
      <svg
        className="absolute bottom-[-60px] left-1/3 h-72 w-72 animate-float opacity-[0.10]"
        viewBox="0 0 200 200"
        style={{ animationDelay: "-5s" }}
      >
        <polygon points="100,18 182,168 18,168" fill={a} />
      </svg>
      {/* grade de pontos, como papel milimetrado */}
      <svg className="absolute inset-0 h-full w-full opacity-[0.35]">
        <defs>
          <pattern id="dots" width="26" height="26" patternUnits="userSpaceOnUse">
            <circle cx="1.5" cy="1.5" r="1.5" fill="var(--muted)" opacity="0.28" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#dots)" />
      </svg>
    </div>
  );
}

/** Marca do app: um lapis cruzando um compasso, bem chapado. */
export function Logo({ className = "h-9 w-9" }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={className} aria-hidden>
      <rect
        x="3" y="3" width="42" height="42" rx="12"
        fill="var(--accent)" stroke="var(--line)" strokeWidth="2.5"
      />
      <path
        d="M15 33 L15 27 L29 13 L35 19 L21 33 Z"
        fill="var(--surface)" stroke="var(--line)" strokeWidth="2.5"
        strokeLinejoin="round"
      />
      <path d="M29 13 L35 19" stroke="var(--line)" strokeWidth="2.5" />
      <circle cx="17" cy="31" r="1.8" fill="var(--line)" />
    </svg>
  );
}

export function MathArt({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 100" className={className} aria-hidden>
      <rect x="6" y="6" width="108" height="88" rx="10"
            fill="var(--math-soft)" stroke="var(--line)" strokeWidth="3" />
      {[26, 46, 66, 86].map((x) => (
        <line key={x} x1={x} y1="12" x2={x} y2="88" stroke="var(--line)" strokeWidth="1" opacity="0.28" />
      ))}
      {[28, 48, 68].map((y) => (
        <line key={y} x1="12" y1={y} x2="108" y2={y} stroke="var(--line)" strokeWidth="1" opacity="0.28" />
      ))}
      <path d="M14 82 Q46 6 66 52 T108 20"
            fill="none" stroke="var(--math)" strokeWidth="4.5" strokeLinecap="round" />
      <circle cx="66" cy="52" r="5" fill="var(--surface)" stroke="var(--line)" strokeWidth="3" />
    </svg>
  );
}

export function RwArt({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 100" className={className} aria-hidden>
      <rect x="10" y="8" width="94" height="84" rx="8"
            fill="var(--rw-soft)" stroke="var(--line)" strokeWidth="3" />
      <line x1="34" y1="12" x2="34" y2="88" stroke="var(--line)" strokeWidth="2" opacity="0.4" />
      {[26, 40, 54, 68].map((y, i) => (
        <line key={y} x1="44" y1={y} x2={i % 2 ? 92 : 84} y2={y}
              stroke="var(--rw)" strokeWidth="5" strokeLinecap="round" />
      ))}
      <line x1="44" y1="82" x2="66" y2="82"
            stroke="var(--line)" strokeWidth="5" strokeLinecap="round" opacity="0.55" />
    </svg>
  );
}

/** Estado vazio: nada mais a praticar neste filtro. */
export function EmptyArt({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 100" className={className} aria-hidden>
      <circle cx="60" cy="52" r="34" fill="var(--right-soft)"
              stroke="var(--line)" strokeWidth="3" />
      <path d="M45 53 l10 11 l21 -24" fill="none" stroke="var(--right)"
            strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M22 22 l6 6 M98 22 l-6 6 M18 74 l7 3 M102 74 l-7 3"
            stroke="var(--accent)" strokeWidth="3.5" strokeLinecap="round" />
    </svg>
  );
}
