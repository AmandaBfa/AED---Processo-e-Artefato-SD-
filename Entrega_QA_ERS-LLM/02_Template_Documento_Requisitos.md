# {{ID-DO-DOCUMENTO}} — Especificação de Requisitos: {{Nome do Serviço}}

<!--
MODELO PADRÃO DE ESPECIFICAÇÃO DE REQUISITOS ORIENTADA A LLM (ERS-LLM) — versão 1.2, proposta após auditoria
Portal B2B Distribuído · Grupo de QA

Como usar:
  1. Copie este arquivo e renomeie para  ESP-<SIGLA>-<NNN>_<Servico>.md
  2. Substitua todo texto entre {{ }}. Não deixe nenhum {{ }} no documento final.
  3. Comentários HTML (como este) são orientações de preenchimento: apague-os antes de
     enviar o documento à LLM (eles consomem contexto e podem ser lidos como requisito).
  4. Siga o arquivo "03_Instrucoes_Preenchimento.md" seção por seção.
  5. O documento só pode ser enviado para geração depois de passar no Checklist da seção 14.

Regra de ouro: se um comportamento não está escrito aqui, a LLM vai inventá-lo.
Se não dá para escrever um teste para uma frase, a frase não é requisito.
-->

## 0. Metadados

| Campo | Valor |
|---|---|
| Identificador | {{ESP-XXX-000}} |
| Versão | {{1.0}} |
| Status | {{Rascunho \| Em revisão \| Aprovado para geração}} |
| Serviço / Bounded context | {{nome do microsserviço na arquitetura}} |
| Autores (PO / Dev / QA) | {{nomes}} |
| Data | {{AAAA-MM-DD}} |
| Documentos relacionados | {{diagrama de arquitetura, outras ESPs}} |

## 1. Diretivas para a LLM geradora

> Esta seção é lida pela LLM antes de qualquer outra. Não altere a estrutura; ajuste apenas os valores.

1. Implemente **exatamente** o que está especificado. Não adicione endpoints, campos, tópicos, perfis ou regras que não estejam neste documento.
2. **Ordem de precedência** quando houver conflito aparente: Catálogo de erros (§10) e Contratos (§7) > Critérios de aceitação (§8) > Regras de negócio (§9) > Requisitos funcionais (§8) > texto descritivo.
3. Nomes de campos, tópicos, códigos de erro, rotas e valores de enumeração são **literais**: use-os byte a byte, com a mesma grafia e caixa.
4. Quando algo não estiver definido, escolha o comportamento mais simples que **não viole** nenhum item deste documento e registre a decisão em um comentário `# DECISÃO:` no código.
5. Entregue código completo e executável. Proibido: `TODO`, `pass` como implementação, pseudocódigo, trechos omitidos ("...").
6. Saída: grave todos os arquivos completos na estrutura do §5. Na resposta final, liste seus caminhos relativos.

## 2. Contexto

### 2.1 Objetivo do serviço
{{Uma ou duas frases: que problema de negócio este serviço resolve.}}

### 2.2 Posição na arquitetura
{{Com quem o serviço conversa, de forma síncrona (REST) e assíncrona (eventos). Cite o fluxo de negócio em que ele participa.}}

```text
{{diagrama textual: produtores → [tópico] → este serviço → [tópico] → consumidores}}
```

## 3. Escopo

### 3.1 Dentro do escopo
- {{capacidade 1}}

### 3.2 Fora do escopo (não implementar)
- {{capacidade explicitamente excluída — evita que a LLM "complete" o sistema}}

## 4. Glossário

| Termo | Definição precisa |
|---|---|
| {{termo}} | {{definição sem ambiguidade; inclua unidade/formato quando houver}} |

## 5. Restrições técnicas

| Item | Valor obrigatório |
|---|---|
| Linguagem / versão | {{ex.: Python 3.12}} |
| Framework | {{ex.: FastAPI}} |
| Dependências permitidas | {{lista fechada — qualquer outra é proibida}} |
| Persistência | {{ex.: em memória, por instância da aplicação}} |
| Estrutura de arquivos | {{árvore de diretórios e arquivos obrigatórios}} |
| Ponto de entrada | {{assinatura exata da função/fábrica que os testes vão chamar}} |
| Formato de data/hora | {{ex.: ISO-8601 UTC com sufixo Z}} |
| Formato monetário | {{ex.: string decimal com 2 casas; aritmética com Decimal}} |

### 5.1 Portas (interfaces de infraestrutura)
<!-- Toda dependência externa (broker, relógio, banco, outro serviço) entra como porta injetada.
     É isso que permite ao QA substituir a infraestrutura por dublês nos testes. -->

```{{linguagem}}
{{assinaturas exatas das interfaces: EventBus, Clock, Repositório...}}
```

Comportamento das portas (obrigatório responder):
- {{A publicação é síncrona? Pode chamar handlers no mesmo fluxo (reentrância)?}}
- {{Ordem dentro de uma escrita: validar → alterar estado → publicar? O que fazer se publicar falhar?}}
- {{Garantias do relógio (fuso sempre presente?).}}

## 6. Modelo de domínio

### 6.1 Entidades

#### {{Entidade}}
| Atributo | Tipo | Obrigatório | Restrições / origem |
|---|---|---|---|
| {{atributo}} | {{tipo}} | {{Sim/Não}} | {{faixa, formato, regex, quem gera o valor}} |

### 6.2 Estados e transições

| Estado atual | Evento / comando | Condição | Próximo estado |
|---|---|---|---|
| {{ESTADO}} | {{ação}} | {{guarda}} | {{ESTADO}} |

## 7. Contratos de interface

### 7.1 Autenticação e contexto da requisição
{{Quem autentica, quais cabeçalhos chegam ao serviço, valores aceitos, o que fazer quando faltam.}}

### 7.2 API REST

| ID | Método | Rota | Perfis | Sucesso | Erros possíveis (na ordem de verificação) |
|---|---|---|---|---|---|
| {{API-01}} | {{GET}} | {{/rota/{id}}} | {{perfis}} | {{200}} | {{401 → 404 → ...}} |

#### {{API-01}} — {{nome}}
Requisição:
```json
{{exemplo completo e válido}}
```
Resposta {{200}}:
```json
{{exemplo completo, com todos os campos}}
```

### 7.3 Eventos consumidos

| Tópico | Produtor | Chave | Ação | Em caso de mensagem inválida |
|---|---|---|---|---|
| {{topico}} | {{serviço}} | {{campo}} | {{RF-xx}} | {{descartar / DLQ}} |

Exemplo de mensagem:
```json
{{envelope + payload}}
```

### 7.4 Eventos publicados

| Tópico | Quando | Chave de partição | Payload |
|---|---|---|---|
| {{topico}} | {{gatilho}} | {{campo}} | {{campos}} |

Exemplo:
```json
{{envelope + payload}}
```

## 8. Requisitos funcionais

<!-- Um bloco por requisito. Enunciado no padrão EARS. Cada RF tem ≥ 1 CA de caminho feliz
     e ≥ 1 CA de erro. CAs em Gherkin, com valores concretos (nunca "um valor válido"). -->

### {{RF-01}} — {{título}}
- **Prioridade:** {{Must \| Should \| Could}}
- **Enunciado (EARS):** {{Quando <gatilho>, o serviço deve <resposta>.}}
- **Regras aplicáveis:** {{RN-xx, RN-yy}}
- **Interface:** {{API-xx / tópico}}

**Critérios de aceitação**
```gherkin
# CA-{{NN}}
Cenário: {{nome}}
  Dado {{estado inicial com valores concretos}}
  Quando {{ação concreta}}
  Então {{resultado observável: status, corpo, evento, estado}}
```

## 9. Regras de negócio

| ID | Regra | Exemplo concreto |
|---|---|---|
| {{RN-01}} | {{regra declarativa, verificável}} | {{entrada → saída esperada}} |

## 10. Catálogo de erros

Formato único de erro:
```json
{{ex.: {"erro": {"codigo": "CODIGO", "mensagem": "texto"}}}}
```

| Código | HTTP | Quando ocorre |
|---|---|---|
| {{CODIGO}} | {{4xx}} | {{condição exata}} |

Respostas fora do catálogo: {{rota inexistente, método não permitido, documentação automática do framework — manter padrão do framework ou não?}}

**Ordem de verificação** (quando mais de um erro se aplica, retornar o primeiro da lista):
1. {{...}}

## 11. Requisitos não funcionais

| ID | Característica (ISO/IEC 25010) | Requisito | Métrica e limiar | Verificação |
|---|---|---|---|---|
| {{RNF-01}} | {{Eficiência de desempenho}} | {{enunciado}} | {{ex.: 300 operações < 3 s}} | {{teste automatizado / inspeção}} |

## 12. Matriz de rastreabilidade

| Requisito | Regras | Interfaces | Critérios de aceitação |
|---|---|---|---|
| {{RF-01}} | {{RN-01}} | {{API-01}} | {{CA-01, CA-02}} |

## 13. Premissas, decisões e questões em aberto

| ID | Tipo | Descrição | Decisão |
|---|---|---|---|
| {{Q-01}} | {{Premissa \| Decisão \| Questão}} | {{texto}} | {{resolução — nenhuma questão pode ficar aberta no status "Aprovado para geração"}} |

### 13.1 Casos de borda obrigatórios
<!-- Incluído na v1.1: no piloto, as LLMs registraram 9 comentários "# DECISÃO:" exatamente nestes pontos.
     Cada linha deve ter uma decisão explícita (ou "não se aplica"). -->

| Caso de borda | Decisão |
|---|---|
| String vazia ou só com espaços em campos obrigatórios | {{inválida / aceita}} |
| Cabeçalho opcional presente porém vazio | {{equivale a ausente / erro}} |
| Mensagem duplicada **e** inválida (qual regra vence: duplicidade ou validação?) | {{...}} |
| Campo de chave/ID com tipo inesperado (ex.: número no lugar de string) | {{...}} |
| Data/hora sem fuso horário | {{...}} |
| Falha da porta de publicação / banco | {{...}} |
| Rotas e métodos fora do contrato | {{...}} |

## 14. Checklist de prontidão (Definition of Ready) — preenchido pelo QA

- [ ] Nenhum `{{ }}` restante; comentários de orientação removidos.
- [ ] Todo RF tem enunciado EARS, prioridade e CAs de sucesso e erro quando aplicáveis; exceções justificadas na matriz.
- [ ] Todo CA usa valores concretos e resultado observável.
- [ ] Todo código de erro citado em CA existe no §10 e vice-versa.
- [ ] Ordem de verificação de erros definida para cada endpoint.
- [ ] Campos de entidade, projeções de resposta e campos derivados estão mapeados; exemplos JSON respeitam os contratos.
- [ ] Todo tópico citado tem produtor/consumidor, chave e exemplo.
- [ ] Toda dependência externa está modelada como porta (§5.1).
- [ ] Todo RNF tem métrica, limiar e forma de verificação.
- [ ] Matriz de rastreabilidade completa (nenhum RF sem CA, nenhum CA órfão).
- [ ] Não há palavras vagas sem quantificação ("rápido", "adequado", "etc.", "deve tratar erros").
- [ ] Seção 13 sem questões abertas e tabela 13.1 (casos de borda) toda decidida.
- [ ] Comentários `# DECISÃO:` da última geração (se houver) analisados e incorporados como regra.

## 15. Histórico de versões

| Versão | Data | Autor | Mudança |
|---|---|---|---|
| {{1.0}} | {{AAAA-MM-DD}} | {{nome}} | {{criação}} |

<!-- Histórico do próprio MODELO: v1.0 (criação) → v1.1 (após piloto: comportamento das portas em §5.1,
     respostas fora do catálogo em §10, tabela 13.1 de casos de borda, 2 itens novos no checklist). -->
<!-- v1.2 proposta: alinhamento das diretivas de saída, exceções justificadas nos CAs e mapeamento de campos. -->
