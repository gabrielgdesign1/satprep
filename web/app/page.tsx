import Link from "next/link";
import { supabaseServer } from "@/lib/supabase-server";
import { BackdropShapes, Logo, MathArt, RwArt } from "@/components/Doodles";
import ThemeToggle from "@/components/ThemeToggle";
import SignOut from "@/components/SignOut";

export const dynamic = "force-dynamic";

/** Primeiro nivel: escolher Reading & Writing ou Math. */
export default async function HomePage() {
  const supabase = supabaseServer();

  const { data: rows } = await supabase
    .from("v_skill_progress")
    .select("section, total, solved");

  const tally = { reading_writing: { t: 0, s: 0 }, math: { t: 0, s: 0 } };
  for (const r of rows ?? []) {
    const k = r.section as "reading_writing" | "math";
    if (!tally[k]) continue;
    tally[k].t += r.total ?? 0;
    tally[k].s += r.solved ?? 0;
  }

  const cards = [
    {
      href: "/practice/reading_writing",
      title: "Reading & Writing",
      blurb: "Craft and Structure, Information and Ideas, Expression of Ideas e Conventions.",
      art: <RwArt className="h-28 w-32" />,
      accent: "var(--rw)",
      soft: "var(--rw-soft)",
      ...tally.reading_writing,
    },
    {
      href: "/practice/math",
      title: "Math",
      blurb: "Algebra, Advanced Math, Problem-Solving and Data Analysis, Geometry and Trigonometry.",
      art: <MathArt className="h-28 w-32" />,
      accent: "var(--math)",
      soft: "var(--math-soft)",
      ...tally.math,
    },
  ];

  return (
    <main className="relative min-h-dvh">
      <BackdropShapes tone="mix" />

      <header className="mx-auto flex max-w-4xl items-center justify-between px-5 pt-6">
        <div className="flex items-center gap-3">
          <Logo className="h-10 w-10" />
          <span className="font-display text-xl font-bold">SAT Practice</span>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <SignOut />
        </div>
      </header>

      <div className="mx-auto max-w-4xl px-5 pb-20 pt-12">
        <h1 className="max-w-[16ch] font-display text-4xl font-black leading-[1.05] sm:text-5xl">
          O que voce quer praticar hoje?
        </h1>
        <p className="mt-3 max-w-[52ch] text-muted">
          Escolha a secao, depois o topico. As questoes vem das provas oficiais
          do College Board.
        </p>

        <div className="mt-9 grid gap-5 sm:grid-cols-2">
          {cards.map((c) => {
            const pct = c.t ? Math.round((c.s / c.t) * 100) : 0;
            return (
              <Link
                key={c.href}
                href={c.href}
                className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border-2 border-line bg-surface p-6 shadow-flat-lg transition-transform hover:-translate-y-1 active:translate-y-0 active:shadow-flat"
              >
                <div
                  aria-hidden
                  className="absolute -right-8 -top-8 h-32 w-32 rounded-full opacity-40"
                  style={{ background: c.soft }}
                />
                <div className="relative">
                  <div className="mb-4">{c.art}</div>
                  <h2
                    className="font-display text-2xl font-bold"
                    style={{ color: c.accent }}
                  >
                    {c.title}
                  </h2>
                  <p className="mt-2 text-sm leading-relaxed text-muted">
                    {c.blurb}
                  </p>
                </div>

                <div className="relative mt-6">
                  <div className="flex items-baseline justify-between text-sm">
                    <span className="font-semibold">
                      {c.s} de {c.t} resolvidas
                    </span>
                    <span className="font-mono text-xs text-muted">{pct}%</span>
                  </div>
                  <div className="mt-2 h-3 overflow-hidden rounded-full border-2 border-line bg-paper">
                    <div
                      className="h-full transition-[width]"
                      style={{ width: `${pct}%`, background: c.accent }}
                    />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </main>
  );
}
