"""
Gera o dataset de Reading & Writing sem chamar a API.

Escreve out/questions_rw.jsonl no mesmo formato que ingest.py produz, para o
carregador tratar os dois iguais. Questoes cuja estrutura nao foi reconhecida
saem em out/rw_needs_vision.jsonl e ficam para o pipeline de visao.

Uso:
    python ingest_rw.py
"""
import io
import json
import pathlib
import sys

import pymupdf

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
ASSETS = OUT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

from segment import segment_pdf, assign_modules       # noqa: E402
from answers import parse_answers                      # noqa: E402
from extract import render_crop                        # noqa: E402
from figures import figure_bbox                        # noqa: E402
from rw_offline import (                               # noqa: E402
    parse_question, classify, parse_rationale, has_visual,
)

TESTS = [4, 5, 6, 7, 8, 9, 10, 11]
ASSET_ZOOM = 2.6


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    base = HERE.parent / "pdfs"
    done, needs_vision = [], []

    for number in TESTS:
        doc_q, regions = segment_pdf(str(base / f"sat-practice-test-{number}-digital.pdf"))
        labelled, problems = assign_modules(regions)
        doc_a, answers, aprob = parse_answers(
            str(base / f"sat-practice-test-{number}-answers-digital.pdf")
        )
        if problems or aprob:
            print(f"  prova {number}: avisos {problems + aprob}")

        n_ok = n_skip = 0
        for section, module_no, mod in labelled:
            if section != "reading_writing":
                continue
            for r in mod:
                key = (section, module_no, r.number)
                aregion = answers.get(key)
                tag = f"t{number}_{section}_m{module_no}_q{r.number}"

                parsed = parse_question(r)
                if parsed is None or aregion is None:
                    needs_vision.append({
                        "tag": tag, "test_number": number, "section": section,
                        "module_number": module_no, "question_number": r.number,
                        "reason": "estrutura nao reconhecida" if parsed is None
                                  else "sem gabarito",
                    })
                    n_skip += 1
                    continue

                correct = aregion.correct_choice()
                if not correct:
                    needs_vision.append({
                        "tag": tag, "test_number": number, "section": section,
                        "module_number": module_no, "question_number": r.number,
                        "reason": "resposta correta nao reconhecida",
                    })
                    n_skip += 1
                    continue

                domain, skill, conf = classify(parsed["prompt_md"],
                                               parsed["choices"])
                rationale, distractors = parse_rationale(aregion.text, correct)

                # figura: em R&W tabela e grafico viram imagem, porque sem visao
                # nao da para transcrever a tabela com seguranca
                assets = []
                if has_visual(doc_q, r):
                    fb = figure_bbox(doc_q, r, "graph")
                    if fb:
                        png = render_crop(doc_q, fb[0], fb[1],
                                          zoom=ASSET_ZOOM, tight=True)
                        fname = f"{tag}_figure.png"
                        (ASSETS / fname).write_bytes(png)
                        assets.append({
                            "file": fname, "bytes": len(png),
                            "kind": "graph", "role": "stimulus",
                            "alt_text": None,
                            "source_page": fb[0] + 1,
                            "source_bbox": [round(v, 1) for v in fb[1]],
                        })

                done.append({
                    "tag": tag,
                    "test_number": number,
                    "section": section,
                    "module_number": module_no,
                    "question_number": r.number,
                    "question_type": "multiple_choice",
                    "stimulus_md": parsed["stimulus_md"],
                    "prompt_md": parsed["prompt_md"],
                    "choices": parsed["choices"],
                    "has_figure": bool(assets),
                    "figure_kind": "graph" if assets else None,
                    "figure_alt_text": None,
                    "official_correct_choice": correct,
                    "correct_answer_text": None,
                    "correct_answer_alternates": [],
                    "answer_source": "official",
                    "rationale_md": rationale,
                    "distractor_rationales": distractors,
                    "domain_code": domain,
                    "skill_code": skill,
                    "classification_confidence": conf,
                    "classification_reason": "regra sobre o enunciado (offline)",
                    "difficulty": "unrated",
                    "assets": assets,
                    "source_page": r.page + 1,
                    "source_rects": [
                        {"page": p + 1, "bbox": [round(v, 1) for v in bb]}
                        for p, bb in (r.rects or [(r.page, r.bbox)])
                    ],
                    "answers_source_page": aregion.first_page + 1,
                    "extraction_model": "offline-rules",
                    "raw_text": r.body_text()[:8000],
                })
                n_ok += 1

        print(f"prova {number}: {n_ok} ok, {n_skip} para visao", flush=True)

    (OUT / "questions_rw.jsonl").write_text(
        "\n".join(json.dumps(d, ensure_ascii=False) for d in done),
        encoding="utf-8",
    )
    (OUT / "rw_needs_vision.jsonl").write_text(
        "\n".join(json.dumps(d, ensure_ascii=False) for d in needs_vision),
        encoding="utf-8",
    )

    figs = sum(1 for d in done if d["assets"])
    print(f"\n{len(done)} questoes em questions_rw.jsonl ({figs} com figura)")
    print(f"{len(needs_vision)} em rw_needs_vision.jsonl")


if __name__ == "__main__":
    main()
