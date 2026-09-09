"""
Segmenta um PDF de questoes do SAT (formato digital, entrega nao-digital) em
regioes de questao individuais.

Como o PDF e montado
--------------------
* A maioria das paginas tem DUAS colunas separadas por um divisor pontilhado
  vertical em x ~ 294-312. Paginas com tabela/grafico largo sao de COLUNA UNICA
  e nao tem esse divisor -- por isso o layout e detectado, nao assumido.
* O numero da questao e um span puramente numerico, na fonte de corpo, sozinho
  na sua linha horizontal e recuado a esquerda da margem do enunciado.
* O texto real da questao usa subsets de MinionPro. Times / Helvetica /
  HiddenHorzOCR sao a camada de OCR embutida nos graficos vetoriais: viram lixo
  como "6 -4 -2 IU , 2" e sao descartados do texto (mas nao da imagem).
* Os modulos sao delimitados pelo reinicio da numeracao, na ordem fixa do
  caderno: R&W M1, R&W M2, Math M1, Math M2.
"""
import re
from dataclasses import dataclass, field

import pymupdf

# Area util: fora dela ficam o logo do topo, o rodape "Unauthorized copying"
# e o numero da pagina.
CONTENT_TOP = 105.0
CONTENT_BOTTOM = 745.0

# Divisor pontilhado entre as colunas
DIVIDER_X_MIN, DIVIDER_X_MAX = 288.0, 318.0
PAGE_MID = 306.0

BODY_FONT_RE = re.compile(r"MinionPro", re.I)
JUNK_FONT_RE = re.compile(r"HiddenHorzOCR|Helvetica|Times|MyriadPro", re.I)
NUMERIC_RE = re.compile(r"\d{1,2}")

MODULE_ORDER = [
    ("reading_writing", 1),
    ("reading_writing", 2),
    ("math", 1),
    ("math", 2),
]
EXPECTED_COUNTS = {"reading_writing": 33, "math": 27}


@dataclass
class Span:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float
    font: str

    @property
    def is_body_font(self) -> bool:
        return bool(BODY_FONT_RE.search(self.font))

    @property
    def is_junk_font(self) -> bool:
        return bool(JUNK_FONT_RE.search(self.font))


@dataclass
class QuestionRegion:
    number: int
    page: int          # 0-indexed, pagina onde a questao COMECA
    col: int           # 0 = esquerda / unica, 1 = direita
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0
    two_column: bool = True
    spans: list = field(default_factory=list)
    # Uma questao pode transbordar para a coluna/pagina seguinte sem repetir o
    # numero (o caso classico: grafico numa coluna, pergunta e alternativas na
    # outra). Por isso a regiao e uma lista de retangulos, nao um so.
    rects: list = field(default_factory=list)   # [(page_no, (x0,y0,x1,y1)), ...]

    @property
    def bbox(self):
        return (self.x0, self.y0, self.x1, self.y1)

    @property
    def spans_across(self) -> bool:
        return len(self.rects) > 1

    def body_text(self) -> str:
        """Texto limpo: so fonte de corpo, em ordem de leitura."""
        good = [s for s in self.spans if s.is_body_font]
        good.sort(key=lambda s: (round(s.y0 / 3), s.x0))
        return " ".join(s.text for s in good).strip()

    def raw_text(self) -> str:
        good = sorted(self.spans, key=lambda s: (round(s.y0 / 3), s.x0))
        return " ".join(s.text for s in good).strip()


def page_spans(page) -> list:
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] == 1:  # bloco de imagem
            continue
        for line in b["lines"]:
            for s in line["spans"]:
                if not s["text"].strip():
                    continue
                x0, y0, x1, y1 = s["bbox"]
                if y1 < CONTENT_TOP or y0 > CONTENT_BOTTOM:
                    continue
                out.append(Span(s["text"], x0, y0, x1, y1, s["size"], s["font"]))
    return out


def is_two_column(spans: list) -> bool:
    """
    Detecta o layout por geometria, nao pelo divisor pontilhado: o teste 11 usa
    duas colunas SEM divisor, e depender do ornamento fazia a pagina inteira ser
    lida como coluna unica.

    Regra: ha texto de corpo comecando na metade direita e nenhum texto de corpo
    atravessa a linha central. Uma tabela/grafico de largura total sempre produz
    spans que cruzam o meio, entao cai para coluna unica.
    """
    body = [s for s in spans if s.is_body_font]
    if not body:
        return False
    crossing = [s for s in body if s.x0 < PAGE_MID - 6 and s.x1 > PAGE_MID + 6]
    right = [s for s in body if s.x0 >= PAGE_MID]
    return bool(right) and not crossing


def column_of(span: Span, two_col: bool) -> int:
    return 1 if (two_col and span.x0 >= PAGE_MID) else 0


def column_bounds(col: int, two_col: bool):
    if not two_col:
        return (36.0, 578.0)
    return (36.0, 300.0) if col == 0 else (314.0, 578.0)


def _alone_on_line(cand: Span, spans: list) -> bool:
    """
    True se nenhum outro span de corpo compartilha a faixa vertical do candidato.

    E o que separa um numero de questao (isolado acima do enunciado) de um numero
    dentro de celula de tabela (que sempre tem vizinhos na mesma linha).
    """
    for s in spans:
        if s is cand or not s.is_body_font:
            continue
        if s.y0 < cand.y1 - 1 and s.y1 > cand.y0 + 1:  # sobreposicao vertical
            return False
    return True


def find_question_markers(spans: list, page_no: int, two_col: bool):
    markers = []
    for col in ((0, 1) if two_col else (0,)):
        col_spans = [s for s in spans if column_of(s, two_col) == col]
        body = [
            s for s in col_spans
            if s.is_body_font and not NUMERIC_RE.fullmatch(s.text.strip())
        ]
        if not body:
            continue
        margin = min(s.x0 for s in body)
        for s in col_spans:
            if not s.is_body_font or s.size < 9.5:
                continue
            if not NUMERIC_RE.fullmatch(s.text.strip()):
                continue
            # Na margem ou a esquerda dela. A tolerancia e generosa porque em
            # paginas de coluna unica uma celula de tabela pode comecar a
            # esquerda do numero da questao; quem remove o ruido de verdade e o
            # _alone_on_line abaixo, somado a validacao de sequencia.
            if s.x0 > margin + 8.0:
                continue
            if not _alone_on_line(s, col_spans):
                continue
            markers.append(
                QuestionRegion(
                    number=int(s.text.strip()), page=page_no, col=col,
                    y0=s.y0, two_column=two_col,
                )
            )
    markers.sort(key=lambda m: (m.col, m.y0))
    return markers


def segment_pdf(path: str):
    """
    Percorre os slots (pagina, coluna) em ordem de leitura montando as questoes.

    Conteudo que aparece num slot ANTES do primeiro numero de questao daquele
    slot e continuacao da questao anterior -- exceto na fronteira de modulo,
    onde esse conteudo e a pagina de DIRECTIONS/REFERENCE e nao pertence a
    questao nenhuma. A fronteira e reconhecida porque o proximo numero de
    questao volta a ser 1.
    """
    doc = pymupdf.open(path)

    # 1) monta os slots em ordem de leitura
    slots = []
    for pno in range(doc.page_count):
        spans = page_spans(doc[pno])
        if not spans:
            continue
        two_col = is_two_column(spans)
        markers = find_question_markers(spans, pno, two_col)
        for col in ((0, 1) if two_col else (0,)):
            col_spans = [s for s in spans if column_of(s, two_col) == col]
            if not any(s.is_body_font for s in col_spans):
                continue
            slots.append({
                "page": pno,
                "col": col,
                "two_col": two_col,
                "spans": col_spans,
                "markers": [m for m in markers if m.col == col],
                "bounds": column_bounds(col, two_col),
            })

    regions = []
    open_region = None

    for si, slot in enumerate(slots):
        cx0, cx1 = slot["bounds"]
        col_spans = slot["spans"]
        col_markers = slot["markers"]

        # --- conteudo antes do primeiro marcador: continuacao ou directions?
        body = [s for s in col_spans if s.is_body_font]
        top = min(s.y0 for s in body)
        first_y = col_markers[0].y0 if col_markers else CONTENT_BOTTOM

        if open_region is not None and top < first_y - 5:
            next_number = col_markers[0].number if col_markers else _peek_next(
                slots, si + 1
            )
            at_module_boundary = next_number == 1
            if not at_module_boundary:
                rect = (cx0, CONTENT_TOP, cx1, first_y - 2.0)
                open_region.rects.append((slot["page"], rect))
                open_region.spans.extend(
                    s for s in col_spans if CONTENT_TOP <= s.y0 < first_y - 2.0
                )

        # --- questoes que comecam neste slot
        for i, m in enumerate(col_markers):
            m.x0, m.x1 = cx0, cx1
            m.y1 = (
                col_markers[i + 1].y0 - 2.0
                if i + 1 < len(col_markers)
                else CONTENT_BOTTOM
            )
            m.spans = [s for s in col_spans if m.y0 - 1 <= s.y0 < m.y1]
            m.rects = [(m.page, (m.x0, m.y0, m.x1, m.y1))]
            regions.append(m)
            open_region = m

    return doc, regions


def _peek_next(slots, start: int):
    """Numero da proxima questao a aparecer a partir do slot `start`."""
    for s in slots[start:]:
        if s["markers"]:
            return s["markers"][0].number
    return None


def assign_modules(regions: list):
    """
    Agrupa as questoes em modulos pelo reinicio da numeracao e valida a
    sequencia. Retorna (modulos_rotulados, problemas) -- nada e descartado
    em silencio.
    """
    modules, cur, prev = [], [], 0
    for r in regions:
        if r.number <= prev and cur:
            modules.append(cur)
            cur = []
        cur.append(r)
        prev = r.number
    if cur:
        modules.append(cur)

    problems = []
    labelled = []
    for i, mod in enumerate(modules):
        section, module_no = MODULE_ORDER[i] if i < len(MODULE_ORDER) else ("?", 0)
        nums = [r.number for r in mod]
        expected = EXPECTED_COUNTS.get(section)
        if nums != list(range(1, len(nums) + 1)):
            problems.append(f"{section} M{module_no}: sequencia irregular {nums}")
        elif expected and len(nums) != expected:
            missing = sorted(set(range(1, expected + 1)) - set(nums))
            problems.append(
                f"{section} M{module_no}: {len(nums)}/{expected}, faltando {missing}"
            )
        labelled.append((section, module_no, mod))

    if len(modules) != 4:
        problems.append(f"esperava 4 modulos, encontrou {len(modules)}")
    return labelled, problems


if __name__ == "__main__":
    import sys, io, glob, os
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    total = 0
    for path in sorted(glob.glob("../pdfs/sat-practice-test-*-digital.pdf")):
        if "answers" in path:
            continue
        doc, regions = segment_pdf(path)
        labelled, problems = assign_modules(regions)
        counts = [len(m) for _, _, m in labelled]
        total += sum(counts)
        status = "OK" if not problems else " | ".join(problems)
        print(f"{os.path.basename(path):42s} {counts}  {status}")
    print("total de questoes:", total)
