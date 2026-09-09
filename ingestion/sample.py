"""
Roda o pipeline numa amostra pequena e deliberadamente dificil, para revisao
manual antes de gastar as ~960 chamadas.

A amostra nao e aleatoria: escolhe os casos que mais tendem a quebrar --
questao com grafico, questao com tabela, grid-in, formula com fracao/expoente --
alem de alguns casos simples de R&W como controle.
"""
import json
import os
import pathlib
import sys
import io
import time

from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

from segment import segment_pdf, assign_modules            # noqa: E402
from answers import parse_answers                           # noqa: E402
from extract import extract_question, render_crop           # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent / "out" / "sample"
OUT.mkdir(parents=True, exist_ok=True)

MODEL = os.environ.get("INGEST_VISION_MODEL", "claude-opus-5")

# (teste, secao, modulo, numero) -- escolhidos pelo tipo de dificuldade
SAMPLE = [
    (10, "reading_writing", 1, 1),    # words in context, simples (controle)
    (10, "reading_writing", 1, 7),    # text structure, alternativas longas
    (10, "reading_writing", 2, 12),   # tabela larga, pagina de coluna unica
    (10, "reading_writing", 2, 14),   # tabela, a questao que quase se perdeu
    (10, "math", 1, 3),               # fracao t/10 <= 75, formula desmontada
    (10, "math", 1, 4),               # ALTERNATIVAS sao graficos
    (10, "math", 1, 11),              # expoentes negativos, EuclidSymbol
    (10, "math", 1, 23),              # equacao de circunferencia
    (4,  "math", 2, 16),              # outro teste, outro subset de fonte
    (11, "reading_writing", 1, 3),    # teste 11: layout de 2 colunas sem divisor
    (10, "math", 1, 6),               # grid-in inteiro simples
    (10, "math", 1, 27),              # grid-in FRACAO ("3 29" no texto cru)
    (10, "reading_writing", 1, 17),   # continuacao: grafico numa coluna, pergunta na outra
    (7,  "reading_writing", 1, 13),   # outra continuacao, em outro teste
]


def load_test(number: int):
    base = pathlib.Path(__file__).resolve().parent.parent / "pdfs"
    qpath = base / f"sat-practice-test-{number}-digital.pdf"
    apath = base / f"sat-practice-test-{number}-answers-digital.pdf"
    doc_q, regions = segment_pdf(str(qpath))
    labelled, problems = assign_modules(regions)
    if problems:
        print(f"  aviso na segmentacao do teste {number}: {problems}")
    index = {}
    for section, module_no, mod in labelled:
        for r in mod:
            index[(section, module_no, r.number)] = r
    doc_a, answers, aproblems = parse_answers(str(apath))
    if aproblems:
        print(f"  aviso no gabarito do teste {number}: {aproblems}")
    return doc_q, index, doc_a, answers


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    cache = {}
    results = []
    total_in = total_out = 0

    for test_no, section, module_no, qnum in SAMPLE:
        if test_no not in cache:
            print(f"carregando teste {test_no}...")
            cache[test_no] = load_test(test_no)
        doc_q, index, doc_a, answers = cache[test_no]

        key = (section, module_no, qnum)
        qregion = index.get(key)
        aregion = answers.get(key)
        if qregion is None or aregion is None:
            print(f"  FALTANDO teste {test_no} {key}")
            continue

        tag = f"t{test_no}_{section}_m{module_no}_q{qnum}"
        # salva os recortes para conferencia visual lado a lado com o JSON
        for i, (pno, rect) in enumerate(qregion.rects or [(qregion.page, qregion.bbox)]):
            (OUT / f"{tag}_question{i}.png").write_bytes(
                render_crop(doc_q, pno, rect)
            )
        for i, (pno, rect) in enumerate(aregion.rects[:3]):
            (OUT / f"{tag}_answer{i}.png").write_bytes(
                render_crop(doc_a, pno, rect)
            )

        print(f"  extraindo {tag} ...", end=" ", flush=True)
        t0 = time.time()
        try:
            data, usage = extract_question(
                qregion, aregion, doc_q, doc_a, section, MODEL
            )
        except Exception as exc:
            print(f"ERRO: {type(exc).__name__}: {exc}")
            results.append({"tag": tag, "error": f"{type(exc).__name__}: {exc}"})
            continue

        total_in += usage.input_tokens
        total_out += usage.output_tokens
        data.update({
            "tag": tag,
            "test_number": test_no,
            "section": section,
            "module_number": module_no,
            "question_number": qnum,
            "source_page": qregion.page + 1,
            "source_bbox": [round(v, 1) for v in qregion.bbox],
            "answers_source_page": aregion.first_page + 1,
            "official_correct_choice": aregion.correct_choice(),
            "raw_text": qregion.body_text(),
        })
        results.append(data)
        print(f"ok ({time.time() - t0:.1f}s)")

    (OUT / "sample.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ok = [r for r in results if "error" not in r]
    print(f"\n{len(ok)}/{len(SAMPLE)} extraidas")
    print(f"tokens: entrada={total_in:,} saida={total_out:,}")
    if ok:
        est = (total_in / len(ok)) * 960, (total_out / len(ok)) * 960
        print(f"projecao p/ 960 questoes: ~{est[0]:,.0f} in / ~{est[1]:,.0f} out")
    print(f"arquivos em {OUT}")


if __name__ == "__main__":
    main()
