"""
Ingestao completa: as 960 questoes das 8 provas.

Grava incrementalmente em out/questions.jsonl e e resumivel -- rodar de novo
so processa o que falta. As figuras (apenas graficos/diagramas, nunca tabelas)
vao para out/assets/ como PNG.

Uso:
    python ingest.py                 # tudo o que falta
    python ingest.py --tests 10 11   # so essas provas
    python ingest.py --retry-low     # refaz as de baixa confianca com Opus
"""
import argparse
import base64
import json
import os
import pathlib
import sys
import io
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

from segment import segment_pdf, assign_modules          # noqa: E402
from answers import parse_answers                         # noqa: E402
from extract import extract_question, render_crop         # noqa: E402
from figures import figure_bbox, choice_graphic_boxes     # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
ASSETS = OUT / "assets"
JSONL = OUT / "questions.jsonl"
FAILED = OUT / "failed.jsonl"
ASSETS.mkdir(parents=True, exist_ok=True)

TESTS = [4, 5, 6, 7, 8, 9, 10, 11]
WORKERS = 6
ASSET_ZOOM = 2.6            # nitidez de leitura na tela, sem inflar o arquivo
LOW_CONF = 0.80

_write_lock = threading.Lock()
_docs_lock = threading.Lock()
_docs = {}


def load_test(number: int):
    """Carrega e indexa uma prova (cache: os PDFs sao caros de reabrir)."""
    with _docs_lock:
        if number in _docs:
            return _docs[number]
    base = HERE.parent / "pdfs"
    doc_q, regions = segment_pdf(str(base / f"sat-practice-test-{number}-digital.pdf"))
    labelled, problems = assign_modules(regions)
    index = {}
    for section, module_no, mod in labelled:
        for r in mod:
            index[(section, module_no, r.number)] = r
    doc_a, answers, aproblems = parse_answers(
        str(base / f"sat-practice-test-{number}-answers-digital.pdf")
    )
    val = (doc_q, index, doc_a, answers, problems + aproblems)
    with _docs_lock:
        _docs[number] = val
    return val


def done_keys():
    if not JSONL.exists():
        return set()
    keys = set()
    for line in JSONL.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
            keys.add((d["test_number"], d["section"], d["module_number"],
                      d["question_number"]))
        except Exception:
            pass
    return keys


def append(path, record):
    with _write_lock:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def save_asset(doc, page_no, bbox, name) -> dict:
    png = render_crop(doc, page_no, bbox, zoom=ASSET_ZOOM, tight=False)
    path = ASSETS / f"{name}.png"
    path.write_bytes(png)
    return {
        "file": path.name,
        "bytes": len(png),
        "source_page": page_no + 1,
        "source_bbox": [round(v, 1) for v in bbox],
    }


def process(test_no, section, module_no, qnum, model):
    doc_q, index, doc_a, answers, _ = load_test(test_no)
    key = (section, module_no, qnum)
    qregion, aregion = index.get(key), answers.get(key)
    if qregion is None or aregion is None:
        raise KeyError(f"regiao ausente para {key}")

    data, usage = extract_question(qregion, aregion, doc_q, doc_a, section, model)

    tag = f"t{test_no}_{section}_m{module_no}_q{qnum}"
    assets = []

    # figura do enunciado: so grafico/diagrama; tabela ja virou Markdown
    kind = data.get("figure_kind")
    if data.get("has_figure") and kind != "table":
        fb = figure_bbox(doc_q, qregion, kind)
        if fb:
            a = save_asset(doc_q, fb[0], fb[1], f"{tag}_figure")
            a["kind"] = kind or "graph"
            a["alt_text"] = data.get("figure_alt_text")
            a["role"] = "stimulus"
            assets.append(a)
        else:
            data["figure_missing"] = True

    # alternativas que sao graficos
    if any(c.get("is_graphic") for c in data.get("choices") or []):
        boxes = choice_graphic_boxes(doc_q, qregion)
        for label, (pno, bbox) in boxes.items():
            a = save_asset(doc_q, pno, bbox, f"{tag}_choice_{label}")
            a["kind"] = "choice_graphic"
            a["role"] = "choice"
            a["choice_label"] = label
            assets.append(a)
        if not boxes:
            data["choice_graphics_missing"] = True

    data.update({
        "tag": tag,
        "test_number": test_no,
        "section": section,
        "module_number": module_no,
        "question_number": qnum,
        "source_page": qregion.page + 1,
        "source_rects": [
            {"page": p + 1, "bbox": [round(v, 1) for v in bb]}
            for p, bb in (qregion.rects or [(qregion.page, qregion.bbox)])
        ],
        "answers_source_page": aregion.first_page + 1,
        "official_correct_choice": aregion.correct_choice(),
        "answer_source": "official",
        "difficulty": "unrated",
        "assets": assets,
        "extraction_model": model,
        "raw_text": qregion.body_text()[:8000],
        "usage": {"in": usage.input_tokens, "out": usage.output_tokens},
    })
    return data


def build_worklist(tests, only_missing=True):
    work = []
    have = done_keys() if only_missing else set()
    for t in tests:
        _, index, _, answers, problems = load_test(t)
        if problems:
            print(f"  prova {t}: AVISOS {problems}")
        for key in sorted(index.keys() & answers.keys(),
                          key=lambda k: (k[0], k[1], k[2])):
            section, module_no, qnum = key
            if (t, section, module_no, qnum) in have:
                continue
            work.append((t, section, module_no, qnum))
    return work


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", nargs="*", type=int, default=TESTS)
    ap.add_argument("--workers", type=int, default=WORKERS)
    ap.add_argument("--model", default=os.environ.get(
        "INGEST_VISION_MODEL", "claude-sonnet-5"))
    ap.add_argument("--retry-low", action="store_true")
    args = ap.parse_args()

    if args.retry_low:
        return retry_low(args)

    print(f"modelo: {args.model} | workers: {args.workers}")
    work = build_worklist(args.tests)
    print(f"{len(work)} questoes a processar")
    if not work:
        print("nada a fazer -- tudo ja ingerido")
        return

    t0 = time.time()
    ok = fail = 0
    tin = tout = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(process, *w, args.model): w for w in work
        }
        for i, fut in enumerate(as_completed(futs), 1):
            w = futs[fut]
            try:
                rec = fut.result()
                append(JSONL, rec)
                tin += rec["usage"]["in"]
                tout += rec["usage"]["out"]
                ok += 1
            except Exception as exc:
                fail += 1
                append(FAILED, {
                    "test_number": w[0], "section": w[1],
                    "module_number": w[2], "question_number": w[3],
                    "error": f"{type(exc).__name__}: {exc}",
                })
            if i % 20 == 0 or i == len(work):
                el = time.time() - t0
                rate = i / el if el else 0
                eta = (len(work) - i) / rate if rate else 0
                print(f"  {i}/{len(work)}  ok={ok} falhas={fail}  "
                      f"{rate:.2f}/s  ETA {eta/60:.1f}min", flush=True)

    print(f"\nconcluido em {(time.time()-t0)/60:.1f} min")
    print(f"ok={ok} falhas={fail}")
    print(f"tokens: entrada={tin:,} saida={tout:,}")
    if fail:
        print(f"falhas registradas em {FAILED}")


def retry_low(args):
    """Refaz com Opus as questoes de baixa confianca ou com asset faltando."""
    model = "claude-opus-5"
    recs = [json.loads(l) for l in JSONL.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    targets = [
        r for r in recs
        if r.get("classification_confidence", 1) < LOW_CONF
        or r.get("figure_missing") or r.get("choice_graphics_missing")
    ]
    print(f"{len(targets)} questoes para refazer com {model}")
    if not targets:
        return

    keep = {(r["test_number"], r["section"], r["module_number"],
             r["question_number"]) for r in targets}
    redone = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(process, r["test_number"], r["section"],
                        r["module_number"], r["question_number"], model): r
            for r in targets
        }
        for i, fut in enumerate(as_completed(futs), 1):
            try:
                rec = fut.result()
                redone[(rec["test_number"], rec["section"],
                        rec["module_number"], rec["question_number"])] = rec
            except Exception as exc:
                print(f"  falhou: {exc}")
            if i % 10 == 0:
                print(f"  {i}/{len(targets)}", flush=True)

    merged = []
    for r in recs:
        k = (r["test_number"], r["section"], r["module_number"],
             r["question_number"])
        merged.append(redone.get(k, r) if k in keep else r)
    with open(JSONL, "w", encoding="utf-8") as fh:
        for r in merged:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(redone)} regravadas")


if __name__ == "__main__":
    main()
