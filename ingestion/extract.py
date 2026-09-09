"""
Estagio de visao: transforma uma regiao de questao + a explicacao oficial
correspondente em um registro estruturado, pronto para o banco.

Por que visao e nao regex
-------------------------
No caderno de Math as formulas vem desmontadas em spans posicionados: numerador
e denominador viram spans separados, expoentes so se distinguem por delta-Y e
corpo 8.4 vs 10.5, parenteses vem numa fonte EuclidSymbol. Reconstruir LaTeX
disso por regra erra fracao, radical e matriz. O recorte renderizado mostra a
formula como ela e, entao o modelo transcreve o que ve.

A resposta correta NAO e decidida pelo modelo: ela vem parseada do PDF oficial
de respostas e e passada como fato no prompt. O modelo transcreve e classifica,
nao resolve. Isso mantem o gabarito oficial e evita alucinacao.
"""
import base64
import json
import os
import re

import pymupdf
from anthropic import Anthropic

from taxonomy import taxonomy_prompt, VALID_SKILL_CODES, skills_for

ZOOM = 3.0  # ~216 dpi: legivel para o modelo sem estourar o limite de imagem

_client = None


def client() -> Anthropic:
    global _client
    if _client is None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY nao definida (ver .env)")
        _client = Anthropic(api_key=key)
    return _client


PAD = 6.0


def tight_bbox(doc, page_no: int, bbox):
    """
    Encolhe o retangulo ate o conteudo que realmente existe dentro dele.

    A regiao bruta vai ate o rodape da coluna; quando a questao e curta, ou
    quando a pagina foi tratada como coluna unica por ter a metade direita
    vazia, sobra area em branco que so gasta token e diminui a nitidez efetiva.
    Considera texto, desenhos vetoriais (os graficos) e imagens embutidas.
    """
    page = doc[page_no]
    clip = pymupdf.Rect(*bbox)
    boxes = []

    for b in page.get_text("dict")["blocks"]:
        r = pymupdf.Rect(b["bbox"])
        if r.intersects(clip) and not r.is_empty:
            boxes.append(r & clip)

    for d in page.get_drawings():
        r = pymupdf.Rect(d["rect"])
        if r.intersects(clip) and not r.is_empty:
            boxes.append(r & clip)

    if not boxes:
        return bbox

    x0 = min(r.x0 for r in boxes) - PAD
    y0 = min(r.y0 for r in boxes) - PAD
    x1 = max(r.x1 for r in boxes) + PAD
    y1 = max(r.y1 for r in boxes) + PAD
    tight = pymupdf.Rect(x0, y0, x1, y1) & clip
    if tight.is_empty or tight.width < 20 or tight.height < 20:
        return bbox
    return (tight.x0, tight.y0, tight.x1, tight.y1)


def render_crop(doc, page_no: int, bbox, zoom: float = ZOOM, tight: bool = True) -> bytes:
    """Renderiza um retangulo da pagina como PNG."""
    if tight:
        bbox = tight_bbox(doc, page_no, bbox)
    page = doc[page_no]
    clip = pymupdf.Rect(*bbox)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip, alpha=False)
    return pix.tobytes("png")


def _img_block(png: bytes):
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": base64.standard_b64encode(png).decode("ascii"),
        },
    }


EXTRACTION_TOOL = {
    "name": "record_question",
    "description": "Registra a questao do SAT transcrita e classificada.",
    "input_schema": {
        "type": "object",
        "properties": {
            "question_type": {
                "type": "string",
                "enum": ["multiple_choice", "grid_in"],
            },
            "stimulus_md": {
                "type": ["string", "null"],
                "description": (
                    "Passagem, texto-base, notas em bullets, legenda de tabela ou "
                    "contexto que precede a pergunta. null se a questao nao tiver. "
                    "Markdown; matematica em LaTeX entre $...$."
                ),
            },
            "prompt_md": {
                "type": "string",
                "description": (
                    "A pergunta em si (ex.: 'Which choice completes the text...'). "
                    "Markdown; matematica em LaTeX entre $...$."
                ),
            },
            "choices": {
                "type": "array",
                "description": "Vazio para grid_in.",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string", "enum": ["A", "B", "C", "D"]},
                        "content_md": {"type": "string"},
                        "is_graphic": {
                            "type": "boolean",
                            "description": (
                                "true quando a alternativa E um grafico/figura em "
                                "vez de texto (ex.: 'qual sera o grafico "
                                "resultante'). Nesse caso content_md e uma "
                                "descricao curta."
                            ),
                        },
                    },
                    "required": ["label", "content_md", "is_graphic"],
                },
            },
            "has_figure": {
                "type": "boolean",
                "description": (
                    "true se o ENUNCIADO tem figura, grafico ou tabela que o aluno "
                    "precisa ver para responder."
                ),
            },
            "figure_kind": {
                "type": ["string", "null"],
                "enum": ["graph", "table", "diagram", "illustration", None],
            },
            "figure_alt_text": {
                "type": ["string", "null"],
                "description": "Descricao da figura para acessibilidade.",
            },
            "correct_answer_text": {
                "type": ["string", "null"],
                "description": (
                    "Somente grid_in: o valor correto normalizado, lido da "
                    "explicacao oficial (ex.: '3/29', '11875', '1.5')."
                ),
            },
            "correct_answer_alternates": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Somente grid_in: outras formas aceitaveis do mesmo valor "
                    "(ex.: para 1/4 -> ['0.25', '.25'])."
                ),
            },
            "rationale_md": {
                "type": "string",
                "description": (
                    "A explicacao oficial da resposta CORRETA, transcrita da "
                    "imagem da explicacao, com LaTeX nas formulas. Nao resumir "
                    "nem reescrever com suas palavras."
                ),
            },
            "distractor_rationales": {
                "type": "object",
                "description": (
                    "Mapa label -> explicacao oficial de por que a alternativa "
                    "esta errada, quando o PDF trouxer. Ex.: {'A': '...'}."
                ),
                "additionalProperties": {"type": "string"},
            },
            "domain_code": {"type": "string"},
            "skill_code": {"type": "string"},
            "classification_confidence": {
                "type": "number",
                "description": "0.0 a 1.0.",
            },
            "classification_reason": {
                "type": "string",
                "description": "Uma frase justificando a skill escolhida.",
            },
        },
        "required": [
            "question_type", "prompt_md", "choices", "has_figure",
            "rationale_md", "domain_code", "skill_code",
            "classification_confidence", "classification_reason",
        ],
    },
}


SYSTEM = """Voce transcreve questoes oficiais do Digital SAT a partir de recortes \
de PDF e as classifica na taxonomia oficial do College Board.

REGRAS DE TRANSCRICAO
- Transcreva EXATAMENTE o que esta na imagem. Nao corrija, resuma nem reescreva.
- Toda matematica vai em LaTeX entre $...$ (inline) ou $$...$$ (bloco). Nunca
  deixe formula como texto cru tipo "x^2+3x" ou "t 10 <= 75".
- O texto extraido do PDF vem junto como apoio para grafia de nomes proprios,
  mas ele esta corrompido nas formulas e contem lixo de OCR dos graficos
  (sequencias como "6 -4 -2 IU , 2"). Onde texto e imagem divergirem, a IMAGEM
  manda. Nunca inclua o lixo de OCR na transcricao.
- Separe stimulus_md (passagem/contexto/tabela) de prompt_md (a pergunta).
- TABELA nunca vira imagem: transcreva como tabela Markdown com pipes, dentro de
  stimulus_md, mantendo o titulo da tabela como linha em negrito acima dela.
  Preserve todas as linhas e colunas, na mesma ordem.
- GRAFICO, DIAGRAMA e ILUSTRACAO nao sao transcritos: sao recortados como imagem
  a parte. Nesses casos descreva o essencial em figure_alt_text e nao tente
  desenhar o grafico em texto.
- Ignore cabecalho, rodape ("Unauthorized copying..."), numero de pagina,
  "CONTINUE" e o numero da questao.

REGRAS DE RESPOSTA
- A resposta correta ja foi extraida do PDF oficial e esta no prompt. NAO
  resolva a questao e nao a contradiga.
- rationale_md e a explicacao da alternativa correta, transcrita da imagem da
  explicacao oficial, com as formulas em LaTeX.

REGRAS DE CLASSIFICACAO
- Escolha exatamente um skill_code da taxonomia fornecida, e o domain_code do
  dominio ao qual esse skill pertence. Nao invente codigos.
- classification_confidence deve refletir sua duvida real: use abaixo de 0.7
  quando duas skills forem defensaveis."""


def build_user_content(qregion, aregion, doc_q, doc_a, section: str):
    content = []

    qrects = qregion.rects or [(qregion.page, qregion.bbox)]
    plural = (
        " A questao ocupa mais de um recorte: o conteudo continua na coluna/"
        "pagina seguinte (tipicamente o grafico num recorte e a pergunta com as "
        "alternativas no outro). Trate todos como UMA questao so."
        if len(qrects) > 1 else ""
    )
    content.append({
        "type": "text",
        "text": (
            f"SECAO: {section}\n"
            f"Questao numero {qregion.number} do modulo {aregion.module}.\n"
            f"=== {len(qrects)} IMAGEM(NS) do caderno ==={plural}"
        ),
    })
    for pno, rect in qrects:
        content.append(_img_block(render_crop(doc_q, pno, rect)))

    content.append({
        "type": "text",
        "text": "=== IMAGEM(NS) seguintes: explicacao oficial da resposta ===",
    })
    for pno, rect in aregion.rects[:3]:   # explicacoes longas cruzam paginas
        content.append(_img_block(render_crop(doc_a, pno, rect)))

    correct = aregion.correct_choice()
    if correct:
        fact = f"A resposta correta oficial e a alternativa {correct}."
    else:
        fact = (
            "Esta e uma questao de resposta construida (grid-in), sem "
            "alternativas. O valor correto oficial aparece na explicacao como "
            f"'The correct answer is ...' (texto bruto: "
            f"{aregion.correct_answer_text()!r}). Normalize-o em "
            "correct_answer_text."
        )

    content.append({
        "type": "text",
        "text": (
            f"FATO OFICIAL: {fact}\n\n"
            "=== texto extraido do caderno (apoio, corrompido nas formulas) ===\n"
            f"{qregion.body_text()[:4000]}\n\n"
            "=== texto extraido da explicacao (apoio) ===\n"
            f"{aregion.text[:6000]}\n\n"
            "=== TAXONOMIA OFICIAL PARA ESTA SECAO ===\n"
            f"{taxonomy_prompt(section)}\n\n"
            "Chame a ferramenta record_question com o resultado."
        ),
    })
    return content


def extract_question(qregion, aregion, doc_q, doc_a, section: str, model: str):
    """Uma chamada de visao -> dict estruturado. Levanta em caso de falha."""
    resp = client().messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM,
        tools=[EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "record_question"},
        messages=[{"role": "user", "content": build_user_content(
            qregion, aregion, doc_q, doc_a, section
        )}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            data = dict(block.input)
            _validate(data, section, aregion)
            return data, resp.usage
    raise RuntimeError("modelo nao chamou a ferramenta")


def _validate(data: dict, section: str, aregion):
    """Falha alto: erro de classificacao silencioso contamina o dataset."""
    if data.get("skill_code") not in VALID_SKILL_CODES[section]:
        raise ValueError(
            f"skill_code invalido para {section}: {data.get('skill_code')!r}"
        )
    valid_domains = {t[0] for t in skills_for(section)}
    if data.get("domain_code") not in valid_domains:
        raise ValueError(f"domain_code invalido: {data.get('domain_code')!r}")
    # o dominio tem de ser o dono do skill
    owner = {t[2]: t[0] for t in skills_for(section)}[data["skill_code"]]
    if owner != data["domain_code"]:
        data["domain_code"] = owner  # skill manda

    correct = aregion.correct_choice()
    if correct and data.get("question_type") != "multiple_choice":
        raise ValueError("gabarito diz multiple choice, modelo disse grid_in")
    if correct and len(data.get("choices") or []) != 4:
        raise ValueError(
            f"esperava 4 alternativas, veio {len(data.get('choices') or [])}"
        )
