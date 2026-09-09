import Link from "next/link";
import { notFound } from "next/navigation";
import { supabaseServer } from "@/lib/supabase-server";
import { BackdropShapes, EmptyArt, Logo } from "@/components/Doodles";
import ThemeToggle from "@/components/ThemeToggle";
import PracticeSession from "@/components/PracticeSession";
import type { Question, Section } from "@/lib/types";

export const dynamic = "force-dynamic";

/**
 * Monta a fila da sessao: questoes da skill + dificuldade escolhidas, tirando
 * as que ja estao resolvidas (isto e, as que tem linha em
 * user_question_progress). Reiniciar o topico devolve todas para a fila.
 */
export default async function SkillPracticePage({
  params,
  searchParams,
}: {
  params: { section: string; skill: string };
  searchParams: { d?: string };
}) {
  const section = params.section as Section;
  if (section !== "math" && section !== "reading_writing") notFound();

  const supabase = supabaseServer();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) notFound();

  const { data: skill } = await supabase
    .from("skills")
    .select("id, code, name, domain_id, domains(name, section)")
    .eq("code", params.skill)
    .single();

  if (!skill) notFound();

  const difficulty = searchParams.d;

  const { data: solvedRows } = await supabase
    .from("user_question_progress")
    .select("question_id")
    .eq("user_id", user.id);
  const solved = new Set((solvedRows ?? []).map((r) => r.question_id));

  let query = supabase
    .from("questions")
    .select(
      `id, section, question_type, stimulus_md, prompt_md, has_figure,
       figure_alt_text, difficulty, module_number, question_number,
       tests(number),
       question_choices(id, label, content_md, is_graphic, display_order,
                        question_assets(storage_path)),
       question_assets(kind, role, choice_label, storage_path, alt_text)`
    )
    .eq("skill_id", skill.id)
    .order("question_number", { ascending: true });

  if (difficulty) query = query.eq("difficulty", difficulty);

  const { data: raw } = await query;

  const questions: Question[] = (raw ?? [])
    .filter((q: any) => !solved.has(q.id))
    .map((q: any) => ({
      id: q.id,
      section: q.section,
      question_type: q.question_type,
      stimulus_md: q.stimulus_md,
      prompt_md: q.prompt_md,
      has_figure: q.has_figure,
      figure_alt_text: q.figure_alt_text,
      difficulty: q.difficulty,
      test_number: q.tests?.number ?? 0,
      module_number: q.module_number,
      question_number: q.question_number,
      skill_name: skill.name,
      domain_name: (skill as any).domains?.name ?? "",
      assets: (q.question_assets ?? []).map((a: any) => ({
        kind: a.kind,
        role: a.role,
        choice_label: a.choice_label,
        storage_path: a.storage_path,
        alt_text: a.alt_text,
      })),
      choices: (q.question_choices ?? [])
        .slice()
        .sort((a: any, b: any) => a.display_order - b.display_order)
        .map((c: any) => ({
          id: c.id,
          label: c.label,
          content_md: c.content_md,
          is_graphic: c.is_graphic,
          asset_path:
            (q.question_assets ?? []).find(
              (a: any) => a.role === "choice" && a.choice_label === c.label
            )?.storage_path ?? null,
          display_order: c.display_order,
        })),
    }));

  const accent = section === "math" ? "var(--math)" : "var(--rw)";
  const backHref = `/practice/${section}${difficulty ? `?d=${difficulty}` : ""}`;

  return (
    <main className="relative min-h-dvh">
      <BackdropShapes tone={section === "math" ? "math" : "rw"} />

      <header className="mx-auto flex max-w-3xl items-center justify-between px-5 pt-6">
        <Link href={backHref} className="flex items-center gap-3">
          <Logo className="h-9 w-9" />
          <span className="font-display text-lg font-bold">SAT Practice</span>
        </Link>
        <ThemeToggle />
      </header>

      {questions.length === 0 ? (
        <div className="mx-auto max-w-lg px-5 py-24 text-center">
          <EmptyArt className="mx-auto h-32 w-40" />
          <h1 className="mt-6 font-display text-3xl font-black">
            Topico zerado
          </h1>
          <p className="mt-3 text-muted">
            Voce ja resolveu todas as questoes de{" "}
            <b className="text-ink">{skill.name}</b>
            {difficulty ? " neste nivel de dificuldade" : ""}. Para repetir,
            use <b className="text-ink">Reiniciar</b> na lista de topicos.
          </p>
          <Link
            href={backHref}
            className="mt-7 inline-block rounded-xl border-2 border-line px-5 py-3 font-bold shadow-flat transition-transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-none"
            style={{ background: accent, color: "var(--paper)" }}
          >
            Voltar aos topicos
          </Link>
        </div>
      ) : (
        <PracticeSession
          questions={questions}
          accent={accent}
          backHref={backHref}
          skillName={skill.name}
          domainName={(skill as any).domains?.name ?? ""}
        />
      )}
    </main>
  );
}
