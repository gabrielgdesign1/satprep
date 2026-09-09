"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState, useTransition } from "react";
import { supabaseBrowser } from "@/lib/supabase-browser";
import type { Difficulty, Section, SkillProgress } from "@/lib/types";

const DIFFS: { key: string; label: string }[] = [
  { key: "all", label: "Todas" },
  { key: "easy", label: "Facil" },
  { key: "medium", label: "Media" },
  { key: "hard", label: "Dificil" },
  { key: "unrated", label: "Sem nivel" },
];

type Agg = {
  skill_id: string;
  skill_code: string;
  skill_name: string;
  skill_order: number;
  total: number;
  solved: number;
};

export default function TopicTree({
  rows,
  section,
  difficulty,
  accent,
}: {
  rows: SkillProgress[];
  section: Section;
  difficulty: string;
  accent: string;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [resetting, setResetting] = useState<string | null>(null);

  // As linhas vem quebradas por dificuldade; agrega conforme o filtro ativo.
  const domains = useMemo(() => {
    const keep = rows.filter(
      (r) => difficulty === "all" || r.difficulty === difficulty
    );
    const byDomain = new Map<
      string,
      { name: string; order: number; skills: Map<string, Agg> }
    >();

    for (const r of keep) {
      if (!byDomain.has(r.domain_id)) {
        byDomain.set(r.domain_id, {
          name: r.domain_name,
          order: r.domain_order,
          skills: new Map(),
        });
      }
      const d = byDomain.get(r.domain_id)!;
      const cur = d.skills.get(r.skill_id) ?? {
        skill_id: r.skill_id,
        skill_code: r.skill_code,
        skill_name: r.skill_name,
        skill_order: r.skill_order,
        total: 0,
        solved: 0,
      };
      cur.total += r.total ?? 0;
      cur.solved += r.solved ?? 0;
      d.skills.set(r.skill_id, cur);
    }

    return [...byDomain.values()]
      .sort((a, b) => a.order - b.order)
      .map((d) => ({
        ...d,
        skills: [...d.skills.values()].sort(
          (a, b) => a.skill_order - b.skill_order
        ),
      }));
  }, [rows, difficulty]);

  function setDifficulty(key: string) {
    const qs = key === "all" ? "" : `?d=${key}`;
    startTransition(() => router.push(`/practice/${section}${qs}`));
  }

  async function reset(skill: Agg) {
    if (
      !confirm(
        `Reiniciar o progresso de "${skill.skill_name}"?\n\n` +
          `As ${skill.solved} questoes resolvidas voltam a aparecer. ` +
          `Seu historico de respostas nao e apagado.`
      )
    )
      return;

    setResetting(skill.skill_id);
    const supabase = supabaseBrowser();
    const { error } = await supabase.rpc("reset_skill_progress", {
      p_skill_id: skill.skill_id,
      p_difficulty: difficulty === "all" ? null : (difficulty as Difficulty),
    });
    setResetting(null);
    if (error) alert(`Nao deu para reiniciar: ${error.message}`);
    else router.refresh();
  }

  return (
    <>
      <div className="mt-7 flex flex-wrap items-center gap-2">
        <span className="mr-1 text-xs font-bold uppercase tracking-wider text-muted">
          Dificuldade
        </span>
        {DIFFS.map((d) => {
          const on = d.key === difficulty;
          return (
            <button
              key={d.key}
              onClick={() => setDifficulty(d.key)}
              aria-pressed={on}
              className={`rounded-full border-2 border-line px-3.5 py-1.5 text-sm font-semibold transition-transform hover:-translate-y-0.5 ${
                on
                  ? "bg-ink text-paper shadow-none"
                  : "bg-surface shadow-flat-sm"
              }`}
            >
              {d.label}
            </button>
          );
        })}
      </div>

      <p className="mt-2 text-xs text-muted">
        As provas oficiais nao trazem rotulo de dificuldade, por isso as
        questoes ficam em <b>Sem nivel</b> — nada foi inventado.
      </p>

      <div
        className={`mt-7 space-y-6 ${pending ? "opacity-60" : ""}`}
        aria-busy={pending}
      >
        {domains.map((d) => (
          <section
            key={d.name}
            className="overflow-hidden rounded-2xl border-2 border-line bg-surface shadow-flat"
          >
            <h2
              className="border-b-2 border-line px-5 py-3 font-display text-lg font-bold"
              style={{ background: "var(--sunken)" }}
            >
              {d.name}
            </h2>

            <ul className="divide-y-2 divide-line/30">
              {d.skills.map((s: Agg) => {
                const done = s.total > 0 && s.solved >= s.total;
                const pct = s.total ? (s.solved / s.total) * 100 : 0;
                const empty = s.total === 0;

                return (
                  <li key={s.skill_id} className="flex items-center gap-3 px-5 py-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline gap-2">
                        <span className="truncate font-semibold">
                          {s.skill_name}
                        </span>
                        {done && (
                          <span className="shrink-0 rounded-full border border-right bg-right-soft px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-right">
                            completo
                          </span>
                        )}
                      </div>
                      <div className="mt-1.5 flex items-center gap-2.5">
                        <div className="h-2 w-32 overflow-hidden rounded-full border border-line/50 bg-paper">
                          <div
                            className="h-full"
                            style={{
                              width: `${pct}%`,
                              background: done ? "var(--right)" : accent,
                            }}
                          />
                        </div>
                        <span className="font-mono text-xs tabular-nums text-muted">
                          {s.solved}/{s.total}
                        </span>
                      </div>
                    </div>

                    {s.solved > 0 && (
                      <button
                        onClick={() => reset(s)}
                        disabled={resetting === s.skill_id}
                        title="Reiniciar o progresso deste topico"
                        className="shrink-0 rounded-lg border-2 border-line bg-surface px-2.5 py-1.5 text-xs font-semibold text-muted transition hover:text-ink disabled:opacity-50"
                      >
                        {resetting === s.skill_id ? "…" : "Reiniciar"}
                      </button>
                    )}

                    {empty ? (
                      <span className="shrink-0 rounded-lg border-2 border-dashed border-line/50 px-3 py-2 text-xs text-muted">
                        sem questoes
                      </span>
                    ) : (
                      <Link
                        href={`/practice/${section}/${s.skill_code}${
                          difficulty === "all" ? "" : `?d=${difficulty}`
                        }`}
                        className="shrink-0 rounded-lg border-2 border-line px-3.5 py-2 text-sm font-bold text-ink shadow-flat-sm transition-transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-none"
                        style={{ background: accent, color: "var(--paper)" }}
                      >
                        {done ? "Revisar" : "Praticar"}
                      </Link>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>
    </>
  );
}
