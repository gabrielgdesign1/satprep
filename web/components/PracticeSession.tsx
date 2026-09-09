"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useMemo, useState } from "react";
import { supabaseBrowser } from "@/lib/supabase-browser";
import Markdown from "@/components/Markdown";
import Desmos from "@/components/Desmos";
import type { Question } from "@/lib/types";

/**
 * Fluxo de resposta, exatamente nesta ordem:
 *
 *   1. O usuario escolhe uma alternativa (ou digita, no grid-in) e confirma.
 *   2. O app diz na hora apenas SE acertou ou errou -- sem revelar qual e a
 *      correta.
 *   3. Se errou, aparece "Mostrar resposta". So ao clicar nele e que a
 *      alternativa correta e a explicacao aparecem.
 *   4. "Proxima questao" fica disponivel o tempo todo, inclusive sem responder.
 *
 * Quem decide se a questao vira "resolvida" e a funcao record_attempt no
 * banco: acertou OU revelou. O cliente nunca grava progresso por conta.
 */

type Phase = "answering" | "wrong" | "correct" | "revealed";

export default function PracticeSession({
  questions,
  accent,
  backHref,
  skillName,
  domainName,
}: {
  questions: Question[];
  accent: string;
  backHref: string;
  skillName: string;
  domainName: string;
}) {
  const router = useRouter();
  const [idx, setIdx] = useState(0);
  const [phase, setPhase] = useState<Phase>("answering");
  const [picked, setPicked] = useState<string | null>(null);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [reveal, setReveal] = useState<null | {
    correct_choice: string | null;
    correct_answer_text: string | null;
    rationale_md: string | null;
    distractor_rationales: Record<string, string>;
  }>(null);
  const [showCalc, setShowCalc] = useState(false);
  const [solvedCount, setSolvedCount] = useState(0);

  const q = questions[idx];
  const isMath = q?.section === "math";
  const stimulusAsset = useMemo(
    () => q?.assets.find((a) => a.role === "stimulus") ?? null,
    [q]
  );

  const resetForNext = useCallback(() => {
    setPhase("answering");
    setPicked(null);
    setTyped("");
    setReveal(null);
  }, []);

  function next() {
    resetForNext();
    if (idx + 1 < questions.length) setIdx(idx + 1);
    else router.refresh(); // fim da fila: recarrega o que sobrou
  }

  async function submit() {
    if (busy) return;
    if (q.question_type === "multiple_choice" && !picked) return;
    if (q.question_type === "grid_in" && !typed.trim()) return;

    setBusy(true);
    const supabase = supabaseBrowser();
    const { data, error } = await supabase.rpc("record_attempt", {
      p_question_id: q.id,
      p_selected_choice: q.question_type === "multiple_choice" ? picked : null,
      p_typed_answer: q.question_type === "grid_in" ? typed.trim() : null,
      p_revealed: false,
    });
    setBusy(false);

    if (error) {
      alert(`Nao deu para registrar a resposta: ${error.message}`);
      return;
    }

    const ok = Array.isArray(data) ? data[0]?.is_correct : (data as any)?.is_correct;
    if (ok) {
      setPhase("correct");
      setSolvedCount((n) => n + 1);
      // acertou: pode ver a explicacao imediatamente
      await loadReveal(false);
    } else {
      setPhase("wrong");
    }
  }

  /** Busca gabarito e explicacao. So e chamado depois de acertar ou de o
   *  usuario pedir explicitamente -- nunca antes de responder. */
  async function loadReveal(markRevealed: boolean) {
    const supabase = supabaseBrowser();

    if (markRevealed) {
      const { error } = await supabase.rpc("record_attempt", {
        p_question_id: q.id,
        p_selected_choice: null,
        p_typed_answer: null,
        p_revealed: true,
      });
      if (error) {
        alert(`Nao deu para registrar: ${error.message}`);
        return;
      }
      setSolvedCount((n) => n + 1);
    }

    const { data } = await supabase
      .from("questions")
      .select(
        "correct_choice, correct_answer_text, rationale_md, distractor_rationales"
      )
      .eq("id", q.id)
      .single();

    if (data) {
      setReveal({
        correct_choice: data.correct_choice,
        correct_answer_text: data.correct_answer_text,
        rationale_md: data.rationale_md,
        distractor_rationales: (data.distractor_rationales ?? {}) as Record<
          string,
          string
        >,
      });
    }
    if (markRevealed) setPhase("revealed");
  }

  if (!q) return null;

  const answerShown = phase === "revealed" || phase === "correct";

  return (
    <div className="mx-auto max-w-3xl px-5 pb-28 pt-6">
      {/* trilha da sessao */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href={backHref}
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink"
        >
          <span aria-hidden>←</span> {domainName || "Topicos"}
        </Link>
        <div className="flex items-center gap-3 text-sm">
          <span className="font-mono tabular-nums text-muted">
            {idx + 1} / {questions.length}
          </span>
          {solvedCount > 0 && (
            <span className="rounded-full border-2 border-right bg-right-soft px-2.5 py-0.5 text-xs font-bold text-right">
              +{solvedCount} resolvidas
            </span>
          )}
        </div>
      </div>

      <h1 className="mt-2 font-display text-2xl font-bold" style={{ color: accent }}>
        {skillName}
      </h1>

      {/* barra de avanco da fila */}
      <div className="mt-3 h-2 overflow-hidden rounded-full border-2 border-line bg-surface">
        <div
          className="h-full transition-[width] duration-300"
          style={{
            width: `${((idx + (answerShown ? 1 : 0)) / questions.length) * 100}%`,
            background: accent,
          }}
        />
      </div>

      {/* ---------------- questao ---------------- */}
      <article className="mt-5 animate-pop rounded-2xl border-2 border-line bg-surface p-6 shadow-flat-lg sm:p-7">
        <div className="mb-4 flex flex-wrap items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-muted">
          <span className="rounded border border-line/50 px-2 py-0.5">
            Prova {q.test_number} · Modulo {q.module_number} · Q{q.question_number}
          </span>
          {q.difficulty === "unrated" ? (
            <span className="rounded border border-line/50 px-2 py-0.5">
              sem nivel
            </span>
          ) : (
            <span className="rounded border border-line/50 px-2 py-0.5">
              {q.difficulty}
            </span>
          )}
          {q.question_type === "grid_in" && (
            <span className="rounded border-2 border-accent bg-accent/15 px-2 py-0.5 text-ink">
              resposta digitada
            </span>
          )}
        </div>

        {q.stimulus_md && (
          <div className="mb-5 rounded-xl border-2 border-line/40 bg-sunken/60 p-4">
            <Markdown className="font-serif text-[15.5px] leading-relaxed">
              {q.stimulus_md}
            </Markdown>
          </div>
        )}

        {stimulusAsset && (
          <figure className="mb-5">
            <img
              src={stimulusAsset.storage_path}
              alt={stimulusAsset.alt_text ?? "Figura da questao"}
              className="mx-auto block max-h-[340px] w-auto max-w-full rounded-xl border-2 border-line bg-white object-contain p-1"
            />
          </figure>
        )}

        <Markdown className="font-serif text-lg font-semibold leading-relaxed">
          {q.prompt_md}
        </Markdown>

        {/* ---------------- alternativas ---------------- */}
        {q.question_type === "multiple_choice" ? (
          <ul className="mt-5 space-y-2.5">
            {q.choices.map((c) => {
              const isPicked = picked === c.label;
              const isRight = answerShown && reveal?.correct_choice === c.label;
              const isPickedWrong =
                isPicked && (phase === "wrong" || (answerShown && !isRight));

              let cls =
                "border-line bg-paper hover:-translate-y-0.5 hover:shadow-flat-sm";
              if (isRight) cls = "border-right bg-right-soft";
              else if (isPickedWrong) cls = "border-wrong bg-wrong-soft";
              else if (isPicked) cls = "border-line bg-sunken shadow-flat-sm";

              return (
                <li key={c.id}>
                  <button
                    type="button"
                    disabled={phase !== "answering"}
                    onClick={() => setPicked(c.label)}
                    aria-pressed={isPicked}
                    className={`flex w-full items-start gap-3 rounded-xl border-2 p-3.5 text-left transition-all disabled:cursor-default ${cls}`}
                  >
                    <span
                      className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full border-2 border-line font-display text-sm font-bold"
                      style={
                        isRight
                          ? { background: "var(--right)", color: "var(--paper)" }
                          : isPickedWrong
                          ? { background: "var(--wrong)", color: "var(--paper)" }
                          : isPicked
                          ? { background: "var(--ink)", color: "var(--paper)" }
                          : undefined
                      }
                    >
                      {c.label}
                    </span>

                    <span className="min-w-0 flex-1">
                      {c.is_graphic && c.asset_path ? (
                        <img
                          src={c.asset_path}
                          alt={`Alternativa ${c.label}`}
                          className="max-h-[230px] w-auto max-w-full rounded-lg border border-line/40 bg-white object-contain p-1"
                        />
                      ) : (
                        <Markdown className="font-serif text-[15.5px]">
                          {c.content_md}
                        </Markdown>
                      )}
                    </span>

                    {isRight && (
                      <span className="shrink-0 self-center text-xs font-bold uppercase tracking-wide text-right">
                        correta
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <div className="mt-5">
            <label
              htmlFor="gridin"
              className="text-xs font-bold uppercase tracking-wider text-muted"
            >
              Sua resposta
            </label>
            <input
              id="gridin"
              value={typed}
              disabled={phase !== "answering"}
              onChange={(e) => setTyped(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder="ex.: 77, 3/29, -1.5"
              inputMode="text"
              className="mt-1.5 w-full max-w-xs rounded-xl border-2 border-line bg-paper px-4 py-3 font-mono text-xl tabular-nums outline-none disabled:opacity-70"
            />
            <p className="mt-1.5 text-xs text-muted">
              Fracao e decimal equivalentes sao aceitos.
            </p>
          </div>
        )}

        {/* ---------------- veredito ---------------- */}
        {phase === "correct" && (
          <p className="mt-5 flex items-center gap-2 rounded-xl border-2 border-right bg-right-soft px-4 py-3 font-display text-lg font-bold">
            <span aria-hidden>✓</span> Certo!
          </p>
        )}

        {phase === "wrong" && (
          <div className="mt-5 animate-nudge rounded-xl border-2 border-wrong bg-wrong-soft px-4 py-3">
            <p className="flex items-center gap-2 font-display text-lg font-bold">
              <span aria-hidden>✗</span> Errado.
            </p>
            <p className="mt-1 text-sm text-muted">
              Tente de novo ou veja a resposta.
            </p>
          </div>
        )}

        {/* resposta do grid-in so aparece depois de revelada */}
        {answerShown && q.question_type === "grid_in" && reveal && (
          <p className="mt-4 rounded-xl border-2 border-right bg-right-soft px-4 py-3">
            <span className="text-xs font-bold uppercase tracking-wider text-muted">
              Resposta oficial
            </span>
            <span className="ml-2 font-mono text-xl font-bold">
              {reveal.correct_answer_text}
            </span>
          </p>
        )}

        {/* ---------------- explicacao ---------------- */}
        {answerShown && reveal?.rationale_md && (
          <section className="mt-5 rounded-xl border-2 border-line/40 bg-sunken/50 p-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-muted">
              Explicacao oficial
            </h2>
            <Markdown className="mt-2 font-serif text-[15px] leading-relaxed">
              {reveal.rationale_md}
            </Markdown>

            {Object.keys(reveal.distractor_rationales ?? {}).length > 0 && (
              <details className="mt-3">
                <summary className="cursor-pointer text-xs font-bold uppercase tracking-wider text-muted hover:text-ink">
                  Por que as outras estao erradas
                </summary>
                <div className="mt-2 space-y-2">
                  {Object.entries(reveal.distractor_rationales)
                    .sort()
                    .map(([k, v]) => (
                      <div key={k} className="flex gap-2.5">
                        <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full border-2 border-line text-xs font-bold">
                          {k}
                        </span>
                        <Markdown className="font-serif text-sm text-muted">
                          {v}
                        </Markdown>
                      </div>
                    ))}
                </div>
              </details>
            )}
          </section>
        )}
      </article>

      {/* ---------------- calculadora ---------------- */}
      {isMath && (
        <div className="mt-4">
          <button
            onClick={() => setShowCalc((v) => !v)}
            aria-expanded={showCalc}
            className="rounded-xl border-2 border-line bg-surface px-4 py-2.5 text-sm font-bold shadow-flat-sm transition-transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-none"
          >
            {showCalc ? "Esconder calculadora" : "Calculadora"}
          </button>
          {showCalc && <Desmos />}
        </div>
      )}

      {/* ---------------- acoes ---------------- */}
      <div className="fixed inset-x-0 bottom-0 border-t-2 border-line bg-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-3 px-5 py-3.5">
          {phase === "answering" && (
            <button
              onClick={submit}
              disabled={
                busy ||
                (q.question_type === "multiple_choice" ? !picked : !typed.trim())
              }
              className="rounded-xl border-2 border-line px-5 py-2.5 font-display font-bold shadow-flat transition-transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-none disabled:opacity-40 disabled:hover:translate-y-0"
              style={{ background: accent, color: "var(--paper)" }}
            >
              {busy ? "Conferindo…" : "Confirmar resposta"}
            </button>
          )}

          {phase === "wrong" && (
            <>
              <button
                onClick={() => {
                  setPhase("answering");
                  setPicked(null);
                  setTyped("");
                }}
                className="rounded-xl border-2 border-line bg-surface px-5 py-2.5 font-display font-bold shadow-flat-sm transition-transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-none"
              >
                Tentar de novo
              </button>
              <button
                onClick={() => loadReveal(true)}
                className="rounded-xl border-2 border-line px-5 py-2.5 font-display font-bold shadow-flat transition-transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-none"
                style={{ background: "var(--accent)", color: "var(--ink)" }}
              >
                Mostrar resposta
              </button>
            </>
          )}

          <div className="flex-1" />

          <button
            onClick={next}
            className="rounded-xl border-2 border-line bg-surface px-5 py-2.5 font-display font-bold shadow-flat-sm transition-transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-none"
          >
            {idx + 1 < questions.length ? "Proxima questao →" : "Concluir"}
          </button>
        </div>
      </div>
    </div>
  );
}
