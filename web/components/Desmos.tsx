"use client";

import { useEffect, useRef, useState } from "react";

declare global {
  interface Window {
    Desmos?: any;
  }
}

const DESMOS_VERSION = "v1.12";

/**
 * Calculadora grafica Desmos, embutida so nas questoes de Math.
 * O script e carregado sob demanda, na primeira vez que a calculadora e
 * aberta -- nao pesa nas telas de Reading & Writing.
 */
export default function Desmos() {
  const host = useRef<HTMLDivElement>(null);
  const calc = useRef<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const key = process.env.NEXT_PUBLIC_DESMOS_API_KEY;
    if (!key) {
      setError("Falta NEXT_PUBLIC_DESMOS_API_KEY no ambiente.");
      return;
    }

    let cancelled = false;

    function boot() {
      if (cancelled || !host.current || calc.current || !window.Desmos) return;
      calc.current = window.Desmos.GraphingCalculator(host.current, {
        expressions: true,
        settingsMenu: false,
        zoomButtons: true,
        border: false,
      });
    }

    if (window.Desmos) {
      boot();
    } else {
      const src = `https://www.desmos.com/api/${DESMOS_VERSION}/calculator.js?apiKey=${key}`;
      let tag = document.querySelector<HTMLScriptElement>(
        `script[data-desmos="1"]`
      );
      if (!tag) {
        tag = document.createElement("script");
        tag.src = src;
        tag.async = true;
        tag.dataset.desmos = "1";
        document.head.appendChild(tag);
      }
      tag.addEventListener("load", boot);
      tag.addEventListener("error", () =>
        setError("Nao deu para carregar a calculadora Desmos.")
      );
    }

    return () => {
      cancelled = true;
      if (calc.current) {
        calc.current.destroy();
        calc.current = null;
      }
    };
  }, []);

  return (
    <div className="mt-3 overflow-hidden rounded-2xl border-2 border-line shadow-flat">
      {error ? (
        <p className="bg-wrong-soft px-4 py-3 text-sm">{error}</p>
      ) : (
        <div ref={host} className="h-[420px] w-full bg-white" />
      )}
    </div>
  );
}
