import Link from "next/link";
import { notFound } from "next/navigation";
import { supabaseServer } from "@/lib/supabase-server";
import { BackdropShapes, Logo } from "@/components/Doodles";
import ThemeToggle from "@/components/ThemeToggle";
import TopicTree from "@/components/TopicTree";
import { SECTION_LABEL, type Section, type SkillProgress } from "@/lib/types";

export const dynamic = "force-dynamic";

/** Segundo nivel: arvore de dominios e skills, com contador resolvidas/total. */
export default async function SectionPage({
  params,
  searchParams,
}: {
  params: { section: string };
  searchParams: { d?: string };
}) {
  const section = params.section as Section;
  if (section !== "math" && section !== "reading_writing") notFound();

  const difficulty = searchParams.d ?? "all";
  const supabase = supabaseServer();

  const { data } = await supabase
    .from("v_skill_progress")
    .select("*")
    .eq("section", section);

  const rows = (data ?? []) as SkillProgress[];
  const accent = section === "math" ? "var(--math)" : "var(--rw)";

  return (
    <main className="relative min-h-dvh">
      <BackdropShapes tone={section === "math" ? "math" : "rw"} />

      <header className="mx-auto flex max-w-3xl items-center justify-between px-5 pt-6">
        <Link href="/" className="flex items-center gap-3">
          <Logo className="h-9 w-9" />
          <span className="font-display text-lg font-bold">SAT Practice</span>
        </Link>
        <ThemeToggle />
      </header>

      <div className="mx-auto max-w-3xl px-5 pb-20 pt-8">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink"
        >
          <span aria-hidden>←</span> Trocar de secao
        </Link>

        <h1
          className="mt-3 font-display text-4xl font-black leading-tight"
          style={{ color: accent }}
        >
          {SECTION_LABEL[section]}
        </h1>
        <p className="mt-2 text-muted">
          Escolha um topico para comecar. O contador mostra quantas questoes
          voce ja resolveu.
        </p>

        <TopicTree
          rows={rows}
          section={section}
          difficulty={difficulty}
          accent={accent}
        />
      </div>
    </main>
  );
}
