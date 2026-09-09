"""
Taxonomia oficial do Digital SAT: 4 dominios + 8 skills em Reading and Writing,
4 dominios + 19 skills em Math.

As descricoes sao usadas literalmente no prompt de classificacao e vao para a
coluna skills.official_description no banco, para poderem ser ajustadas sem
mexer no codigo.
"""

RW_DOMAINS = [
    {
        "code": "craft_and_structure",
        "name": "Craft and Structure",
        "skills": [
            {
                "code": "cross_text_connections",
                "name": "Cross-Text Connections",
                "description": (
                    "Duas passagens curtas de autores diferentes sobre o mesmo "
                    "tema; a questao pede como um autor responderia ao outro, ou "
                    "em que os dois concordam ou discordam."
                ),
            },
            {
                "code": "text_structure_and_purpose",
                "name": "Text Structure and Purpose",
                "description": (
                    "Pede a estrutura geral do texto, a funcao de uma parte "
                    "especifica (frase sublinhada) dentro do todo, ou o proposito "
                    "retorico principal do texto."
                ),
            },
            {
                "code": "words_in_context",
                "name": "Words in Context",
                "description": (
                    "Preencher uma lacuna com a palavra ou expressao mais logica "
                    "e precisa, ou determinar o sentido de uma palavra conforme "
                    "usada no texto."
                ),
            },
        ],
    },
    {
        "code": "information_and_ideas",
        "name": "Information and Ideas",
        "skills": [
            {
                "code": "central_ideas_and_details",
                "name": "Central Ideas and Details",
                "description": (
                    "Identificar a ideia central, a tese ou um detalhe explicito "
                    "do texto, sem exigir inferencia alem do que esta escrito."
                ),
            },
            {
                "code": "command_of_evidence",
                "name": "Command of Evidence",
                "description": (
                    "Escolher a evidencia textual que melhor sustenta ou enfraquece "
                    "uma afirmacao, ou interpretar dados de tabela/grafico para "
                    "completar ou sustentar uma alegacao (variantes textual e "
                    "quantitativa)."
                ),
            },
            {
                "code": "inferences",
                "name": "Inferences",
                "description": (
                    "Completar o texto com a conclusao mais logica a partir do que "
                    "foi dito; a resposta nao esta escrita, precisa ser inferida. "
                    "Costuma terminar com uma lacuna no fim do texto."
                ),
            },
        ],
    },
    {
        "code": "expression_of_ideas",
        "name": "Expression of Ideas",
        "skills": [
            {
                "code": "rhetorical_synthesis",
                "name": "Rhetorical Synthesis",
                "description": (
                    "Dada uma lista de notas de pesquisa em bullets, escolher a "
                    "frase que melhor cumpre um objetivo retorico declarado pelo "
                    "estudante."
                ),
            },
            {
                "code": "transitions",
                "name": "Transitions",
                "description": (
                    "Escolher a palavra ou expressao de transicao que melhor "
                    "conecta duas partes do texto (however, therefore, for example, "
                    "etc.)."
                ),
            },
        ],
    },
    {
        "code": "standard_english_conventions",
        "name": "Standard English Conventions",
        "skills": [
            {
                "code": "boundaries",
                "name": "Boundaries",
                "description": (
                    "Pontuacao entre oracoes e frases: ponto, ponto e virgula, "
                    "dois pontos, travessao, virgula em oracoes coordenadas, "
                    "emendas de frase e fragmentos."
                ),
            },
            {
                "code": "form_structure_and_sense",
                "name": "Form, Structure, and Sense",
                "description": (
                    "Gramatica interna da frase: concordancia verbal, tempo e "
                    "aspecto verbal, formas de pronome, modificadores mal "
                    "posicionados, estruturas paralelas e formas de plural/possessivo."
                ),
            },
        ],
    },
]

MATH_DOMAINS = [
    {
        "code": "algebra",
        "name": "Algebra",
        "skills": [
            {
                "code": "linear_equations_one_variable",
                "name": "Linear equations in one variable",
                "description": (
                    "Resolver ou interpretar equacoes lineares com uma incognita, "
                    "incluindo equacoes com nenhuma ou infinitas solucoes."
                ),
            },
            {
                "code": "linear_equations_two_variables",
                "name": "Linear equations in two variables",
                "description": (
                    "Equacoes lineares com duas variaveis, inclinacao, intercepto, "
                    "e a relacao entre a equacao e seu grafico no plano xy."
                ),
            },
            {
                "code": "linear_functions",
                "name": "Linear functions",
                "description": (
                    "Modelar situacoes com funcoes lineares e interpretar o "
                    "significado dos coeficientes e do intercepto no contexto."
                ),
            },
            {
                "code": "systems_two_linear_equations",
                "name": "Systems of two linear equations in two variables",
                "description": (
                    "Resolver sistemas de duas equacoes lineares e interpretar o "
                    "numero de solucoes (unica, nenhuma, infinitas)."
                ),
            },
            {
                "code": "linear_inequalities",
                "name": "Linear inequalities in one or two variables",
                "description": (
                    "Montar, resolver e interpretar desigualdades lineares e "
                    "sistemas de desigualdades, incluindo suas regioes no plano."
                ),
            },
        ],
    },
    {
        "code": "advanced_math",
        "name": "Advanced Math",
        "skills": [
            {
                "code": "equivalent_expressions",
                "name": "Equivalent expressions",
                "description": (
                    "Manipular expressoes algebricas equivalentes: fatoracao, "
                    "expansao, expoentes e radicais, expressoes racionais."
                ),
            },
            {
                "code": "nonlinear_equations_and_systems",
                "name": (
                    "Nonlinear equations in one variable and systems of equations "
                    "in two variables"
                ),
                "description": (
                    "Resolver equacoes quadraticas, radicais, racionais ou "
                    "exponenciais, e sistemas em que ao menos uma equacao nao e "
                    "linear."
                ),
            },
            {
                "code": "nonlinear_functions",
                "name": "Nonlinear functions",
                "description": (
                    "Propriedades e graficos de funcoes quadraticas, exponenciais, "
                    "polinomiais e outras nao lineares; vertice, zeros, "
                    "crescimento e decaimento."
                ),
            },
        ],
    },
    {
        "code": "problem_solving_and_data_analysis",
        "name": "Problem-Solving and Data Analysis",
        "skills": [
            {
                "code": "ratios_rates_proportions_units",
                "name": "Ratios, rates, proportional relationships, and units",
                "description": (
                    "Razoes, taxas, proporcoes e conversao de unidades, incluindo "
                    "densidade e escala."
                ),
            },
            {
                "code": "percentages",
                "name": "Percentages",
                "description": (
                    "Porcentagem, variacao percentual, aumento e desconto."
                ),
            },
            {
                "code": "one_variable_data",
                "name": (
                    "One-variable data: distributions and measures of center and "
                    "spread"
                ),
                "description": (
                    "Media, mediana, moda, amplitude, desvio padrao e leitura de "
                    "distribuicoes, histogramas e boxplots."
                ),
            },
            {
                "code": "two_variable_data",
                "name": "Two-variable data: models and scatterplots",
                "description": (
                    "Diagramas de dispersao, linhas e curvas de ajuste, e uso do "
                    "modelo para prever valores."
                ),
            },
            {
                "code": "probability",
                "name": "Probability and conditional probability",
                "description": (
                    "Probabilidade simples e condicional, frequentemente a partir "
                    "de uma tabela de dupla entrada."
                ),
            },
            {
                "code": "inference_from_samples",
                "name": "Inference from sample statistics and margin of error",
                "description": (
                    "Generalizar de uma amostra para a populacao e interpretar "
                    "intervalos de confianca e margem de erro."
                ),
            },
            {
                "code": "evaluating_statistical_claims",
                "name": (
                    "Evaluating statistical claims: observational studies and "
                    "experiments"
                ),
                "description": (
                    "Avaliar se o desenho do estudo (observacional ou experimental, "
                    "com ou sem aleatorizacao) sustenta a conclusao apresentada."
                ),
            },
        ],
    },
    {
        "code": "geometry_and_trigonometry",
        "name": "Geometry and Trigonometry",
        "skills": [
            {
                "code": "area_and_volume",
                "name": "Area and volume",
                "description": (
                    "Area, perimetro, volume e area de superficie de figuras "
                    "planas e solidos."
                ),
            },
            {
                "code": "lines_angles_triangles",
                "name": "Lines, angles, and triangles",
                "description": (
                    "Angulos formados por retas, semelhanca e congruencia de "
                    "triangulos, e a desigualdade triangular."
                ),
            },
            {
                "code": "right_triangles_and_trigonometry",
                "name": "Right triangles and trigonometry",
                "description": (
                    "Teorema de Pitagoras, triangulos notaveis e as razoes "
                    "trigonometricas seno, cosseno e tangente."
                ),
            },
            {
                "code": "circles",
                "name": "Circles",
                "description": (
                    "Equacao da circunferencia, arcos, angulos centrais e "
                    "inscritos, setores e radianos."
                ),
            },
        ],
    },
]

SECTIONS = {
    "reading_writing": RW_DOMAINS,
    "math": MATH_DOMAINS,
}


def skills_for(section: str):
    """Lista plana [(domain_code, domain_name, skill_code, skill_name, desc)]."""
    out = []
    for d in SECTIONS[section]:
        for s in d["skills"]:
            out.append(
                (d["code"], d["name"], s["code"], s["name"], s["description"])
            )
    return out


def taxonomy_prompt(section: str) -> str:
    """Bloco de texto com a taxonomia, injetado no prompt de classificacao."""
    lines = []
    for d in SECTIONS[section]:
        lines.append(f"\nDOMINIO: {d['name']}  (code: {d['code']})")
        for s in d["skills"]:
            lines.append(f"  - skill code: {s['code']}")
            lines.append(f"    nome: {s['name']}")
            lines.append(f"    quando usar: {s['description']}")
    return "\n".join(lines)


VALID_SKILL_CODES = {
    sec: {t[2] for t in skills_for(sec)} for sec in SECTIONS
}

if __name__ == "__main__":
    for sec in SECTIONS:
        sk = skills_for(sec)
        print(f"{sec}: {len(SECTIONS[sec])} dominios, {len(sk)} skills")
