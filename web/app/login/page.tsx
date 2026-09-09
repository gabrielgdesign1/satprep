"use client";

import { useState } from "react";
import { supabaseBrowser } from "@/lib/supabase-browser";
import { BackdropShapes, Logo } from "@/components/Doodles";
import ThemeToggle from "@/components/ThemeToggle";

type Mode = "password" | "magic";

export default function LoginPage() {
  const [mode, setMode] = useState<Mode>("password");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(
    null
  );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    const supabase = supabaseBrowser();

    try {
      if (mode === "magic") {
        const { error } = await supabase.auth.signInWithOtp({
          email,
          options: { emailRedirectTo: `${location.origin}/auth/callback` },
        });
        if (error) throw error;
        setMsg({
          kind: "ok",
          text: "Link enviado. Abra o e-mail neste dispositivo para entrar.",
        });
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) {
          // primeira vez: cria a conta e ja entra
          if (error.message.toLowerCase().includes("invalid login")) {
            const { error: upErr } = await supabase.auth.signUp({
              email,
              password,
            });
            if (upErr) throw upErr;
            location.href = "/";
            return;
          }
          throw error;
        }
        location.href = "/";
      }
    } catch (err: any) {
      setMsg({ kind: "err", text: err?.message ?? "Nao deu para entrar." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="relative min-h-dvh">
      <BackdropShapes tone="mix" />

      <div className="absolute right-5 top-5">
        <ThemeToggle />
      </div>

      <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-5 py-16">
        <div className="mb-7 flex items-center gap-3">
          <Logo className="h-12 w-12" />
          <div>
            <h1 className="font-display text-3xl font-black leading-none">
              SAT Practice
            </h1>
            <p className="mt-1 text-sm text-muted">
              Questoes oficiais, por topico.
            </p>
          </div>
        </div>

        <form
          onSubmit={submit}
          className="rounded-2xl border-2 border-line bg-surface p-6 shadow-flat-lg"
        >
          <div className="mb-5 grid grid-cols-2 gap-2 rounded-xl border-2 border-line bg-sunken p-1">
            {(["password", "magic"] as Mode[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => {
                  setMode(m);
                  setMsg(null);
                }}
                className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${
                  mode === m
                    ? "bg-ink text-paper"
                    : "text-muted hover:text-ink"
                }`}
              >
                {m === "password" ? "Senha" : "Link por e-mail"}
              </button>
            ))}
          </div>

          <label className="block text-sm font-semibold" htmlFor="email">
            E-mail
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1.5 w-full rounded-xl border-2 border-line bg-paper px-3 py-2.5 text-ink outline-none"
            placeholder="voce@exemplo.com"
          />

          {mode === "password" && (
            <>
              <label
                className="mt-4 block text-sm font-semibold"
                htmlFor="password"
              >
                Senha
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={6}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1.5 w-full rounded-xl border-2 border-line bg-paper px-3 py-2.5 text-ink outline-none"
                placeholder="minimo de 6 caracteres"
              />
              <p className="mt-2 text-xs text-muted">
                Na primeira vez, a conta e criada com esses dados.
              </p>
            </>
          )}

          <button
            type="submit"
            disabled={busy}
            className="mt-6 w-full rounded-xl border-2 border-line bg-accent px-4 py-3 font-display text-lg font-bold text-ink shadow-flat transition-transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-none disabled:opacity-60"
          >
            {busy ? "Entrando…" : mode === "magic" ? "Enviar link" : "Entrar"}
          </button>

          {msg && (
            <p
              role="status"
              className={`mt-4 rounded-xl border-2 px-3 py-2 text-sm ${
                msg.kind === "ok"
                  ? "border-right bg-right-soft text-ink"
                  : "border-wrong bg-wrong-soft text-ink"
              }`}
            >
              {msg.text}
            </p>
          )}
        </form>

        <p className="mt-5 text-center text-xs text-muted">
          Seu progresso fica salvo na conta e acompanha voce em qualquer
          dispositivo.
        </p>
      </div>
    </main>
  );
}
