"""
Parser do PDF de "Answer Explanations" do College Board.

Estrutura do documento
----------------------
* Coluna unica (x ~ 57-390). O header de cada pagina identifica secao e modulo:
  "SAT ANSWER EXPLANATIONS  n  MATH: MODULE 1".
* Cada explicacao comeca num bloco "QUESTION N" em AktivGrotesk-Bold.
* Multiple choice:  "Choice C is correct." / "Choice A is the best answer"
* Grid-in (SPR):    "The correct answer is 77."
* A explicacao pode atravessar paginas, entao a regiao de uma questao e uma
  LISTA de retangulos (um por pagina), nao um retangulo so.

As formulas no rationale de Math vem desmontadas em spans posicionados -- o
mesmo problema do caderno de questoes. Por isso guardamos os retangulos: o
estagio de visao recorta essas regioes e reconstroi o LaTeX a partir da imagem.
"""
import re
from dataclasses import dataclass, field

import pymupdf

HEADER_BOTTOM = 70.0
FOOTER_TOP = 735.0
CONTENT_X0, CONTENT_X1 = 50.0, 400.0

QUESTION_RE = re.compile(r"^QUESTION\s+(\d+)\s*$", re.I)
HEADER_RE = re.compile(
    r"(READING AND WRITING|MATH)\s*:\s*MODULE\s*(\d+)", re.I
)

# "Choice C is correct." | "Choice A is the best answer because..."
CHOICE_RE = re.compile(
    r"Choice\s+([A-D])\s+is\s+(?:the\s+best\s+answer|correct)", re.I
)
# "The correct answer is 77." -- o valor pode vir quebrado em varias linhas
GRIDIN_RE = re.compile(r"The correct answer is\s+(.{1,60}?)\.\s", re.I | re.S)

SECTION_MAP = {"READING AND WRITING": "reading_writing", "MATH": "math"}


@dataclass
class AnswerRegion:
    number: int
    section: str
    module: int
    rects: list = field(default_factory=list)   # [(page_no, (x0,y0,x1,y1)), ...]
    text: str = ""

    @property
    def first_page(self) -> int:
        return self.rects[0][0] if self.rects else -1

    def correct_choice(self):
        m = CHOICE_RE.search(self.text)
        return m.group(1).upper() if m else None

    def correct_answer_text(self):
        m = GRIDIN_RE.search(self.text)
        if not m:
            return None
        # o valor vem quebrado em linhas ("3\n29" = 3/29); a normalizacao final
        # e feita pelo estagio de visao, que enxerga a fracao renderizada
        return " ".join(m.group(1).split())


def _page_header(page):
    """Retorna (section, module) lido do cabecalho da pagina, ou None."""
    for b in page.get_text("dict")["blocks"]:
        if b["type"] == 1:
            continue
        if b["bbox"][1] > HEADER_BOTTOM:
            continue
        txt = " ".join(s["text"] for l in b["lines"] for s in l["spans"])
        m = HEADER_RE.search(txt)
        if m:
            return SECTION_MAP[m.group(1).upper()], int(m.group(2))
    return None


def parse_answers(path: str):
    """
    Retorna (doc, {(section, module, number): AnswerRegion}, problemas).
    """
    doc = pymupdf.open(path)

    # 1) marcadores "QUESTION N" com pagina, y e contexto de secao/modulo
    marks = []
    cur_ctx = None
    page_ctx = {}
    for pno in range(doc.page_count):
        page = doc[pno]
        ctx = _page_header(page)
        if ctx:
            cur_ctx = ctx
        page_ctx[pno] = cur_ctx
        for b in page.get_text("dict")["blocks"]:
            if b["type"] == 1:
                continue
            txt = " ".join(
                s["text"] for l in b["lines"] for s in l["spans"]
            ).strip()
            m = QUESTION_RE.match(txt)
            if m and cur_ctx:
                marks.append((pno, b["bbox"][1], int(m.group(1)), cur_ctx))

    marks.sort(key=lambda t: (t[0], t[1]))

    # 2) cada marcador vai ate o proximo, atravessando paginas se preciso
    regions = {}
    problems = []
    for i, (pno, y, num, (section, module)) in enumerate(marks):
        if i + 1 < len(marks):
            end_pno, end_y = marks[i + 1][0], marks[i + 1][1]
        else:
            end_pno, end_y = doc.page_count - 1, FOOTER_TOP

        rects = []
        for p in range(pno, min(end_pno, doc.page_count - 1) + 1):
            top = y if p == pno else HEADER_BOTTOM
            bottom = end_y - 2 if p == end_pno else FOOTER_TOP
            if bottom - top < 5:
                continue
            rects.append((p, (CONTENT_X0, top, CONTENT_X1, bottom)))

        text_parts = []
        for p, rect in rects:
            text_parts.append(
                doc[p].get_text("text", clip=pymupdf.Rect(*rect))
            )
        region = AnswerRegion(
            number=num, section=section, module=module,
            rects=rects, text="\n".join(text_parts),
        )

        key = (section, module, num)
        if key in regions:
            problems.append(f"duplicado: {key}")
        regions[key] = region

    # 3) validacao: toda questao precisa de uma resposta reconhecida
    for key, r in regions.items():
        if r.correct_choice() is None and r.correct_answer_text() is None:
            problems.append(f"sem resposta reconhecida: {key}")

    return doc, regions, problems


if __name__ == "__main__":
    import sys, io, glob, os
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    grand_total = 0
    for path in sorted(glob.glob("../pdfs/*-answers-digital.pdf")):
        doc, regions, problems = parse_answers(path)
        mc = sum(1 for r in regions.values() if r.correct_choice())
        gi = sum(
            1 for r in regions.values()
            if not r.correct_choice() and r.correct_answer_text()
        )
        grand_total += len(regions)
        status = "OK" if not problems else " | ".join(problems[:3])
        print(
            f"{os.path.basename(path):44s} total={len(regions):4d} "
            f"mc={mc:3d} grid={gi:3d}  {status}"
        )
    print("total de explicacoes:", grand_total)
