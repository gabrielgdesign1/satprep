# SAT Practice

Plataforma pessoal para praticar questões oficiais do Digital SAT, extraídas
das provas do College Board (testes 4 a 11).

```
pdfs/         os 16 PDFs oficiais (8 cadernos + 8 gabaritos)
ingestion/    pipeline Python: PDF -> JSON -> Supabase
web/          app Next.js
```

## Estado atual

| item | situação |
|---|---|
| Segmentação das questões | **960/960**, sequência contígua nas 8 provas |
| Gabaritos casados | **960/960** (106 múltipla escolha + 14 grid-in por prova) |
| Extraídas por visão | **33** — parou por falta de crédito na API da Anthropic |
| Carregadas no banco | 6 (conjunto de demonstração) |
| App | completo e testado ponta a ponta |

## Como retomar de onde parou

### 1. Créditos na API da Anthropic

A ingestão parou em `Your credit balance is too low`. Adicione créditos em
console.anthropic.com e rode:

```bash
cd ingestion && python ingest.py
```

É resumível: só processa o que ainda falta. Projeção medida para as 960:
**~7,0M tokens de entrada e ~1,24M de saída**. O padrão é `claude-sonnet-5`
(em `.env`); depois vale refinar os casos duvidosos com Opus:

```bash
cd ingestion && python ingest.py --retry-low
```

### 2. Chave `service_role` do Supabase

Para carregar as 960 no banco. Pegue em
Supabase → Project Settings → API → `service_role`, coloque em `.env` como
`SUPABASE_SERVICE_ROLE_KEY`, e rode:

```bash
cd ingestion && python push_db.py
```

Use `--dry-run` antes para conferir sem escrever nada.

### 3. Rodar o app

```bash
cd web && npm run dev
```

## Decisões que valem lembrar

**Extração por visão, não por regex.** No PDF as fórmulas de Math vêm
desmontadas em fragmentos posicionados — numerador e denominador viram spans
separados, expoentes só se distinguem por delta-Y. Reconstruir LaTeX por regra
erra fração, radical e matriz. O pipeline recorta a questão como imagem, o
modelo lê a fórmula renderizada e devolve LaTeX.

**O print é insumo, não produto.** O que vai para o banco é texto real com
LaTeX. Imagem só existe quando há **gráfico ou diagrama**; tabelas viram tabela
Markdown de verdade, que responde ao tema e ao zoom.

**A resposta correta nunca é decidida pelo modelo.** Vem parseada do PDF oficial
de respostas e entra no prompt como fato. A extração falha alto se o modelo
contradisser o gabarito.

**Dificuldade é sempre `unrated`.** Os PDFs oficiais não trazem esse rótulo e
nada foi inventado. O filtro existe e passa a funcionar se um dia houver dados.

**Critério de "questão resolvida"** — mora só na função `record_attempt()` no
banco, nunca no frontend: a questão é marcada como resolvida se, e somente se,
o usuário **acertou** ou clicou em **mostrar resposta**. Avançar sem responder
não marca nada.

**Reiniciar tópico não apaga histórico.** `reset_skill_progress()` limpa
`user_question_progress`; `user_attempts` fica intacto.

## Fluxo de resposta no app

1. Escolhe a alternativa (ou digita, no grid-in) e confirma.
2. O app diz **só** se acertou ou errou — sem revelar a correta.
3. Se errou: aparece "Mostrar resposta". Só aí a correta e o rationale surgem.
4. "Próxima questão" está sempre disponível, mesmo sem responder.

## Segurança

- `.env` está no `.gitignore`. A chave da Anthropic e a `service_role` nunca
  chegam ao frontend — só o pipeline offline as usa.
- A chave do Desmos é pública por natureza (vai no HTML), daí o prefixo
  `NEXT_PUBLIC_`.
- RLS ativa: conteúdo é somente leitura para autenticados; cada usuário só
  enxerga o próprio progresso.
