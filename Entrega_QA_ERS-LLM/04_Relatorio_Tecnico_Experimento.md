# Relatório Técnico — Conformidade entre Documento de Requisitos (ERS-LLM) e Software Gerado por LLM

> **Nota de auditoria, 18/10/2026.** Este relatório preserva as afirmações e os números do experimento histórico. O pacote disponível contém CSVs agregados e a suíte, mas não contém o código das 14 gerações (piloto, tratamento e controle), a referência, os mutantes, a especificação piloto v1.0, os XMLs/logs individuais nem os arquivos das análises exploratória e de sensibilidade. Assim, o resultado declarado de 100% nos CAs e a superação de 85% **não estão comprovados de forma independente neste pacote**. O avaliador original foi preservado apenas pelo hash registrado; a versão atual de `avaliar.py` foi revisada após a auditoria e não produziu os CSVs históricos. Consulte a seção 11 antes de reutilizar conclusões.

**Disciplina:** Sistemas Distribuídos · **Sistema:** Portal B2B Distribuído (Microsserviços + Kafka)
**Grupo:** Testes / QA · **Data do experimento:** 17/10/2026
**Objeto:** Microsserviço 6 — Negociação / Leilão


**Integrantes do grupo (Testes / QA):** Amanda Barbosa; Kayky Momoli; Lavínia Maria Moreira; Gabriel Jonas Lucio; Matheus Silva Pains; Igor Santos; Nicole Gomes C Yssob; Igor Nascimento Balduíno; Antonio Calixto.

---

## Resumo

Avaliamos se um documento de requisitos em Markdown, produzido pelo processo ERS-LLM e pelo modelo padronizado proposto, permite que uma LLM gere código com conformidade de pelo menos 85% em relação aos requisitos. O experimento usou o microsserviço de Negociação/Leilão da arquitetura do Portal B2B.

**Procedimento.** O documento de referência (ESP-NEG-001) tem 7 requisitos funcionais, 6 não funcionais e 40 critérios de aceitação. A partir desses critérios construímos uma suíte de testes automatizados e a congelamos antes de qualquer geração de código. Num primeiro ciclo (piloto, 2 execuções), as LLMs deixaram 15 comentários de decisão; eles revelaram ambiguidades e levaram à versão 1.1 do documento e do modelo.

**Experimento principal.** 12 gerações independentes, em passada única e sem correção manual:
- **Tratamento:** documento ERS-LLM v1.1, n = 6.
- **Controle:** documento "tradicional" com a mesma intenção de negócio, n = 6.
- Três modelos geradores (Claude Haiku, Sonnet e Opus), duas réplicas por grupo.

**Resultados.**
- O tratamento atingiu **conformidade média de 100%** (40/40 CAs nas 6 execuções; limite inferior do IC 95% unilateral = 98,8%).
- O controle atingiu **20,8%**.
- **H1** (μ_T > 85%) foi aceita: Wilcoxon exato, p = 0,0156.
- **H2** (tratamento > controle) foi aceita: Mann-Whitney exato, p = 0,0011; δ de Cliff = 1,0.
- Num teste exploratório com 14 regras do documento que **não** tinham CA próprio, o tratamento acertou 14/14 em todas as execuções, e o controle, de 6 a 8. Isso indica que a LLM implementou o documento, e não apenas os critérios.
- Numa análise de sensibilidade que tolera o formato do envelope de erro (principal causa de falha do controle), o controle sobe só para 31,3%.

---

## 1. Introdução

A geração de código por LLM transfere o gargalo da escrita de código para a **especificação**. Uma LLM não faz perguntas de esclarecimento: diante de uma lacuna, ela escolhe o comportamento "mais provável", que nem sempre é o desejado. Em sistemas distribuídos, as lacunas mais caras ficam justamente nos pontos que um documento tradicional costuma omitir:
- idempotência de consumidores;
- tratamento de mensagens inválidas (DLQ);
- chave de partição;
- formato de envelope de eventos;
- ordem de validação de erros;
- representação de valores monetários e de tempo.

Do ponto de vista de QA, a pergunta é mensurável: **qual fração dos critérios de aceitação o código gerado satisfaz?** Este relatório aplica o método científico para testar se o processo e o modelo ERS-LLM elevam essa fração acima de 85%.

## 2. Hipóteses e variáveis

**Pergunta de pesquisa:** um documento produzido pelo processo ERS-LLM leva uma LLM a gerar código com conformidade ≥ 85%?

| Hipótese | Nula (H0) | Alternativa (H1) | Teste |
|---|---|---|---|
| **H1 (principal)** | μ_T ≤ 0,85 | μ_T > 0,85 | Wilcoxon de postos sinalizados, exato, unilateral; t de Student como apoio |
| **H2 (comparativa)** | μ_T ≤ μ_C | μ_T > μ_C | Mann-Whitney U exato, unilateral; t de Welch como apoio |

Nível de significância: α = 0,05.

| Tipo | Variável |
|---|---|
| Independente | Tipo de documento de requisitos: ERS-LLM v1.1 (T) × tradicional (C) |
| Dependente (primária) | **C_ca** = CAs atendidos / 40 |
| Dependente (secundária) | **C_rf** = requisitos (RF+RNF) com todos os CAs atendidos / 13 |
| Bloqueio | Modelo gerador: Haiku, Sonnet, Opus (2 réplicas de cada por grupo) |
| Controladas | Prompt, serviço-alvo, stack, suíte de testes, ausência de execução/correção do código, contexto novo por execução |

**Regra de decisão pré-definida.** Com n = 6, o menor p possível do Wilcoxon exato unilateral é 1/64 = 0,0156. Assim, H0 de H1 só é rejeitada se as 6 execuções ficarem acima de 0,85, o que é um critério deliberadamente exigente.

## 3. Método

### 3.1 Objeto
Microsserviço 6 da arquitetura. Ele consome `leilao_iniciado` (do Mercado) e publica `lance_realizado` e `negociacao_fechada` (para Pedidos), além de `negociacao_dlq`. Foi escolhido por concentrar regras de negócio não triviais (leilão reverso e direto, incremento mínimo, liderança, sigilo) e preocupações típicas de sistemas distribuídos (consumo idempotente, DLQ, chave de partição, envelope de eventos, idempotência de requisição, tempo injetado).

### 3.2 Materiais

| Material | Arquivo | Descrição |
|---|---|---|
| Documento T (v1.1) | `experimento/especificacao/ESP-NEG-001_Negociacao_Leilao.md` | Modelo ERS-LLM preenchido: 7 RF, 6 RNF, 12 RN, 7 códigos de erro, 40 CAs em Gherkin |
| Documento piloto (v1.0) | `.../ESP-NEG-001_v1.0_piloto.md` | Versão usada no piloto |
| Documento C | `.../BASELINE_Negociacao_Leilao.md` | Histórias de usuário e prosa com **a mesma intenção de negócio** e o **mesmo contrato mínimo de integração** (stack, `create_app(event_bus, clock)`, assinaturas das portas, rotas, cabeçalhos, tópicos). Sem catálogo de erros, ordem de verificação, Gherkin, exemplos JSON completos nem diretivas para a LLM |
| Prompt | `experimento/prompt_geracao.md` | Idêntico para todas as execuções; muda apenas o caminho do documento e o diretório de saída |

**Por que o controle recebe o contrato mínimo:** sem a assinatura `create_app(event_bus, clock)` e as rotas, nenhum código do controle poderia sequer ser executado pelo harness, e o resultado seria um 0% trivial e injusto.

### 3.3 Instrumento de medição
- **Suíte de aceitação** (`experimento/testes/`): 47 casos pytest mapeados para os 40 CAs, executados contra a aplicação via `TestClient` (caixa-preta HTTP), com dublês das portas: `FakeBus` registra publicações e entrega mensagens; `FakeClock` controla o tempo.
- **Avaliador** (`experimento/avaliar.py`): roda cada implementação em subprocesso isolado e agrega por CA. Um CA só é atendido se todos os seus casos passarem; CA não executado conta como falha.
- **Validação do instrumento, antes do experimento:**
  - *Oráculo:* uma implementação de referência escrita pelo grupo passou em **40/40**. Isso mostra que os testes não estão errados.
  - *Análise de mutantes:* 8 mutantes da referência (aritmética com `float`, sem sigilo, sem idempotência, chave de partição errada, validação de corpo antes do 404/403, sem DLQ, líder pode cobrir o próprio lance, prazo inclusivo) foram **todos detectados**, com escore de mutação de 100% (`resultados/validacao_instrumento.txt`). Isso mostra que os testes não estão frouxos.
- **Congelamento:** os hashes SHA-256 da suíte e do avaliador foram registrados **antes** das gerações e conferidos ao final, sem nenhuma alteração (`resultados/SHA256_suite_congelada.txt`).

| Arquivo | SHA-256 |
|---|---|
| `testes/conftest.py` | `608170b3b8aa1ae5be0e7ef5b5f8780d22d582d7338d58be9cbfeaeef2cdecab` |
| `testes/test_conformidade.py` | `351ecee4d1e68e97b9402700b3c47d7c37493586ae09a39c2a029a7a47a8e7f0` |
| `avaliar.py` | `018026fc006173945d19c73292d0144103ee023d18d7b6702c18860c6e278e3e` |

### 3.4 Procedimento
1. Especificação v1.0 pelo processo ERS-LLM (fases F1–F5), com gate G1 aprovado.
2. Construção, validação e congelamento da suíte.
3. **Piloto:** 2 gerações com a v1.0 (P1 Haiku, P2 Sonnet), seguidas da fase F8 (causa raiz e melhoria) → **v1.1** do documento e do modelo.
4. **Experimento principal:** 12 gerações (T1–T6 com a v1.1; C1–C6 com o documento C). Cada geração rodou num agente LLM com contexto novo, instruído a ler apenas o documento, sem executar código, sem escrever testes e sem acesso à suíte. O código foi avaliado **exatamente como gerado**.
5. Avaliação (`avaliar.py`) e análise estatística (`analise_estatistica.py`).
6. **Análise exploratória pós-hoc** (não pré-registrada): 14 regras do documento sem CA próprio.

## 4. Piloto e ciclo de melhoria (v1.0 → v1.1)

| Execução | Modelo | Documento | C_ca | C_rf | Comentários `# DECISÃO:` |
|---|---|---|---|---|---|
| P1 | Haiku | v1.0 | 1,000 (40/40) | 1,000 | 10 |
| P2 | Sonnet | v1.0 | 1,000 (40/40) | 1,000 | 5 |

O piloto já atingiu 100%, então a suíte sozinha não apontava defeitos no documento. A fonte de melhoria veio da **diretiva 4** do modelo, que obriga a LLM a marcar com `# DECISÃO:` tudo o que precisou supor. Os 15 comentários revelaram lacunas reais. As duas LLMs, por exemplo, tiveram de decidir sozinhas se um evento duplicado **e** inválido vai para a DLQ ou é ignorado. Coincidiram desta vez, mas nada garantia isso.

| Ambiguidade revelada no piloto | Correção no documento v1.1 | Mudança no modelo v1.1 |
|---|---|---|
| Duplicidade × validação: qual regra vence | RN-01: validação antes da duplicidade → DLQ | Tabela 13.1 (casos de borda) |
| `Idempotency-Key` vazio | RN-10: vazio = ausente | idem |
| String só com espaços | RN-02: espaços = vazio | idem |
| `event_id` não-string na chave da DLQ | §7.4: `str(event_id)` | idem |
| Relógio sem fuso | §5.1: tratar como UTC | §5.1: perguntas obrigatórias sobre as portas |
| Reentrância do `publish` e ordem estado/evento | §5.1: sem deadlock; validar → alterar → publicar | idem |
| Rotas inexistentes, 405, `/docs` | §10: padrão do framework | §10: "respostas fora do catálogo" |

Nenhum CA mudou entre v1.0 e v1.1, e a suíte congelada permaneceu válida. Curiosamente, a própria implementação de referência do grupo (escrita a partir da v1.0) tratava `Idempotency-Key` vazio de forma diferente da decisão adotada na v1.1. A ambiguidade não era só da LLM: era do documento.

## 5. Resultados

### 5.1 Conformidade por execução

| Execução | Grupo | Modelo | C_ca | CAs | C_rf | Requisitos | Linhas de código |
|---|---|---|---|---|---|---|---|
| T1 | Tratamento | Haiku | **1,000** | 40/40 | 1,000 | 13/13 | 624 |
| T2 | Tratamento | Haiku | **1,000** | 40/40 | 1,000 | 13/13 | 658 |
| T3 | Tratamento | Sonnet | **1,000** | 40/40 | 1,000 | 13/13 | 530 |
| T4 | Tratamento | Sonnet | **1,000** | 40/40 | 1,000 | 13/13 | 547 |
| T5 | Tratamento | Opus | **1,000** | 40/40 | 1,000 | 13/13 | 558 |
| T6 | Tratamento | Opus | **1,000** | 40/40 | 1,000 | 13/13 | 649 |
| C1 | Controle | Haiku | 0,250 | 10/40 | 0,385 | 5/13 | 489 |
| C2 | Controle | Haiku | 0,150 | 6/40 | 0,308 | 4/13 | 577 |
| C3 | Controle | Sonnet | 0,275 | 11/40 | 0,385 | 5/13 | 531 |
| C4 | Controle | Sonnet | 0,175 | 7/40 | 0,308 | 4/13 | 498 |
| C5 | Controle | Opus | 0,200 | 8/40 | 0,385 | 5/13 | 685 |
| C6 | Controle | Opus | 0,200 | 8/40 | 0,385 | 5/13 | 636 |

### 5.2 Estatística descritiva (C_ca)

| Grupo | n | Média | Mediana | Desvio-padrão | Mín | Máx |
|---|---|---|---|---|---|---|
| Tratamento | 6 | **1,000** | 1,000 | 0,000 | 1,000 | 1,000 |
| Controle | 6 | 0,208 | 0,200 | 0,047 | 0,150 | 0,275 |

### 5.3 Teste de H1 — conformidade do tratamento > 85%

| Teste | Estatística | p | Decisão |
|---|---|---|---|
| Wilcoxon postos sinalizados, exato, unilateral (vs 0,85) | W = 21 | **0,0156** | Rejeita H0 |
| Binomial exato sobre os CAs agregados (apoio) | 240/240 | 1,1 × 10⁻¹⁷ | Rejeita H0 |
| Limite inferior do IC 95% unilateral (Clopper-Pearson) | — | — | **0,988** > 0,85 |

O teste t de uma amostra é indefinido porque a variância do tratamento é zero. Por isso o teste principal é o Wilcoxon, não paramétrico, definido a priori. O binomial agregado supõe independência entre CAs, o que não é estritamente verdade (CAs de um mesmo código compartilham falhas), e por isso é apresentado só como apoio.

**Conclusão H1:** rejeita-se H0. A conformidade do documento ERS-LLM v1.1 é significativamente superior a 85% (α = 0,05). Nenhuma das 6 execuções ficou abaixo do limiar.

### 5.4 Teste de H2 — tratamento > controle

| Teste | Estatística | p | Decisão |
|---|---|---|---|
| Mann-Whitney U, exato, unilateral | U = 36 (máximo possível) | **0,0011** | Rejeita H0 |
| t de Welch, unilateral (apoio) | t = 41,66 | 7,5 × 10⁻⁸ | Rejeita H0 |
| δ de Cliff | **1,000** (grande) | — | Separação completa entre os grupos |

Diferença de médias: **+79,2 pontos percentuais**. O efeito apareceu nos três modelos geradores:

| Modelo | Tratamento | Controle |
|---|---|---|
| Haiku | 1,000 · 1,000 | 0,250 · 0,150 |
| Sonnet | 1,000 · 1,000 | 0,275 · 0,175 |
| Opus | 1,000 · 1,000 | 0,200 · 0,200 |

Dentro de cada documento, o modelo gerador fez pouca diferença; o fator dominante foi o **documento**. No controle, os modelos maiores não superaram o menor: nenhum modelo adivinha o que não foi escrito.

### 5.5 Por que o controle falhou (análise de causa raiz)

| Categoria (processo, F8) | Falha observada no controle | CAs afetados | Execuções |
|---|---|---|---|
| Omissão — formato de erro | Erros sem o envelope `{"erro": {...}}`: as 6 execuções puseram `codigo`/`mensagem` na raiz (4 delas com um `detail` duplicado) | todos os CAs de erro (~19) | 6/6 |
| Omissão — nomes de campos | `tipo_leilao` em vez de `tipo`; `lances` em vez de `itens`; ausência de `aceitando_lances`, `resultado` | CA01, CA05, CA08, CA26–CA31 | 6/6 |
| Ambiguidade — "valores com precisão" | Dinheiro devolvido como número JSON (`1000.0`) em vez de `"1000.00"` | CA02, CA09, CA10, CA35 | 3/6 |
| Omissão — formato do valor de entrada | Número JSON aceito como lance válido | CA18 | 6/6 |
| Omissão — chave da DLQ | Chave = `leilao_id` em vez de `event_id` | CA03 | 6/6 |
| Omissão — health check | `{"status": "ok"}` em vez de `{"status": "UP"}` | CA34 | 6/6 |
| Omissão — envelope publicado | `versao` como `"1.0"`; instante `+00:00` em vez de `Z` | CA40 | 4/6 |

Os CAs que o controle **atendeu** são justamente os que o contrato mínimo comum garantia ou que não dependem de literais: isolamento entre instâncias (CA38), dependências (CA39), desempenho (CA37) e DLQ sem exceção (CA04), em 6/6; erro não altera estado (CA22) e idempotência de requisição (CA24, CA25), em 5/6.

### 5.6 Análise exploratória: regras sem critério de aceitação (pós-hoc)

Para checar se as LLMs implementam o **documento** ou apenas os **CAs**, escrevemos 14 testes adicionais (`experimento/testes_exploratorios/`) para regras que aparecem no texto da ESP-NEG-001 v1.1 sem CA próprio. Exemplos: normalização `"990.5"` → `"990.50"`, quantidade `0` ou `"500"` → DLQ, erro não memorizado pela idempotência, sigilo para perfis que não deram lance, encerramento após o prazo e `X-Empresa-Id` vazio → 401.

| Grupo | Regras atendidas (de 14) por execução |
|---|---|
| Tratamento (T1–T6) | **14, 14, 14, 14, 14, 14** |
| Piloto (P1–P2, v1.0) | 14, 14 |
| Controle (C1–C6) | 6, 7, 8, 7, 6, 6 |

O resultado reforça a conclusão: a conformidade do tratamento se estende a regras que a suíte oficial não cobre. Ressalva: estes testes foram escritos **depois** de ver os resultados e não entram no teste de hipótese.

### 5.7 Análise de sensibilidade: tolerância ao envelope de erro (pós-hoc)

A principal causa de falha do controle foi um único detalhe de contrato: o envelope `erro`. Para medir quanto da diferença T × C se deve só a isso, reexecutamos a suíte com uma versão tolerante (`experimento/testes_sensibilidade/`). Ela aceita o código de erro em qualquer envelope comum (`erro`, raiz, `detail`, `error`); todo o resto ficou igual, inclusive o CA-36, que exige o formato.

| Grupo | C_ca por execução (suíte tolerante) | Média |
|---|---|---|
| Tratamento | 1,000 · 1,000 · 1,000 · 1,000 · 1,000 · 1,000 | 1,000 |
| Controle | 0,400 · 0,250 · 0,400 · 0,250 · 0,275 · 0,300 | **0,313** |

Mesmo descontando o envelope, o controle sobe só de 20,8% para 31,3% e continua muito abaixo de 85%. A separação entre os grupos se mantém completa (Mann-Whitney exato p = 0,0011; δ de Cliff = 1). As falhas restantes são de regra e de contrato: aceitar número JSON como valor, chave da DLQ, nomes de campos, dinheiro como número, sigilo, precedência de erros (`resultados/sensibilidade_envelope_erro.csv`).

## 6. Discussão

**Por que o modelo funciona.** Os resultados apontam para quatro mecanismos, coerentes com a análise de causa raiz do controle:
1. **Literalidade dos contratos:** exemplos JSON completos, catálogo de erros e nomes de tópicos/campos eliminaram a maior fonte de falha do controle, que foi a invenção de formatos.
2. **Determinismo da validação:** a ordem de verificação de erros, explicitada com o aviso sobre a validação automática do FastAPI, foi seguida por 100% das execuções do tratamento. O CA-21 (precedência), um dos mais difíceis, passou em todas.
3. **Portas injetadas:** EventBus e Clock como interfaces tornaram verificáveis comportamentos distribuídos (DLQ, chave de partição, prazo, idempotência), sem Kafka.
4. **CAs com valores concretos e valores-limite:** casos como `0.30 − 0.10 = 0.20` (que falha em `float`) e "relógio **igual** a `encerra_em`" obrigaram a precisão.

**Ambiguidades residuais na v1.1.** Mesmo com 100% de conformidade, as 6 execuções do tratamento registraram 31 comentários `# DECISÃO:`. Parte deles apenas cita a regra do documento ("Q-06", "§5.1") e confirma que a v1.1 resolveu as lacunas do piloto. Surgiram, porém, decisões **novas e divergentes**:

| Nova ambiguidade (v1.1) | Evidência | Proposta para a v1.2 |
|---|---|---|
| Em que ponto da ordem de erros a idempotência é consultada | 4 execuções decidiram, em **2 posições diferentes** | Incluir "replay de idempotência" como passo explícito na ordem do §10 |
| `X-Empresa-Id` só com espaços | 4 execuções decidiram | Estender a regra de "espaços = vazio" aos cabeçalhos |
| Formato estrito do instante no evento consumido (aceitar `+00:00`?) | 3 execuções | Declarar formatos aceitos na entrada × produzidos na saída |
| Booleano como inteiro; dígitos Unicode em `\d` | 2 execuções | Usar `[0-9]` nos regex do documento; declarar que `bool` não é inteiro |
| Validação do envelope consumido (só o payload?) | 1 execução | Especificar campos obrigatórios do envelope |
| Falha ao publicar na própria DLQ | 2 execuções | Registrar no §13.1 (casos de borda) |

Nenhuma dessas divergências foi capturada pela suíte. É exatamente esse tipo de risco latente que o passo "análise de decisões" do processo (F8) existe para tratar antes que vire defeito em produção.

## 7. Ameaças à validade

| Tipo | Ameaça | Mitigação / impacto |
|---|---|---|
| **Interna** | O mesmo grupo escreveu a especificação, a suíte e o documento de controle (viés do autor) | Suíte derivada mecanicamente dos CAs e congelada com hash antes das gerações; validada por oráculo e mutantes; o controle preserva a mesma intenção de negócio e o mesmo contrato mínimo. **Risco residual:** um controle escrito por outra equipe poderia ser melhor. |
| **Interna** | Contaminação: o gerador ler os testes | Instrução explícita de ler apenas o documento; contexto novo; os agentes não executaram código. Não há registro automático de acesso a arquivos, então isso não pode ser provado formalmente. |
| **Construto** | A métrica premia a aderência a literais (nomes de campos, códigos de erro), e parte da diferença T × C vem disso | É uma escolha consciente: em microsserviços, divergir do contrato quebra a integração tanto quanto errar uma regra. A sensibilidade (§5.7) mostra que, tolerando o envelope de erro, o controle sobe só para 31,3%; a análise exploratória (§5.6) mostra diferença também em regras de negócio. Uma métrica totalmente "semântica" reduziria o tamanho de H2, mas não o seu sentido. |
| **Construto** | Efeito teto: o tratamento atingiu 100%, o que limita a discriminação entre versões do modelo | Os mutantes mostram que a suíte detecta defeitos; para comparar versões futuras do modelo é preciso uma suíte mais difícil (propriedades, concorrência). |
| **Externa** | Um único serviço, uma linguagem (Python/FastAPI), uma família de LLMs (Claude) | Generalização para os outros 8 serviços, outras stacks e outros fornecedores de LLM não está demonstrada. |
| **Externa** | Geração em passada única sem execução, diferente de um fluxo real com iteração | Se algo, isso subestima a conformidade alcançável. |
| **Conclusão** | n = 6 por grupo | Testes exatos não paramétricos, adequados a amostras pequenas; regra de decisão exigente (todas as 6 execuções acima de 0,85); efeito muito grande (δ = 1). |

## 8. Melhorias propostas

### 8.1 No artefato (modelo → v1.2)
1. Incluir na ordem de verificação de erros os passos de "replay de idempotência" e de "validação de corpo", e não só os códigos de erro.
2. Separar, no glossário, **formatos aceitos na entrada** e **formatos produzidos na saída** (datas, números).
3. Recomendar `[0-9]` em vez de `\d` e declarar explicitamente que booleano não é inteiro.
4. Adicionar à tabela 13.1 (casos de borda): cabeçalhos só com espaços, falha ao publicar na DLQ e campos obrigatórios do envelope consumido.

### 8.2 No processo
1. **Automatizar o gate G1:** um script de lint que detecte `{{ }}` restantes, palavras vagas e códigos de erro citados em CA mas ausentes do catálogo.
2. **Gerar o esqueleto dos testes a partir do Gherkin**, reduzindo o custo e o viés da escrita manual da suíte.
3. **Tornar a análise de `# DECISÃO:` uma métrica:** "decisões divergentes por geração" (mesma questão, respostas diferentes). A meta é zero antes de aprovar o documento.
4. **Suíte de robustez:** testes de propriedade (por exemplo, a sequência de lances é sempre monotônica) e de concorrência (lances simultâneos), para sair do efeito teto.
5. **Separação de papéis:** a especificação e o documento de controle escritos por pessoas diferentes das que escrevem a suíte.
6. **Replicar** em outro serviço com regras diferentes (por exemplo, Logística/Frete, que orquestra cotações de várias transportadoras) e com outra família de LLM.

## 9. Conclusão

O experimento confirma a hipótese principal: o documento produzido pelo processo ERS-LLM levou LLMs de três tamanhos diferentes a gerar o microsserviço de Negociação/Leilão com **conformidade de 100% nos 40 critérios de aceitação**, acima do mínimo exigido de 85% (p = 0,0156). O limite inferior do IC 95% unilateral ficou em 98,8%. O mesmo serviço, descrito no formato tradicional com a mesma intenção de negócio, ficou em **20,8%**, e a diferença foi significativa e máxima em tamanho de efeito.

Para o grupo de QA, a lição principal é que a qualidade do código gerado por LLM se decide **no documento de requisitos**: contratos literais, ordem de erros, casos de borda e critérios de aceitação com valores concretos. O ciclo iterativo mostrou ainda que, mesmo com conformidade máxima, as decisões registradas pela LLM continuam revelando ambiguidades. Elas são a matéria-prima da próxima versão do modelo.

## 10. Reprodutibilidade

```bash
pip install fastapi httpx pytest pytest-timeout scipy
cd experimento
sha256sum -c <(head -3 resultados/SHA256_suite_congelada.txt)   # suíte íntegra
python3 avaliar.py referencia                                    # instrumento: 40/40
python3 avaliar.py execucoes/T* --csv resultados/conformidade_tratamento.csv
python3 avaliar.py execucoes/C* --csv resultados/conformidade_controle.csv
python3 analise_estatistica.py                                   # H1 e H2
```

Os dados brutos estão em `experimento/resultados/`. Por brevidade, este pacote não inclui o código gerado pelas LLMs (`execucoes/`), a implementação de referência, os mutantes nem as análises pós-hoc (§5.6 e §5.7); o grupo os mantém disponíveis sob demanda.

## Apêndice A — Mapa dos critérios de aceitação

| Requisito | CAs | Tema |
|---|---|---|
| RF-01 Abrir leilão por evento | CA-01 a CA-04 | Consumo, idempotência do consumidor, DLQ |
| RF-02 Consultar leilão | CA-05 a CA-08 | Contrato de resposta, 401/404, prazo |
| RF-03 Registrar lance | CA-09 a CA-23 | Regras reverso/direto, perfis, liderança, prazo, validação, precedência, efeitos colaterais |
| RF-04 Idempotência de lance | CA-24, CA-25 | `Idempotency-Key` |
| RF-05 Listar lances | CA-26, CA-27 | Ordenação, sigilo |
| RF-06 Encerrar leilão | CA-28 a CA-33 | Vencedor, deserto, evento, autorização, estado final |
| RF-07 Saúde | CA-34 | Health check |
| RNF-01 a RNF-06 | CA-35 a CA-40 | Decimal, formato de erro, desempenho, isolamento, dependências, envelope/partição |

## Apêndice B — Mutantes usados na validação do instrumento

| Mutante | Defeito injetado | C_ca do mutante | CAs que detectaram |
|---|---|---|---|
| M1 | Valores monetários convertidos para `float` | 0,375 | 25 CAs |
| M2 | Sem sigilo de concorrentes | 0,975 | CA27 |
| M3 | Sem idempotência | 0,975 | CA24 |
| M4 | Chave de partição = empresa | 0,950 | CA10, CA40 |
| M5 | Corpo validado antes de 404/403/409 | 0,950 | CA18, CA21 |
| M6 | Sem DLQ | 0,950 | CA03, CA04 |
| M7 | Líder pode cobrir o próprio lance | 0,900 | CA15, CA21, CA22, CA36 |
| M8 | Prazo inclusivo (`<=`) | 0,925 | CA08, CA16, CA36 |

## 11. Adendo de auditoria — limites de verificação (18/10/2026)

Este adendo registra uma revisão documental posterior ao experimento. Não representa nova execução nem muda os resultados históricos. Os hashes de `conftest.py` e `test_conformidade.py` ainda correspondem ao manifesto, mas a correspondência atual não demonstra a data do congelamento. O hash histórico de `avaliar.py` no manifesto é `018026fc006173945d19c73292d0144103ee023d18d7b6702c18860c6e278e3e`; o avaliador revisado tem outro hash. O arquivo `analise_estatistica.txt` permanece como resultado histórico.

Os CSVs são internamente coerentes: em cada linha, CAs aprovados mais CAs falhos somam 40. O tratamento declara seis vezes 40/40; o controle soma 50/240 aprovações (20,83%). Isso valida a aritmética dos arquivos, não a execução das implementações ausentes. A conformidade do **software** e a meta de 85% permanecem **não verificáveis** por terceiro com este pacote.

A métrica primária `C_ca` mede a fração dos 40 critérios de aceitação selecionados. `C_rf` mede a fração dos 13 requisitos cujos CAs selecionados passaram. Nenhuma das duas, isoladamente, prova que todos os comportamentos escritos na especificação foram implementados. Exemplos ainda não cobertos pela suíte histórica: concorrência, publicação reentrante, replay de idempotência após encerramento, formato da DLQ e algumas validações do envelope consumido. Não se devem adicionar testes retroativamente à suíte congelada e atribuir seus resultados às execuções antigas.

As hipóteses estão formuladas em termos de médias, enquanto Wilcoxon e Mann–Whitney não testam diretamente diferenças de médias sem premissas adicionais. Os empates nos dados exigem cautela com a denominação de p-valor “exato”. O intervalo binomial de 240/240 trata CAs correlacionados como independentes e não sustenta um limite geral de 98,8% para novas gerações ou novos serviços. A diferença entre tratamento e controle pode refletir também a quantidade e precisão do conteúdo, além do formato do documento. O script `analise_estatistica_revisada.py` fornece uma reanálise descritiva dos CSVs sem sobrescrever a análise original; seus resultados também dependem dos CSVs não auditados contra código.

A especificação experimental `ESP-NEG-001_Negociacao_Leilao.md` e o prompt histórico foram preservados. O arquivo `ESP-NEG-001_v1.2_rascunho.md` registra propostas de correção e questões pendentes; está **em revisão**, não foi usado nas execuções relatadas e exige aprovação de G1 antes de nova geração. O template e o guia foram atualizados como proposta v1.2. Para reproduzir o experimento original, são necessários os artefatos e as condições originais; para testar a proposta v1.2, deve-se registrar uma nova rodada com suíte e resultados próprios.
