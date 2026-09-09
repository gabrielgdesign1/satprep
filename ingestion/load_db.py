"""
Gera o SQL de carga das questoes extraidas (out/questions.jsonl) e copia as
figuras para web/public/figures/.

As figuras sao servidas como estaticos pelo Next em vez de irem para o Supabase
Storage: sao poucos arquivos, evitam uma credencial de service_role no ambiente
e ficam versionados junto com o deploy.

Uso:
    python load_db.py            # gera out/load_XX.sql
"""
import json
import pathlib
import shutil
import sys
import io

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
ASSETS = OUT / "assets"
WEB_FIGURES = HERE.parent / "web" / "public" / "figures"
BATCH = 17


def q(s):
    """Literal SQL seguro para texto."""
    if s is None:
        return "null"
    return "'" + str(s).replace("'", "''") + "'"


def qarr(items):
    if not items:
        return "'{}'"
    inner = ",".join('"' + str(i).replace('\\', '\\\\').replace('"', '\\"') + '"'
                     for i in items)
    return "'{" + inner.replace("'", "''") + "}'"


def qjson(obj):
    return q(json.dumps(obj, ensure_ascii=False)) + "::jsonb"


def build():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    recs = [
        json.loads(l) for l in (OUT / "questions.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    print(f"{len(recs)} questoes em questions.jsonl")

    WEB_FIGURES.mkdir(parents=True, exist_ok=True)
    copied = 0
    for rec in recs:
        for a in rec.get("assets") or []:
            src = ASSETS / a["file"]
            if src.exists():
                shutil.copy2(src, WEB_FIGURES / a["file"])
                copied += 1
    print(f"{copied} figuras copiadas para {WEB_FIGURES}")

    for path in OUT.glob("load_*.sql"):
        path.unlink()

    for bi in range(0, len(recs), BATCH):
        chunk = recs[bi:bi + BATCH]
        stmts = []
        for r in chunk:
            tag = r["tag"]
            correct_choice = (
                q(r.get("official_correct_choice"))
                if r["question_type"] == "multiple_choice" else "null"
            )
            correct_text = (
                q(r.get("correct_answer_text"))
                if r["question_type"] == "grid_in" else "null"
            )

            stmts.append(f"""
with t as (select id from tests where number = {r['test_number']}),
     sk as (select id, domain_id from skills where code = {q(r['skill_code'])}),
ins as (
  insert into questions (
    test_id, section, module_number, question_number,
    source_page, source_rects, answers_page,
    question_type, stimulus_md, prompt_md, has_figure, figure_alt_text,
    difficulty, domain_id, skill_id,
    classification_source, classification_confidence, classification_reason,
    correct_choice, correct_answer_text, correct_answer_alternates,
    answer_source, rationale_md, distractor_rationales,
    raw_text, extraction_model
  )
  select
    t.id, {q(r['section'])}::section_kind, {r['module_number']}, {r['question_number']},
    {r['source_page']}, {qjson(r.get('source_rects') or [])}, {r.get('answers_source_page') or 'null'},
    {q(r['question_type'])}::question_kind, {q(r.get('stimulus_md'))}, {q(r['prompt_md'])},
    {str(bool(r.get('has_figure'))).lower()}, {q(r.get('figure_alt_text'))},
    {q(r.get('difficulty', 'unrated'))}::difficulty_kind, sk.domain_id, sk.id,
    'ai'::classif_origin, {r.get('classification_confidence') or 'null'},
    {q(r.get('classification_reason'))},
    {correct_choice}, {correct_text}, {qarr(r.get('correct_answer_alternates'))},
    'official'::answer_origin, {q(r.get('rationale_md'))},
    {qjson(r.get('distractor_rationales') or {})},
    {q((r.get('raw_text') or '')[:400])}, {q(r.get('extraction_model'))}
  from t, sk
  on conflict (test_id, section, module_number, question_number) do update
    set prompt_md = excluded.prompt_md,
        stimulus_md = excluded.stimulus_md,
        skill_id = excluded.skill_id,
        domain_id = excluded.domain_id,
        rationale_md = excluded.rationale_md,
        distractor_rationales = excluded.distractor_rationales,
        classification_confidence = excluded.classification_confidence,
        classification_reason = excluded.classification_reason,
        extraction_model = excluded.extraction_model
  returning id
)
select id from ins;""".strip())

            # limpa filhos antes de reinserir (idempotencia)
            key = (f"(select q.id from questions q join tests t on t.id=q.test_id "
                   f"where t.number={r['test_number']} and q.section={q(r['section'])}::section_kind "
                   f"and q.module_number={r['module_number']} "
                   f"and q.question_number={r['question_number']})")
            stmts.append(f"delete from question_assets  where question_id = {key};")
            stmts.append(f"delete from question_choices where question_id = {key};")

            for a in r.get("assets") or []:
                stmts.append(f"""
insert into question_assets (
  question_id, kind, role, choice_label, storage_path, alt_text,
  source_page, source_bbox, byte_size
) values (
  {key}, {q(a.get('kind', 'graph'))}::asset_kind, {q(a.get('role', 'stimulus'))},
  {q(a.get('choice_label'))}, {q('/figures/' + a['file'])}, {q(a.get('alt_text'))},
  {a.get('source_page') or 'null'}, {qjson(a.get('source_bbox') or [])},
  {a.get('bytes') or 'null'}
);""".strip())

            for i, c in enumerate(r.get("choices") or []):
                asset_lookup = "null"
                if c.get("is_graphic"):
                    asset_lookup = (
                        f"(select id from question_assets where question_id = {key} "
                        f"and role='choice' and choice_label={q(c['label'])} limit 1)"
                    )
                stmts.append(f"""
insert into question_choices (
  question_id, label, content_md, is_graphic, asset_id, display_order
) values (
  {key}, {q(c['label'])}, {q(c['content_md'])},
  {str(bool(c.get('is_graphic'))).lower()}, {asset_lookup}, {i}
);""".strip())

        path = OUT / f"load_{bi // BATCH:02d}.sql"
        path.write_text("\n".join(stmts), encoding="utf-8")
        print(f"  {path.name}: {len(chunk)} questoes, {path.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    build()
