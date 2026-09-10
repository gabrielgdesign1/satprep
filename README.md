# SAT Practice

Plataforma pessoal para praticar questões oficiais do Digital SAT, extraídas
das provas do College Board (testes 4 a 11).

```
pdfs/         os 16 PDFs oficiais (8 cadernos + 8 gabaritos)
ingestion/    pipeline Python: PDF -> JSON -> Supabase
web/          app Next.js
```

## Estado atual

No ar em **https://web-amber-kappa-30.vercel.app**

| item | situação |
|---|---|
| Segmentação das questões | **960/960**, sequência contígua nas 8 provas |
| Gabaritos casados | **960/960** |
| Reading & Writing no banco | **522 de 528** — extraídas offline, sem API |
| Math no banco | **33 de 432** — parou por falta de crédito na API |
| **Total jogável** | **555 questões** |
| App | completo, testado em produção |

R&W está praticamente completo porque não precisa de IA: o texto do PDF é limpo
e o enunciado do SAT é formulaico. Só Math depende da API, por causa das
fórmulas. As 6 questões de R&W que sobraram estão em
`ingestion/out/rw_needs_vision.jsonl`.

## Os dois pipelines

**Reading & Writing — offline, custo zero.** Não chama API nenhuma:

```bash
cd ingestion && python ingest_rw.py
```

**Math — precisa da API da Anthropic.** É o único que consome crédito:

```bash
cd ingestion && python ingest.py --tests 4 5 6 7 8 9 10 11
```

É resumível: só processa o que ainda falta. Restam 399 questões de Math.
O padrão é `claude-sonnet-5` (em `.env`). Depois vale refinar os duvidosos:

```bash
cd ingestion && python ingest.py --retry-low
```

## Carregar no banco

Com a `service_role` (Supabase → Project Settings → API) em `.env` como
`SUPABASE_SERVICE_ROLE_KEY`:

```bash
cd ingestion && python push_db.py
```

Use `--dry-run` antes para conferir sem escrever nada.

> A carga das 555 atuais foi feita por `load_via_rpc.py`, que usava uma função
> `security definer` temporária no banco porque a `service_role` não estava
> disponível. **Essa função já foi removida.** Prefira `push_db.py`.

## Rodar o app

```bash
cd web && npm run dev
```

## Publicar

```bash
cd web && npx vercel deploy --temporary --yes --prod
```

O ideal é conectar o repo ao projeto na Vercel (Settings → Git, com
**Root Directory = `web`**); aí todo push publica sozinho.

## Decisões que valem lembrar

**Visão só onde ela é necessária.** Reading & Writing sai por extração de
texto e classificação por regra, sem API: o texto do PDF é limpo e o enunciado
do SAT é formulaico (quatro perguntas cobrem 59% das questões). A validação é
estatística — a distribuição por domínio ficou em 29/25/24/22%, contra os
~26/28/26/20% do blueprint oficial do College Board.

**Math é que precisa de visão.** No PDF as fórmulas vêm
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
