"use client";

import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("satprep-theme", next ? "dark" : "light");
    } catch {}
  }

  return (
    <button
      onClick={toggle}
      aria-label={next_label(dark)}
      title={next_label(dark)}
      className="grid h-10 w-10 place-items-center rounded-full border-2 border-line bg-surface shadow-flat-sm transition-transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-none"
    >
      <span className="text-lg leading-none">{dark ? "☾" : "☀"}</span>
    </button>
  );
}

function next_label(dark: boolean) {
  return dark ? "Mudar para o modo claro" : "Mudar para o modo escuro";
}
