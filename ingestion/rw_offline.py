"""
Extracao de Reading & Writing SEM chamar a API.

Por que da para fazer offline
-----------------------------
O problema que obrigou a usar visao e exclusivo de Math: as formulas vem
desmontadas em spans posicionados. Em R&W o texto do PDF e limpo e continuo,
e o enunciado do SAT e formulaico -- quatro perguntas cobrem 59% das questoes
e o resto segue padroes fechados. Entao aqui:

  * enunciado, alternativas e passagem saem direto do texto, pelas posicoes
    dos rotulos "A)" ... "D)";
  * a resposta correta e o rationale saem do PDF oficial de respostas;
  * a skill sai do proprio enunciado, por regra.

O unico caso que precisa de julgamento e "conforms to the conventions of
Standard English", que pode ser Boundaries ou Form/Structure/Sense. A diferenca
esta nas ALTERNATIVAS: se elas variam a pontuacao entre oracoes, e Boundaries;
se variam forma verbal, pronome ou plural, e Form, Structure, and Sense.
"""
import re

import pymupdf

from segment import BODY_FONT_RE

CHOICE_RE = re.compile(r"^([A-D])\)")

# ---------------------------------------------------------------------------
# Classificacao por enunciado. A ordem importa: a primeira regra que casar vence.
# ---------------------------------------------------------------------------
STEM_RULES = [
    (r"conforms to the conventions of Standard English", "CONVENTIONS"),
    (r"most logical and precise word or phrase",         "words_in_context"),
    (r"most logical transition",                          "transitions"),
    (r"relevant information from the notes",              "rhetorical_synthesis"),
    (r"uses data from the (table|graph)",                 "command_of_evidence"),
    (r"data (in|from) the (table|graph)",                 "command_of_evidence"),
    (r"Which (finding|quotation)[^?]*(support|illustrate)", "command_of_evidence"),
    (r"most effectively illustrates the claim",           "command_of_evidence"),
    (r"would (most likely )?(respond|characterize)",      "cross_text_connections"),
    (r"author of Text 2",                                  "cross_text_connections"),
    (r"both texts|Based on the texts",                     "cross_text_connections"),
    (r"overall structure of the text",                     "text_structure_and_purpose"),
    (r"main purpose of the text",                          "text_structure_and_purpose"),
    (r"function of the (underlined|second|first)",         "text_structure_and_purpose"),
    (r"structure of the text",                             "text_structure_and_purpose"),
    (r"main idea of the text",                             "central_ideas_and_details"),
    (r"According to the text",                             "central_ideas_and_details"),
    (r"best describes",                                    "central_ideas_and_details"),
    (r"most logically completes the text",                 "inferences"),
    (r"logically completes",                               "inferences"),
]

DOMAIN_OF = {
    "words_in_context": "craft_and_structure",
    "text_structure_and_purpose": "craft_and_structure",
    "cross_text_connections": "craft_and_structure",
    "central_ideas_and_details": "information_and_ideas",
    "command_of_evidence": "information_and_ideas",
    "inferences": "information_and_ideas",
    "rhetorical_synthesis": "expression_of_ideas",
    "transitions": "expression_of_ideas",
    "boundaries": "standard_english_conventions",
    "form_structure_and_sense": "standard_english_conventions",
}

# Conjuncoes coordenativas: numa questao de Boundaries elas entram e saem junto
# com a pontuacao, sem que o nucleo lexical mude.
COORD = r"(?:and|but|or|so|yet|for|nor)"
STRONG_BOUNDARY = re.compile(r"[;:—–]")


def _core(text: str) -> str:
    """Nucleo lexical: sem pontuacao e sem conjuncoes coordenativas."""
    t = re.sub(r"[^\w\s]", " ", text.lower())
    t = re.sub(rf"\b{COORD}\b", " ", t)
    return " ".join(t.split())


def split_conventions(choices) -> str:
    """
    Distingue Boundaries de Form, Structure, and Sense pelo que varia entre as
    alternativas.

    Boundaries troca a fronteira entre oracoes -- pontuacao e, junto com ela, a
    conjuncao coordenativa. O nucleo lexical continua o mesmo:
        "out but" / "out, but" / "out" / "out,"   -> boundaries

    Form/Structure/Sense troca a forma da palavra: tempo verbal, concordancia,
    pronome, plural ou possessivo. Ai o nucleo muda:
        "forces" / "to force" / "forcing" / "forced"        -> form
        "its" / "they're" / "their" / "it's"                -> form
    """
    texts = [c["content_md"].strip() for c in choices]
    if len(texts) < 2:
        return "form_structure_and_sense"

    # nucleo igual em todas -> so a fronteira muda
    if len({_core(t) for t in texts}) == 1:
        return "boundaries"

    # ponto e virgula, dois pontos ou travessao so aparecem em Boundaries
    if any(STRONG_BOUNDARY.search(t) for t in texts):
        return "boundaries"

    return "form_structure_and_sense"


def classify(stem: str, choices) -> tuple[str, str, float]:
    """Retorna (domain_code, skill_code, confianca)."""
    for pattern, skill in STEM_RULES:
        if re.search(pattern, stem, re.I):
            if skill == "CONVENTIONS":
                skill = split_conventions(choices)
                return DOMAIN_OF[skill], skill, 0.85
            return DOMAIN_OF[skill], skill, 0.95

    # sem padrao reconhecido: a lacuna no fim do texto e a marca de Inferences
    if re.search(r"_{3,}|b l a n k|\bblank\b", stem, re.I):
        return DOMAIN_OF["inferences"], "inferences", 0.6
    return DOMAIN_OF["central_ideas_and_details"], "central_ideas_and_details", 0.4


# ---------------------------------------------------------------------------
# Estrutura da questao a partir dos spans
# ---------------------------------------------------------------------------

def _ordered_spans(region):
    """Spans de corpo em ordem de leitura, com o indice do recorte de origem."""
    out = []
    rects = region.rects or [(region.page, region.bbox)]
    for ri, (pno, bbox) in enumerate(rects):
        for s in region.spans:
            if not BODY_FONT_RE.search(s.font):
                continue
            if bbox[1] - 1 <= s.y0 < bbox[3] and bbox[0] <= s.x0 < bbox[2]:
                out.append((ri, s))
    out.sort(key=lambda t: (t[0], round(t[1].y0 / 3), t[1].x0))
    return out


def parse_question(region):
    """
    Separa passagem, enunciado e alternativas.
    Retorna None quando a estrutura nao bate (a questao entao vai para visao).
    """
    spans = _ordered_spans(region)
    if not spans:
        return None

    # localiza os rotulos das alternativas: span que COMECA com "A)" .. "D)"
    marks = {}
    for i, (ri, s) in enumerate(spans):
        m = CHOICE_RE.match(s.text.strip())
        if m and m.group(1) not in marks:
            marks[m.group(1)] = i
    if sorted(marks) != ["A", "B", "C", "D"]:
        return None
    order = [marks[l] for l in ("A", "B", "C", "D")]
    if order != sorted(order):
        return None

    def join(a, b):
        txt = " ".join(s.text for _, s in spans[a:b])
        txt = re.sub(r"\s+", " ", txt)
        # A prova 11 desenha a lacuna como as letras de "blank" espacadas;
        # as outras usam sublinhados. Normaliza para uma lacuna so.
        txt = re.sub(r"\bb\s*l\s*a\s*n\s*k\b", "______", txt, flags=re.I)
        txt = re.sub(r"_{2,}", "______", txt)
        txt = re.sub(r"\s+([,.;:?!])", r"\1", txt)
        return txt.strip()

    choices = []
    for j, label in enumerate(("A", "B", "C", "D")):
        start = marks[label]
        end = order[j + 1] if j + 1 < 4 else len(spans)
        body = join(start, end)
        body = CHOICE_RE.sub("", body, count=1).strip()
        choices.append({"label": label, "content_md": body,
                        "is_graphic": False})

    head = join(0, order[0])
    # o numero da questao abre o bloco; remove
    head = re.sub(r"^\d{1,2}\s+", "", head)

    # o enunciado e a ultima frase interrogativa do cabecalho
    qs = list(re.finditer(r"[^.?!]*\?", head))
    if qs:
        prompt = qs[-1].group(0).strip()
        stimulus = head[: qs[-1].start()].strip()
    else:
        # questoes de convencoes as vezes terminam em ":" e nao em "?"
        parts = head.rsplit(". ", 1)
        prompt = parts[-1].strip()
        stimulus = parts[0].strip() if len(parts) > 1 else ""

    if not prompt or not all(c["content_md"] for c in choices):
        return None

    return {
        "stimulus_md": stimulus or None,
        "prompt_md": prompt,
        "choices": choices,
    }


# ---------------------------------------------------------------------------
# Rationale do PDF oficial de respostas
# ---------------------------------------------------------------------------
SPLIT_RE = re.compile(r"(Choice\s+[A-D]\s+is\s+(?:the\s+best\s+answer|correct|incorrect))",
                      re.I)


def parse_rationale(answer_text: str, correct: str):
    """Separa a explicacao da correta das explicacoes dos distratores."""
    text = re.sub(r"\s+", " ", answer_text).strip()
    parts = SPLIT_RE.split(text)
    if len(parts) < 3:
        return text, {}

    chunks = []
    for i in range(1, len(parts), 2):
        head = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        label = re.search(r"Choice\s+([A-D])", head, re.I).group(1).upper()
        chunks.append((label, (head + body).strip()))

    rationale, distractors = "", {}
    for label, chunk in chunks:
        if label == correct and not rationale:
            rationale = chunk
        elif label != correct:
            distractors[label] = chunk
    return rationale or text, distractors


# ---------------------------------------------------------------------------
# Figura: R&W tambem tem tabela e grafico. Sem visao para transcrever, a figura
# e recortada como imagem, exatamente como em Math.
# ---------------------------------------------------------------------------

def has_visual(doc, region) -> bool:
    rects = region.rects or [(region.page, region.bbox)]
    for pno, bbox in rects:
        clip = pymupdf.Rect(*bbox)
        n = 0
        for d in doc[pno].get_drawings():
            r = pymupdf.Rect(d["rect"]) & clip
            if not r.is_empty and r.get_area() > 200:
                n += 1
                if n >= 4:
                    return True
    return False
