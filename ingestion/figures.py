"""
Recorta APENAS a figura de uma questao (grafico, tabela, diagrama), nao a
questao inteira.

O enunciado e as alternativas vao para o banco como texto + LaTeX; imagem so
existe quando a questao tem algo que nao da para escrever: um grafico, uma
tabela, um diagrama.

Como a figura e localizada
--------------------------
Os graficos do PDF sao desenho vetorial, entao a assinatura deles e um aglomerado
de `drawings` dentro da regiao da questao. Junto vem a camada de OCR invisivel
(fontes Times/Helvetica/HiddenHorzOCR) com os rotulos dos eixos, que tambem
pertence a figura. Tabelas sao um caso a parte: as linhas sao drawings, mas o
conteudo e texto de corpo de verdade, entao o bbox precisa englobar as celulas.
"""
import pymupdf

from segment import CONTENT_TOP, CONTENT_BOTTOM

PAD = 5.0
MIN_DRAW_AREA = 60.0        # ignora fiapos: sublinhados, bullets, cantos
MIN_FIGURE_AREA = 2500.0    # abaixo disso nao e figura de verdade


def _region_rects(region):
    return region.rects or [(region.page, region.bbox)]


def _drawing_cluster(page, clip):
    """Uniao dos desenhos vetoriais relevantes dentro do recorte."""
    box = None
    count = 0
    for d in page.get_drawings():
        r = pymupdf.Rect(d["rect"])
        if not r.intersects(clip):
            continue
        r = r & clip
        if r.is_empty or r.get_area() < MIN_DRAW_AREA:
            continue
        # linhas muito finas e muito compridas sao regua/divisor, nao figura
        if (r.width > clip.width * 0.9 and r.height < 3) or (
            r.height > clip.height * 0.9 and r.width < 3
        ):
            continue
        box = r if box is None else (box | r)
        count += 1
    return box, count


def _text_touching(page, clip, box, body_only=False):
    """Expande o box com o texto que faz parte da figura (rotulos, celulas)."""
    grown = pymupdf.Rect(box)
    for b in page.get_text("dict")["blocks"]:
        if b["type"] == 1:
            continue
        for line in b["lines"]:
            for s in line["spans"]:
                if not s["text"].strip():
                    continue
                r = pymupdf.Rect(s["bbox"])
                if not r.intersects(clip):
                    continue
                font = s["font"]
                is_junk = any(
                    k in font
                    for k in ("HiddenHorzOCR", "Helvetica", "Times", "Euclid")
                )
                if body_only and is_junk:
                    continue
                if not body_only and not is_junk:
                    # texto de corpo so entra se estiver DENTRO do aglomerado
                    if not grown.contains(r):
                        continue
                # rotulo de eixo pode ficar logo fora da moldura
                near = pymupdf.Rect(grown)
                near.x0 -= 24; near.y0 -= 24; near.x1 += 24; near.y1 += 24
                if near.intersects(r):
                    grown |= (r & clip)
    return grown


def figure_bbox(doc, region, kind: str | None):
    """
    Retorna (page_no, bbox) da figura da questao, ou None se nao houver.

    `kind` vem da extracao por visao ('graph' | 'table' | 'diagram' | ...) e
    decide o quanto o texto de corpo participa do recorte: numa tabela o texto
    E a figura; num grafico o texto de corpo e o enunciado e fica de fora.
    """
    if kind == "table":
        # Tabela nao vira imagem: e transcrita como tabela Markdown, que
        # responde ao tema, ao zoom e ao leitor de tela.
        return None

    for pno, bbox in _region_rects(region):
        page = doc[pno]
        clip = pymupdf.Rect(*bbox)
        # +14 pula o numero da questao, que fica na margem acima do conteudo
        clip.y0 = max(clip.y0 + 14, CONTENT_TOP)
        clip.y1 = min(clip.y1, CONTENT_BOTTOM)
        if clip.is_empty:
            continue

        box, count = _drawing_cluster(page, clip)
        if box is None or count < 3:
            continue

        box = _text_touching(page, clip, box, body_only=False)
        box.x0 -= PAD; box.y0 -= PAD; box.x1 += PAD; box.y1 += PAD
        box &= clip
        if box.is_empty or box.get_area() < MIN_FIGURE_AREA:
            continue
        # O PRIMEIRO recorte com desenho e o do enunciado. Pegar o de maior
        # area escolheria a pagina das alternativas graficas, que e maior.
        return pno, (box.x0, box.y0, box.x1, box.y1)

    return None


# --------------------------------------------------------------------------
# Alternativas que sao graficos (ex.: "qual sera o grafico resultante")
# --------------------------------------------------------------------------

def choice_graphic_boxes(doc, region):
    """
    Localiza o recorte de cada alternativa grafica usando os rotulos "A)".."D)"
    como ancoras. Devolve {label: (page_no, bbox)} ou {} se nao der para separar.

    Os quatro graficos costumam vir num grid 2x2; cada alternativa vai do seu
    rotulo ate o rotulo seguinte na mesma faixa (a direita) e ate a proxima
    faixa (abaixo).
    """
    for pno, bbox in _region_rects(region):
        page = doc[pno]
        clip = pymupdf.Rect(*bbox)
        labels = {}
        for b in page.get_text("dict")["blocks"]:
            if b["type"] == 1:
                continue
            for line in b["lines"]:
                for s in line["spans"]:
                    t = s["text"].strip()
                    if t in ("A)", "B)", "C)", "D)") and "MinionPro" in s["font"]:
                        r = pymupdf.Rect(s["bbox"])
                        if r.intersects(clip):
                            labels[t[0]] = r
        if len(labels) != 4:
            continue

        # agrupa em linhas pelo y do rotulo
        items = sorted(labels.items(), key=lambda kv: (round(kv[1].y0 / 20), kv[1].x0))
        rows = {}
        for lab, r in items:
            rows.setdefault(round(r.y0 / 20), []).append((lab, r))
        row_keys = sorted(rows)

        out = {}
        for ri, rk in enumerate(row_keys):
            row = sorted(rows[rk], key=lambda kv: kv[1].x0)
            y0 = min(r.y0 for _, r in row) - 4
            if ri + 1 < len(row_keys):
                y1 = min(r.y0 for _, r in rows[row_keys[ri + 1]]) - 6
            else:
                y1 = clip.y1
            for ci, (lab, r) in enumerate(row):
                x0 = r.x0 - 4
                x1 = row[ci + 1][1].x0 - 6 if ci + 1 < len(row) else clip.x1
                box = pymupdf.Rect(x0, y0, x1, y1) & clip
                if not box.is_empty and box.get_area() > MIN_FIGURE_AREA:
                    out[lab] = (pno, (box.x0, box.y0, box.x1, box.y1))
        if len(out) == 4:
            return out
    return {}
