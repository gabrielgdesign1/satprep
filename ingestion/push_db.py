"""
Carrega out/questions.jsonl no Supabase, direto pela API REST.

Este e o caminho para as 960 questoes. Precisa da SERVICE_ROLE key no .env
(Supabase > Project Settings > API > service_role), porque a RLS so permite
leitura de conteudo para usuarios autenticados -- escrever conteudo e
privilegio do pipeline.

Uso:
    python push_db.py            # envia tudo o que estiver no jsonl
    python push_db.py --dry-run  # so valida e mostra o que faria
"""
import argparse
import json
import os
import pathlib
import shutil
import sys
import io

import requests
from dotenv import load_dotenv

HERE = pathlib.Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")

OUT = HERE / "out"
ASSETS = OUT / "assets"
WEB_FIGURES = HERE.parent / "web" / "public" / "figures"

URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
CHUNK = 50


def headers(extra=None):
    h = {
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
    }
    if extra:
        h.update(extra)
    return h


def get(path, params):
    r = requests.get(f"{URL}/rest/v1/{path}", headers=headers(), params=params,
                     timeout=60)
    r.raise_for_status()
    return r.json()


def post(path, rows, on_conflict=None, prefer="return=representation"):
    params = {}
    if on_conflict:
        params["on_conflict"] = on_conflict
        prefer = f"resolution=merge-duplicates,{prefer}"
    r = requests.post(
        f"{URL}/rest/v1/{path}",
        headers=headers({"Prefer": prefer}),
        params=params,
        data=json.dumps(rows, ensure_ascii=False).encode("utf-8"),
        timeout=180,
    )
    if r.status_code >= 300:
        raise RuntimeError(f"{path}: {r.status_code} {r.text[:600]}")
    return r.json() if r.text.strip() else []


def delete(path, params):
    r = requests.delete(f"{URL}/rest/v1/{path}", headers=headers(),
                        params=params, timeout=120)
    if r.status_code >= 300:
        raise RuntimeError(f"delete {path}: {r.status_code} {r.text[:400]}")


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.dry_run and (not URL or not KEY):
        sys.exit(
            "Faltam SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no .env.\n"
            "Pegue em: Supabase > Project Settings > API > service_role."
        )

    path = OUT / "questions.jsonl"
    recs = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    print(f"{len(recs)} questoes em {path.name}")

    # --- mapas de referencia -------------------------------------------
    if args.dry_run:
        # valida so contra a taxonomia local; nao toca a API
        from taxonomy import VALID_SKILL_CODES
        valid = set().union(*VALID_SKILL_CODES.values())
        tests, skills = {}, {c: (None, None) for c in valid}
    else:
        tests = {t["number"]: t["id"]
                 for t in get("tests", {"select": "id,number"})}
        skills = {
            s["code"]: (s["id"], s["domain_id"])
            for s in get("skills", {"select": "id,code,domain_id"})
        }

    missing = {r["skill_code"] for r in recs if r["skill_code"] not in skills}
    if missing:
        sys.exit(f"skill_code fora da taxonomia: {sorted(missing)}")

    # --- figuras para os estaticos do Next ------------------------------
    WEB_FIGURES.mkdir(parents=True, exist_ok=True)
    copied = 0
    for r in recs:
        for a in r.get("assets") or []:
            src = ASSETS / a["file"]
            if src.exists():
                shutil.copy2(src, WEB_FIGURES / a["file"])
                copied += 1
    print(f"{copied} figuras em {WEB_FIGURES}")

    if args.dry_run:
        by_sec = {}
        for r in recs:
            by_sec[r["section"]] = by_sec.get(r["section"], 0) + 1
        print("dry-run:", by_sec)
        print("com figura:", sum(1 for r in recs if r.get("assets")))
        return

    # --- questoes --------------------------------------------------------
    rows = []
    for r in recs:
        skill_id, domain_id = skills[r["skill_code"]]
        mc = r["question_type"] == "multiple_choice"
        rows.append({
            "test_id": tests[r["test_number"]],
            "section": r["section"],
            "module_number": r["module_number"],
            "question_number": r["question_number"],
            "source_page": r["source_page"],
            "source_rects": r.get("source_rects") or [],
            "answers_page": r.get("answers_source_page"),
            "question_type": r["question_type"],
            "stimulus_md": r.get("stimulus_md"),
            "prompt_md": r["prompt_md"],
            "has_figure": bool(r.get("has_figure")),
            "figure_alt_text": r.get("figure_alt_text"),
            "difficulty": r.get("difficulty", "unrated"),
            "domain_id": domain_id,
            "skill_id": skill_id,
            "classification_source": "ai",
            "classification_confidence": r.get("classification_confidence"),
            "classification_reason": r.get("classification_reason"),
            "correct_choice": r.get("official_correct_choice") if mc else None,
            "correct_answer_text": None if mc else r.get("correct_answer_text"),
            "correct_answer_alternates": r.get("correct_answer_alternates") or [],
            "answer_source": "official",
            "rationale_md": r.get("rationale_md"),
            "distractor_rationales": r.get("distractor_rationales") or {},
            "raw_text": (r.get("raw_text") or "")[:8000],
            "extraction_model": r.get("extraction_model"),
        })

    key_of = {}
    inserted = []
    for i in range(0, len(rows), CHUNK):
        got = post(
            "questions", rows[i:i + CHUNK],
            on_conflict="test_id,section,module_number,question_number",
        )
        inserted.extend(got)
        print(f"  questoes {min(i + CHUNK, len(rows))}/{len(rows)}", flush=True)

    for q in inserted:
        key_of[(q["section"], q["module_number"], q["question_number"],
                q["test_id"])] = q["id"]

    def qid(r):
        return key_of[(r["section"], r["module_number"], r["question_number"],
                       tests[r["test_number"]])]

    # --- filhos: apaga e reinsere (idempotente) --------------------------
    ids = [qid(r) for r in recs]
    for i in range(0, len(ids), CHUNK):
        batch = ids[i:i + CHUNK]
        inlist = "(" + ",".join(batch) + ")"
        delete("question_choices", {"question_id": f"in.{inlist}"})
        delete("question_assets", {"question_id": f"in.{inlist}"})

    asset_rows = []
    for r in recs:
        for a in r.get("assets") or []:
            asset_rows.append({
                "question_id": qid(r),
                "kind": a.get("kind", "graph"),
                "role": a.get("role", "stimulus"),
                "choice_label": a.get("choice_label"),
                "storage_path": "/figures/" + a["file"],
                "alt_text": a.get("alt_text"),
                "source_page": a.get("source_page"),
                "source_bbox": a.get("source_bbox") or [],
                "byte_size": a.get("bytes"),
            })

    made_assets = []
    for i in range(0, len(asset_rows), CHUNK):
        made_assets.extend(post("question_assets", asset_rows[i:i + CHUNK]))
    print(f"  {len(made_assets)} figuras registradas")

    asset_by = {
        (a["question_id"], a["choice_label"]): a["id"]
        for a in made_assets if a["role"] == "choice"
    }

    choice_rows = []
    for r in recs:
        q = qid(r)
        for i, c in enumerate(r.get("choices") or []):
            choice_rows.append({
                "question_id": q,
                "label": c["label"],
                "content_md": c["content_md"],
                "is_graphic": bool(c.get("is_graphic")),
                "asset_id": asset_by.get((q, c["label"])),
                "display_order": i,
            })

    for i in range(0, len(choice_rows), CHUNK):
        post("question_choices", choice_rows[i:i + CHUNK])
    print(f"  {len(choice_rows)} alternativas")

    print("\nconcluido.")


if __name__ == "__main__":
    main()
