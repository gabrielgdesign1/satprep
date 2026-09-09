"""
Monta a pagina de revisao da amostra: recorte original do PDF lado a lado com o
que o pipeline extraiu, para conferencia manual antes de rodar as 960 questoes.
"""
import base64
import html
import json
import pathlib
import re

import pymupdf
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

from sample import load_test, SAMPLE, OUT          # noqa: E402
from extract import render_crop                     # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SCRATCH = pathlib.Path(
    r"C:\Users\Admin\AppData\Local\Temp\claude"
    r"\C--Users-Admin-Downloads-SatPrep"
    r"\781674ee-a7e1-4c3f-b977-17431afcb2f7\scratchpad"
)
REVIEW_ZOOM = 2.0   # suficiente para conferir; 3.0 estoura o limite da pagina


def katex_css() -> str:
    """CSS do KaTeX com as fontes embutidas como data URI (a CSP bloqueia
    arquivos de fonte externos, entao referencia solta cairia em fallback)."""
    css = (SCRATCH / "katex.css").read_text(encoding="utf-8")
    fonts = {}
    for f in (SCRATCH / "kf").glob("*.woff2"):
        fonts[f.stem] = base64.b64encode(f.read_bytes()).decode("ascii")

    def repl(m):
        name = m.group(1)
        if name in fonts:
            return f"url(data:font/woff2;base64,{fonts[name]}) format(\"woff2\")"
        return "local(\"sans-serif\")"

    # troca a lista woff2/woff/ttf inteira pela versao embutida
    css = re.sub(
        r'url\(fonts/(KaTeX_[\w-]+)\.woff2\) format\("woff2"\),'
        r'url\(fonts/[\w-]+\.woff\) format\("woff"\),'
        r'url\(fonts/[\w-]+\.ttf\) format\("truetype"\)',
        repl,
        css,
    )
    return css


def collect():
    data = json.loads((OUT / "sample.json").read_text(encoding="utf-8"))
    by_tag = {d["tag"]: d for d in data if "error" not in d}
    cache = {}
    items = []

    for test_no, section, module_no, qnum in SAMPLE:
        tag = f"t{test_no}_{section}_m{module_no}_q{qnum}"
        rec = by_tag.get(tag)
        if not rec:
            continue
        if test_no not in cache:
            cache[test_no] = load_test(test_no)
        doc_q, index, doc_a, answers = cache[test_no]
        qregion = index[(section, module_no, qnum)]

        imgs = []
        for pno, rect in (qregion.rects or [(qregion.page, qregion.bbox)]):
            png = render_crop(doc_q, pno, rect, zoom=REVIEW_ZOOM)
            imgs.append(base64.b64encode(png).decode("ascii"))
        rec["_images"] = imgs
        rec["_pages"] = [p + 1 for p, _ in (qregion.rects or [(qregion.page, 0)])]
        items.append(rec)
    return items


def esc(s):
    return html.escape(s or "", quote=True)


CONF_CLASS = lambda c: "high" if c >= 0.9 else ("mid" if c >= 0.7 else "low")

SKILL_LABEL = {}


def build():
    items = collect()
    from taxonomy import skills_for
    for sec in ("reading_writing", "math"):
        for dcode, dname, scode, sname, _ in skills_for(sec):
            SKILL_LABEL[scode] = (dname, sname)

    cards = []
    for i, r in enumerate(items):
        sec_label = "Reading & Writing" if r["section"] == "reading_writing" else "Math"
        dname, sname = SKILL_LABEL.get(r["skill_code"], ("?", r["skill_code"]))
        conf = r["classification_confidence"]

        imgs = "\n".join(
            f'<img src="data:image/png;base64,{b64}" alt="Recorte {j+1} do PDF '
            f'original, pagina {r["_pages"][j] if j < len(r["_pages"]) else "?"}" '
            f'loading="lazy">'
            for j, b64 in enumerate(r["_images"])
        )

        if r["question_type"] == "grid_in":
            alts = r.get("correct_answer_alternates") or []
            alt_txt = (
                f'<span class="alts">tambem aceita: '
                f'{esc(", ".join(alts))}</span>' if alts else ""
            )
            answer_block = (
                '<div class="gridin">'
                '<span class="lbl">Resposta (grid-in)</span>'
                f'<span class="val">{esc(r.get("correct_answer_text"))}</span>'
                f'{alt_txt}</div>'
            )
        else:
            rows = []
            correct = r.get("official_correct_choice")
            for c in r["choices"]:
                is_ok = c["label"] == correct
                rows.append(
                    f'<li class="{"ok" if is_ok else ""}">'
                    f'<span class="mark">{c["label"]}</span>'
                    f'<span class="body md">{esc(c["content_md"])}</span>'
                    + ('<span class="tick">correta</span>' if is_ok else "")
                    + ('<span class="gfx">grafico</span>' if c.get("is_graphic") else "")
                    + "</li>"
                )
            answer_block = f'<ol class="choices">{"".join(rows)}</ol>'

        stim = (
            f'<div class="stim md">{esc(r["stimulus_md"])}</div>'
            if r.get("stimulus_md") else ""
        )
        figure_note = (
            f'<p class="figalt"><span class="lbl">alt-text da figura</span>'
            f'{esc(r.get("figure_alt_text"))}</p>'
            if r.get("has_figure") and r.get("figure_alt_text") else ""
        )

        distr = r.get("distractor_rationales") or {}
        distr_html = "".join(
            f'<p><b>{esc(k)}</b> <span class="md">{esc(v)}</span></p>'
            for k, v in sorted(distr.items())
        )

        cards.append(f"""
<article class="card" data-section="{r['section']}" id="q{i}">
  <header class="card-head">
    <div class="ident">
      <span class="eyebrow">Prova {r['test_number']} &middot; {sec_label}
        &middot; Modulo {r['module_number']}</span>
      <h2>Questao {r['question_number']}</h2>
    </div>
    <div class="tags">
      <span class="tag type">{'Grid-in' if r['question_type']=='grid_in'
                              else 'Multipla escolha'}</span>
      {'<span class="tag fig">' + esc(r.get('figure_kind') or 'figura') + '</span>'
       if r.get('has_figure') else ''}
      {'<span class="tag multi">' + str(len(r['_images'])) + ' recortes</span>'
       if len(r['_images']) > 1 else ''}
      <span class="tag diff">dificuldade: unrated</span>
    </div>
  </header>

  <div class="split">
    <section class="pane origin">
      <h3 class="pane-title">Original <span class="src">pagina
        {', '.join(str(p) for p in r['_pages'])} do PDF</span></h3>
      <div class="shots">{imgs}</div>
    </section>

    <section class="pane parsed">
      <h3 class="pane-title">Extraido</h3>
      {stim}
      <div class="prompt md">{esc(r['prompt_md'])}</div>
      {answer_block}
      {figure_note}

      <div class="classif">
        <div class="cl-row">
          <span class="lbl">Dominio</span><span>{esc(dname)}</span>
        </div>
        <div class="cl-row">
          <span class="lbl">Skill</span><span>{esc(sname)}</span>
        </div>
        <div class="cl-row">
          <span class="lbl">Confianca</span>
          <span class="conf {CONF_CLASS(conf)}">{conf:.2f}</span>
        </div>
        <p class="why">{esc(r['classification_reason'])}</p>
      </div>

      <details class="rat">
        <summary>Explicacao oficial</summary>
        <div class="md">{esc(r['rationale_md'])}</div>
        {'<div class="distr"><span class="lbl">Por que as outras erram</span>'
         + distr_html + '</div>' if distr_html else ''}
      </details>
    </section>
  </div>

  <footer class="verdict">
    <span class="vlabel">Sua revisao</span>
    <label><input type="radio" name="v{i}" value="ok"><span>Aprovada</span></label>
    <label><input type="radio" name="v{i}" value="bad"><span>Tem erro</span></label>
    <input class="note" type="text" placeholder="o que esta errado (opcional)"
           data-q="{r['test_number']}/{sec_label}/M{r['module_number']}/Q{r['question_number']}">
  </footer>
</article>""")

    n_rw = sum(1 for r in items if r["section"] == "reading_writing")
    n_math = len(items) - n_rw

    doc = f"""<title>Revisao da Extracao SAT</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
{katex_css()}

:root {{
  --paper:      #f6f4ef;
  --surface:    #fffefb;
  --surface-2:  #efece4;
  --ink:        #191b20;
  --graphite:   #5f6470;
  --rule:       #ded8cb;
  --accent:     #1f4d3f;
  --accent-soft:#e2ebe6;
  --amber:      #9c6318;
  --amber-soft: #f6ecdc;
  --crimson:    #8f2f2f;
  --shadow:     0 1px 2px rgba(25,27,32,.06), 0 8px 24px -16px rgba(25,27,32,.30);
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --paper:      #14151a;
    --surface:    #1b1d23;
    --surface-2:  #23262e;
    --ink:        #e9e7e1;
    --graphite:   #9aa0ac;
    --rule:       #333741;
    --accent:     #7fc0a6;
    --accent-soft:#1d2f28;
    --amber:      #d9a35a;
    --amber-soft: #2e2418;
    --crimson:    #d98a8a;
    --shadow:     0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.8);
  }}
}}
:root[data-theme="dark"] {{
  --paper:      #14151a;
  --surface:    #1b1d23;
  --surface-2:  #23262e;
  --ink:        #e9e7e1;
  --graphite:   #9aa0ac;
  --rule:       #333741;
  --accent:     #7fc0a6;
  --accent-soft:#1d2f28;
  --amber:      #d9a35a;
  --amber-soft: #2e2418;
  --crimson:    #d98a8a;
  --shadow:     0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.8);
}}

* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: "Archivo", system-ui, sans-serif;
  font-size: 15px;
  line-height: 1.55;
}}
.wrap {{ max-width: 1240px; margin: 0 auto; padding: 40px 24px 80px; }}

.masthead {{
  display: flex; flex-wrap: wrap; gap: 28px;
  align-items: flex-end; justify-content: space-between;
  padding-bottom: 22px; border-bottom: 2px solid var(--ink);
}}
.masthead h1 {{
  font-size: clamp(28px, 4vw, 40px); font-weight: 700; letter-spacing: -.02em;
  margin: 6px 0 0; text-wrap: balance; max-width: 18ch;
}}
.kicker {{
  font-size: 11px; letter-spacing: .14em; text-transform: uppercase;
  color: var(--accent); font-weight: 600;
}}
.lede {{ color: var(--graphite); max-width: 62ch; margin: 10px 0 0; }}

.stats {{ display: flex; gap: 26px; flex-wrap: wrap; }}
.stat .n {{
  font-family: "JetBrains Mono", monospace; font-size: 24px; font-weight: 500;
  font-variant-numeric: tabular-nums; display: block; line-height: 1.1;
}}
.stat .k {{
  font-size: 11px; letter-spacing: .08em; text-transform: uppercase;
  color: var(--graphite);
}}
.stat.good .n {{ color: var(--accent); }}

.brief {{
  margin: 26px 0 0; padding: 18px 20px; background: var(--surface);
  border: 1px solid var(--rule); border-left: 3px solid var(--accent);
  box-shadow: var(--shadow);
}}
.brief h2 {{ margin: 0 0 8px; font-size: 15px; letter-spacing: -.01em; }}
.brief ul {{ margin: 0; padding-left: 18px; color: var(--graphite); }}
.brief li + li {{ margin-top: 5px; }}
.brief b {{ color: var(--ink); font-weight: 600; }}

.toolbar {{
  position: sticky; top: 0; z-index: 20; margin: 30px 0 0;
  display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
  padding: 12px 0; background: var(--paper);
  border-bottom: 1px solid var(--rule);
}}
.filter {{
  font: inherit; font-size: 13px; font-weight: 500;
  padding: 6px 14px; border-radius: 999px; cursor: pointer;
  border: 1px solid var(--rule); background: var(--surface); color: var(--graphite);
}}
.filter[aria-pressed="true"] {{
  background: var(--accent); border-color: var(--accent);
  color: var(--paper);
}}
.spacer {{ flex: 1 1 auto; }}
.ghost {{
  font: inherit; font-size: 13px; font-weight: 500; cursor: pointer;
  padding: 6px 14px; border-radius: 999px;
  border: 1px solid var(--rule); background: transparent; color: var(--ink);
}}
.ghost:hover {{ background: var(--surface-2); }}

.card {{
  margin-top: 26px; background: var(--surface);
  border: 1px solid var(--rule); box-shadow: var(--shadow);
}}
.card[hidden] {{ display: none; }}
.card-head {{
  display: flex; gap: 16px; align-items: flex-start; justify-content: space-between;
  flex-wrap: wrap; padding: 16px 20px; border-bottom: 1px solid var(--rule);
  background: var(--surface-2);
}}
.eyebrow {{
  display: block; font-size: 11px; letter-spacing: .1em; text-transform: uppercase;
  color: var(--graphite); font-weight: 600;
}}
.card-head h2 {{ margin: 2px 0 0; font-size: 19px; letter-spacing: -.01em; }}
.tags {{ display: flex; gap: 6px; flex-wrap: wrap; }}
.tag {{
  font-size: 11px; font-weight: 600; letter-spacing: .04em;
  padding: 3px 9px; border-radius: 3px;
  background: var(--paper); border: 1px solid var(--rule); color: var(--graphite);
}}
.tag.fig {{ background: var(--amber-soft); border-color: transparent; color: var(--amber); }}
.tag.multi {{ background: var(--accent-soft); border-color: transparent; color: var(--accent); }}

.split {{ display: grid; grid-template-columns: 1fr 1fr; }}
@media (max-width: 900px) {{ .split {{ grid-template-columns: 1fr; }} }}
.pane {{ padding: 18px 20px; min-width: 0; }}
.pane.origin {{ border-right: 1px solid var(--rule); background: var(--paper); }}
@media (max-width: 900px) {{
  .pane.origin {{ border-right: 0; border-bottom: 1px solid var(--rule); }}
}}
.pane-title {{
  font-size: 11px; letter-spacing: .12em; text-transform: uppercase;
  color: var(--graphite); margin: 0 0 12px; font-weight: 600;
  display: flex; gap: 8px; align-items: baseline;
}}
.src {{ font-family: "JetBrains Mono", monospace; letter-spacing: 0;
        text-transform: none; font-size: 11px; font-weight: 400; }}
.shots {{ display: flex; flex-direction: column; gap: 12px; }}
.shots img {{
  width: 100%; height: auto; display: block;
  border: 1px solid var(--rule); background: #fff;
}}

.stim, .prompt {{ font-family: "Source Serif 4", Georgia, serif; font-size: 15.5px; }}
.stim {{
  padding: 12px 14px; background: var(--paper); border: 1px solid var(--rule);
  margin-bottom: 12px; max-height: 300px; overflow-y: auto;
}}
.prompt {{ font-weight: 600; margin-bottom: 14px; }}

.choices {{ list-style: none; margin: 0 0 14px; padding: 0;
            display: flex; flex-direction: column; gap: 6px; }}
.choices li {{
  display: grid; grid-template-columns: auto 1fr auto; gap: 10px;
  align-items: baseline; padding: 8px 12px;
  border: 1px solid var(--rule); background: var(--paper);
  font-family: "Source Serif 4", Georgia, serif; font-size: 15px;
}}
.choices li.ok {{ border-color: var(--accent); background: var(--accent-soft); }}
.mark {{ font-family: "Archivo", sans-serif; font-weight: 700; font-size: 13px;
         color: var(--graphite); }}
.choices li.ok .mark {{ color: var(--accent); }}
.tick, .gfx {{
  font-family: "Archivo", sans-serif; font-size: 10px; font-weight: 700;
  letter-spacing: .07em; text-transform: uppercase; white-space: nowrap;
}}
.tick {{ color: var(--accent); }}
.gfx {{ color: var(--amber); }}

.gridin {{
  display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap;
  padding: 12px 14px; border: 1px solid var(--accent);
  background: var(--accent-soft); margin-bottom: 14px;
}}
.gridin .val {{
  font-family: "JetBrains Mono", monospace; font-size: 20px; font-weight: 500;
  color: var(--accent);
}}
.alts {{ font-size: 12px; color: var(--graphite); }}

.lbl {{
  font-size: 10px; letter-spacing: .1em; text-transform: uppercase;
  color: var(--graphite); font-weight: 700;
}}
.figalt {{ font-size: 13px; color: var(--graphite); margin: 0 0 14px;
           display: flex; flex-direction: column; gap: 3px; }}

.classif {{
  border-top: 1px solid var(--rule); padding-top: 12px;
  display: flex; flex-direction: column; gap: 4px;
}}
.cl-row {{ display: grid; grid-template-columns: 92px 1fr; gap: 10px;
           align-items: baseline; font-size: 13.5px; }}
.conf {{ font-family: "JetBrains Mono", monospace; font-weight: 500;
         font-variant-numeric: tabular-nums; }}
.conf.high {{ color: var(--accent); }}
.conf.mid  {{ color: var(--amber); }}
.conf.low  {{ color: var(--crimson); }}
.why {{ margin: 6px 0 0; font-size: 13px; color: var(--graphite);
        font-style: italic; }}

.rat {{ margin-top: 14px; border-top: 1px solid var(--rule); padding-top: 10px; }}
.rat summary {{
  cursor: pointer; font-size: 12px; font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; color: var(--graphite);
}}
.rat summary:hover {{ color: var(--ink); }}
.rat .md {{ font-family: "Source Serif 4", Georgia, serif; font-size: 14.5px;
            margin-top: 10px; }}
.distr {{ margin-top: 12px; padding-top: 10px; border-top: 1px dashed var(--rule);
          font-size: 13.5px; color: var(--graphite); }}
.distr p {{ margin: 6px 0; }}
.distr b {{ color: var(--ink); }}

.verdict {{
  display: flex; gap: 14px; align-items: center; flex-wrap: wrap;
  padding: 12px 20px; border-top: 1px solid var(--rule); background: var(--surface-2);
}}
.vlabel {{ font-size: 10px; letter-spacing: .1em; text-transform: uppercase;
           color: var(--graphite); font-weight: 700; }}
.verdict label {{ display: flex; gap: 6px; align-items: center; font-size: 13px;
                  cursor: pointer; }}
.verdict .note {{
  flex: 1 1 220px; min-width: 160px; font: inherit; font-size: 13px;
  padding: 5px 10px; border: 1px solid var(--rule); border-radius: 3px;
  background: var(--surface); color: var(--ink);
}}
.card.marked-ok {{ border-left: 3px solid var(--accent); }}
.card.marked-bad {{ border-left: 3px solid var(--crimson); }}

:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.katex {{ font-size: 1.04em; }}
code.raw {{
  font-family: "JetBrains Mono", monospace; font-size: 12px;
  background: var(--surface-2); padding: 1px 5px; border-radius: 3px;
  color: var(--graphite); word-break: break-all;
}}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; }} }}
</style>

<div class="wrap">
  <header class="masthead">
    <div>
      <span class="kicker">Pipeline de ingestao &middot; etapa 1</span>
      <h1>Revisao da extracao</h1>
      <p class="lede">Recorte do PDF oficial a esquerda, o que o pipeline gravaria
        no banco a direita. Confira transcricao, LaTeX, alternativas e a
        classificacao antes de rodar nas 960 questoes.</p>
    </div>
    <div class="stats">
      <div class="stat good"><span class="n">960/960</span>
        <span class="k">questoes segmentadas</span></div>
      <div class="stat good"><span class="n">960</span>
        <span class="k">gabaritos casados</span></div>
      <div class="stat"><span class="n">{len(items)}</span>
        <span class="k">nesta amostra</span></div>
      <div class="stat"><span class="n">{n_rw}/{n_math}</span>
        <span class="k">R&amp;W / Math</span></div>
    </div>
  </header>

  <div class="brief">
    <h2>O que olhar com atencao</h2>
    <ul>
      <li><b>LaTeX</b> &mdash; no PDF as formulas vem desmontadas em pedacos
        soltos; a transcricao veio da imagem, nao do texto. Confira se bate.</li>
      <li><b>Recortes multiplos</b> &mdash; questoes marcadas com "2 recortes"
        continuam na coluna seguinte. Veja se a pergunta e as alternativas
        chegaram inteiras.</li>
      <li><b>Skill</b> &mdash; confianca abaixo de 0.90 aparece em ambar ou
        vermelho; sao as que mais merecem seu olho.</li>
      <li><b>Dificuldade</b> &mdash; sempre <code class="raw">unrated</code>:
        os PDFs oficiais nao trazem esse rotulo e nada foi inventado.</li>
    </ul>
  </div>

  <nav class="toolbar">
    <button class="filter" data-f="all" aria-pressed="true">Todas</button>
    <button class="filter" data-f="reading_writing" aria-pressed="false">Reading &amp; Writing</button>
    <button class="filter" data-f="math" aria-pressed="false">Math</button>
    <span class="spacer"></span>
    <button class="ghost" id="copy">Copiar resumo da revisao</button>
  </nav>

  {"".join(cards)}
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js"></script>
<script>
(function () {{
  // markdown minimo: **negrito**, *italico*, quebras de paragrafo
  function mdInline(s) {{
    return s
      .replace(/\\*\\*([^*]+)\\*\\*/g, "<b>$1</b>")
      .replace(/(^|[^*])\\*([^*\\n]+)\\*/g, "$1<i>$2</i>");
  }}
  document.querySelectorAll(".md").forEach(function (el) {{
    var parts = el.textContent.split(/\\n\\s*\\n/);
    el.innerHTML = parts.map(function (p) {{
      return "<p>" + mdInline(p).replace(/\\n/g, "<br>") + "</p>";
    }}).join("");
  }});

  if (window.renderMathInElement) {{
    renderMathInElement(document.body, {{
      delimiters: [
        {{ left: "$$", right: "$$", display: true }},
        {{ left: "$",  right: "$",  display: false }}
      ],
      throwOnError: false
    }});
  }}

  // filtros
  var cards = Array.prototype.slice.call(document.querySelectorAll(".card"));
  document.querySelectorAll(".filter").forEach(function (b) {{
    b.addEventListener("click", function () {{
      document.querySelectorAll(".filter").forEach(function (o) {{
        o.setAttribute("aria-pressed", String(o === b));
      }});
      var f = b.dataset.f;
      cards.forEach(function (c) {{
        c.hidden = f !== "all" && c.dataset.section !== f;
      }});
    }});
  }});

  // veredito por questao, lembrado no navegador
  var KEY = "sat-review-v1";
  var state = {{}};
  try {{ state = JSON.parse(localStorage.getItem(KEY) || "{{}}"); }} catch (e) {{}}
  function save() {{
    try {{ localStorage.setItem(KEY, JSON.stringify(state)); }} catch (e) {{}}
  }}
  cards.forEach(function (card) {{
    var id = card.id;
    var radios = card.querySelectorAll('input[type="radio"]');
    var note = card.querySelector(".note");
    var st = state[id] || {{}};
    if (st.v) {{
      radios.forEach(function (r) {{ if (r.value === st.v) r.checked = true; }});
      card.classList.add(st.v === "ok" ? "marked-ok" : "marked-bad");
    }}
    if (st.n) note.value = st.n;
    radios.forEach(function (r) {{
      r.addEventListener("change", function () {{
        state[id] = Object.assign({{}}, state[id], {{ v: r.value, q: note.dataset.q }});
        card.classList.remove("marked-ok", "marked-bad");
        card.classList.add(r.value === "ok" ? "marked-ok" : "marked-bad");
        save();
      }});
    }});
    note.addEventListener("input", function () {{
      state[id] = Object.assign({{}}, state[id], {{ n: note.value, q: note.dataset.q }});
      save();
    }});
  }});

  document.getElementById("copy").addEventListener("click", function () {{
    var lines = [];
    cards.forEach(function (card) {{
      var st = state[card.id];
      if (!st || !st.v) return;
      lines.push((st.v === "ok" ? "OK   " : "ERRO ") + (st.q || card.id) +
                 (st.n ? " -- " + st.n : ""));
    }});
    var txt = lines.length ? lines.join("\\n") : "(nenhuma questao marcada ainda)";
    navigator.clipboard.writeText(txt).then(function () {{
      var b = document.getElementById("copy");
      var old = b.textContent;
      b.textContent = "Copiado";
      setTimeout(function () {{ b.textContent = old; }}, 1400);
    }});
  }});
}})();
</script>"""

    path = HERE / "out" / "review.html"
    path.write_text(doc, encoding="utf-8")
    size = path.stat().st_size / 1024 / 1024
    print(f"{path}  ({size:.2f} MB, {len(items)} questoes)")
    return path


if __name__ == "__main__":
    build()
