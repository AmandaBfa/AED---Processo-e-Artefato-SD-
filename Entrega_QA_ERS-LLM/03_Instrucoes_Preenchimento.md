# Instruções para Preenchimento do Documento de Requisitos (Modelo ERS-LLM v1.2, proposta)

Este guia explica, seção por seção, como preencher o modelo `02_Template_Documento_Requisitos.md`. A especificação `experimento/especificacao/ESP-NEG-001_Negociacao_Leilao.md` é o exemplo histórico v1.1 do experimento. O arquivo `ESP-NEG-001_v1.2_rascunho.md` documenta ajustes propostos e ainda não está aprovado para geração.


**Integrantes do grupo (Testes / QA):** Amanda Barbosa; Kayky Momoli; Lavínia Maria Moreira; Gabriel Jonas Lucio; Matheus Silva Pains; Igor Santos; Nicole Gomes C Yssob; Igor Nascimento Balduíno; Antonio Calixto.

---

## Antes de começar

1. **Um documento por microsserviço** (*bounded context*). Não misture dois serviços no mesmo documento.
2. **Pense como quem vai testar.** Para cada frase escrita, pergunte: *"Que teste prova que isso foi implementado?"* Se não houver resposta, a frase está vaga.
3. **Pense como a LLM.** Ela lê tudo literalmente, não pergunta nada e preenche lacunas com o que é "mais comum". O que você não escrever será decidido por ela.
4. **Ordem recomendada de preenchimento:** 2 → 3 → 4 → 5 → 6 → 7 → 9 → 10 → 8 → 11 → 12 → 13 → 1 → 0 → 14. Os RFs (§8) vêm depois das regras e erros porque os CAs dependem deles.

### Regras gerais de redação

| Faça | Não faça |
|---|---|
| "responde `409` com `erro.codigo` = `LEILAO_ENCERRADO`" | "retorna um erro apropriado" |
| "300 lances em menos de 3 s" | "deve ser rápido" |
| "valor string `^\d+(\.\d{1,2})?$`, > 0" | "valor numérico válido" |
| "`agora < encerra_em`" | "antes do fim do leilão" (inclui ou não o instante final?) |
| Valores concretos: `"1000.00"`, `"FORN-A"` | "um valor qualquer", "uma empresa" |
| Uma regra por linha, com ID | Parágrafos com várias regras misturadas |
| Escrever o que **não** fazer (§3.2) | Deixar a LLM decidir o escopo |

**Palavras proibidas** (se aparecerem, quantifique ou remova): *adequado, apropriado, rápido, eficiente, amigável, robusto, etc., e/ou, entre outros, normalmente, geralmente, se possível, quando necessário, tratar erros, flexível, intuitivo*.

---

## Seção 0 — Metadados
- **Identificador:** `ESP-<SIGLA DO SERVIÇO>-<NNN>` (ex.: `ESP-NEG-001`).
- **Status:** o documento só vai para a LLM com o status *Aprovado para geração*, atribuído pelo QA após o gate G1.
- **Versão:** incremente a cada mudança e registre na §15. A versão do documento usada em cada geração deve ser rastreável.

## Seção 1 — Diretivas para a LLM
Mantenha as seis diretivas do modelo. Elas são o "contrato de leitura" com a LLM:
- A **ordem de precedência** resolve conflitos que escaparam da revisão.
- A diretiva de **literalidade** evita que `LEILAO_ENCERRADO` vire `LeilaoEncerrado` ou `AUCTION_CLOSED`.
- A diretiva `# DECISÃO:` torna as suposições da LLM visíveis no código, o que facilita a análise de causa raiz.
- Ajuste apenas o item 6 (formato da resposta) ao seu caso.

## Seção 2 — Contexto
- **2.1 Objetivo:** no máximo duas frases, em linguagem de negócio.
- **2.2 Posição na arquitetura:** cite os serviços vizinhos **pelo nome usado no diagrama** e os tópicos exatos. Inclua o diagrama textual produtor → tópico → consumidor e o passo do fluxo de negócio.

## Seção 3 — Escopo
- **Dentro:** liste capacidades, não telas.
- **Fora:** liste tudo que um desenvolvedor (ou uma LLM) poderia razoavelmente achar que faz parte, mas não faz. Exemplos: autenticação (feita no gateway), cliente Kafka real, banco de dados, agendadores, cancelamento. Esta lista é a principal defesa contra funcionalidades inventadas.

## Seção 4 — Glossário
Defina todo termo que aparece em regra ou CA e que poderia ser lido de duas formas. Inclua formato e unidade. Termos que **sempre** precisam estar aqui em sistemas distribuídos:
- **Agora / instante atual:** de onde vem o tempo (porta Clock) e o formato de data/hora.
- **Valor monetário:** tipo no JSON (string ou número) e número de casas decimais.
- Qualquer **condição composta** usada várias vezes (ex.: "leilão aceitando lances" = `status == ABERTO e agora < encerra_em`).

## Seção 5 — Restrições técnicas
- **Dependências permitidas:** lista **fechada**. "Qualquer outra é proibida."
- **Ponto de entrada:** assinatura exata da função/fábrica que os testes vão chamar. Sem isso, o código gerado pode até estar correto, mas o harness não consegue executá-lo.
- **Estrutura de arquivos:** caminhos obrigatórios.
- **Estado:** declare se é por instância (recomendado; permite testes isolados).

### 5.1 Portas
Toda dependência externa vira uma interface com assinatura exata em código. Para cada porta, diga:
- quem fornece a implementação (sempre quem chama o ponto de entrada);
- quando o serviço deve usá-la (ex.: "chamar `subscribe` durante a criação da aplicação");
- o que o serviço **não pode** fazer (ex.: "nunca usar o relógio do sistema"; "o handler nunca propaga exceção").

> Por que isso importa para o QA: com portas, o teste injeta um EventBus falso que registra publicações e um relógio controlável. Assim dá para testar prazo, idempotência, DLQ e chave de partição em milissegundos, sem Kafka real.

## Seção 6 — Modelo de domínio
- Uma tabela por entidade. Para cada atributo: tipo, obrigatoriedade e **restrição verificável** (faixa, regex, enumeração literal) **e origem** (quem gera o valor: o evento, o cabeçalho, o serviço, o relógio).
- **Estados:** use a tabela de transições. Inclua estados finais e diga explicitamente o que **não** muda o estado (ex.: "prazo vencido não altera o status").
- Os nomes de atributos devem ser idênticos aos usados nos JSONs da §7.

## Seção 7 — Contratos de interface

### 7.1 Autenticação
Quais cabeçalhos chegam, os valores aceitos e o que acontece quando faltam ou são inválidos. Diga quais rotas são públicas.

### 7.2 API REST
- **Tabela resumo:** uma linha por endpoint, com a coluna **"Erros possíveis (na ordem de verificação)"**. Essa ordem é o item que mais diferencia implementações geradas: sem ela, cada LLM valida numa ordem diferente.
- **Um exemplo JSON completo por resposta de sucesso**, com todos os campos e valores realistas. Se um campo pode ser `null`, diga quando.
- Se o framework tiver validação automática que responde antes da sua lógica (ex.: FastAPI/Pydantic → 422 genérico), diga explicitamente se ela pode ou não ser usada.

### 7.3 Eventos consumidos
Para cada tópico: produtor, chave, qual RF trata e **o que fazer com mensagem inválida**. Inclua um exemplo completo de mensagem (envelope + payload).

### 7.4 Eventos publicados
- Defina o **envelope** uma única vez (id do evento, tipo, versão, instante).
- Para cada tópico: gatilho, **chave de partição** e campos do payload, com um exemplo.
- Regra prática: a chave de partição é o identificador da entidade cujos eventos precisam manter a ordem (no exemplo, `leilao_id`).

## Seção 8 — Requisitos funcionais

### Enunciado no padrão EARS
| Padrão | Forma | Exemplo |
|---|---|---|
| Evento | **Quando** <gatilho>, o serviço deve <resposta>. | Quando uma mensagem válida de `leilao_iniciado` for recebida… |
| Estado | **Enquanto** <estado>, o serviço deve <resposta>. | Enquanto o leilão estiver aceitando lances… |
| Indesejado | **Se** <condição indesejada>, **então** o serviço deve <resposta>. | Se o corpo for inválido, então o serviço deve responder 422… |
| Opcional | **Onde** <característica>, o serviço deve <resposta>. | Onde houver `Idempotency-Key`… |
| Ubíquo | O serviço deve <resposta>. | O serviço deve usar `Decimal` em toda aritmética monetária. |

### Critérios de aceitação em Gherkin
- Numere globalmente: `# CA-01`, `# CA-02`… (o número vira o nome do teste).
- **Dado:** estado inicial com valores concretos. **Quando:** uma ação. **Então:** resultado observável (status HTTP, `erro.codigo`, campo da resposta, evento publicado com tópico e chave, estado consultável).
- Regra geral: 1 cenário de sucesso + 1 de erro por RF. Se não houver erro aplicável, justifique a exceção na matriz de rastreabilidade. Não marque o checklist como cumprido sem essa justificativa.

| Técnica | Pergunta que gera o CA |
|---|---|
| Partição de equivalência | Quais classes de entrada inválida existem? Liste todas no mesmo CA. |
| Valor-limite | O que acontece exatamente na borda (`=`, `+0.01`)? |
| Tabela de decisão | Quais combinações de perfil × tipo × estado existem? |
| Transição de estado | E se a ação for repetida depois do estado final? |
| Combinação de erros | Se dois erros acontecem juntos, qual vence? |
| Distribuído | E se a mensagem chegar duas vezes? E se for inválida? E se o cliente reenviar? Qual a chave? |

**Exemplo ruim:**
```gherkin
Cenário: Lance inválido
  Quando o usuário envia um lance inválido
  Então o sistema retorna erro
```
**Exemplo bom:**
```gherkin
# CA-12
Cenário: Decremento mínimo em leilão reverso
  Dado o leilão REVERSO com incremento_minimo "10.00" e melhor lance "1000.00" de FORN-A
  Quando FORN-B envia valor "995.00"
  Então a resposta é 422 com erro.codigo "LANCE_INSUFICIENTE"
  Quando FORN-B envia valor "990.00"
  Então a resposta é 201
```

## Seção 9 — Regras de negócio
- Uma regra por linha, com ID `RN-NN`, escrita de forma declarativa (condição → resultado) e **com exemplo concreto** na terceira coluna.
- Cite o código de erro resultante dentro da própria regra.
- Para regras sobre mensagens assíncronas, diga sempre: o que acontece com duplicatas, com mensagens inválidas e se há efeito colateral (publicação, DLQ).

## Seção 10 — Catálogo de erros
1. Defina **um** formato de corpo de erro, com exemplo JSON.
2. Tabela código × HTTP × condição. Todo código usado em qualquer CA tem de estar aqui, e todo código daqui tem de aparecer em pelo menos um CA.
3. **Ordem de verificação:** lista numerada global. Se houver risco de validação automática do framework furar a ordem, avise explicitamente (como na ESP-NEG-001).

## Seção 11 — Requisitos não funcionais
Use as características da ISO/IEC 25010. Cada RNF precisa de **métrica + limiar + forma de verificação**. Se não tiver como medir, não é RNF; é intenção.

| Ruim | Bom |
|---|---|
| "O serviço deve ser rápido." | "300 lances sequenciais aceitos em < 3 s no cliente de teste em processo." |
| "Valores monetários com precisão." | "Aritmética com `Decimal`; teto `0.30`, incremento `0.10` → lance `0.20` aceito." |
| "Manter ordem no Kafka." | "100% das mensagens com `key == leilao_id`." |

Dica: um bom RNF de exatidão monetária é um caso em que `float` falha (`0.30 − 0.10 < 0.20` em ponto flutuante). Ele separa implementações corretas de aparentemente corretas.

## Seção 12 — Matriz de rastreabilidade
Uma linha por requisito (RF e RNF), apontando regras, interfaces e CAs. Verifique os dois sentidos: nenhum RF sem CA e nenhum CA sem RF.
Registre aqui as exceções justificadas à regra de cenário de erro por RF. Diferencie atributos da entidade, campos derivados da resposta e campos do envelope de evento; eles não precisam ter tabelas idênticas.

## Seção 13 — Premissas, decisões e questões
Registre toda suposição feita durante a análise. Antes do gate G1, **nenhuma** linha pode estar como "Questão" sem decisão. Decisões aqui evitam que a LLM tome a mesma decisão sozinha (e diferente).

**13.1 Casos de borda obrigatórios** (novidade da v1.1). Decida cada linha da tabela, mesmo que a resposta pareça óbvia. Foi exatamente nesses pontos que as LLMs do piloto precisaram decidir sozinhas e deixaram comentários `# DECISÃO:`. Exemplos de decisão da ESP-NEG-001:
- string só com espaços = vazia (inválida);
- `Idempotency-Key` vazio = ausente;
- evento duplicado **e** inválido → a validação vem antes, então vai para a DLQ;
- `event_id` numérico → chave da DLQ é `str(event_id)`;
- relógio sem fuso → tratar como UTC;
- falha de `publish` → fora do escopo (outbox no adaptador real);
- 404/405 de rota inexistente e `/docs` → padrão do framework.

Também na §5.1, responda às três perguntas sobre comportamento das portas: publicação síncrona/reentrante, ordem validar → alterar → publicar e garantias do relógio.

## Seção 14 — Checklist de prontidão (DoR)
Preenchido pelo **QA** no gate G1. Um item desmarcado bloqueia a geração. Remova os comentários de orientação do modelo antes de enviar o documento à LLM.

## Seção 15 — Histórico
Registre cada versão, inclusive as mudanças feitas na fase F8 (causa raiz), citando o CA que motivou a mudança.

---

## Como enviar o documento à LLM
1. Para reproduzir o experimento histórico, use `experimento/prompt_geracao.md` com a especificação v1.1. Para uma nova rodada com o modelo revisado, use `experimento/prompt_geracao_v1.2_proposta.md` após aprovação da especificação; o documento é a única fonte de informação.
2. Contexto novo, sem histórico de conversa e sem os testes.
3. Não corrija o código à mão antes de medir: a medição avalia o **documento**.
4. Rode `python3 experimento/avaliar.py <diretório_gerado>` e registre C_ca e C_rf.
   Para conservar o XML e a saída do pytest, use `--evidencias <diretório>` e identifique modelo, versão do documento, versão da LLM e ambiente em um registro da execução.
5. Se C_ca < 0,85, siga para a fase F8 do processo.
