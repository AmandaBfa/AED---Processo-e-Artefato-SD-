# ESP-NEG-001 — Especificação de Requisitos: Serviço de Negociação / Leilão

## 0. Metadados

| Campo | Valor |
|---|---|
| Identificador | ESP-NEG-001 |
| Versão | 1.1 |
| Status | Aprovado para geração |
| Serviço / Bounded context | Microsserviço 6 — Negociação / Leilão (Portal B2B Distribuído) |
| Autores (PO / Dev / QA) | Grupo de QA — Amanda Barbosa, Kayky Momoli, Lavínia Maria Moreira, Gabriel Jonas Lucio, Matheus Silva Pains, Igor Santos, Nicole Gomes C Yssob, Igor Nascimento Balduíno, Antonio Calixto |
| Data | 2026-10-17 |
| Documentos relacionados | Arquitetura do Portal B2B Distribuído (Microsserviços + Kafka) |

## 1. Diretivas para a LLM geradora

1. Implemente **exatamente** o que está especificado. Não adicione endpoints, campos, tópicos, perfis ou regras que não estejam neste documento.
2. **Ordem de precedência** quando houver conflito aparente: Catálogo de erros (§10) e Contratos (§7) > Critérios de aceitação (§8) > Regras de negócio (§9) > Requisitos funcionais (§8) > texto descritivo.
3. Nomes de campos, tópicos, códigos de erro, rotas e valores de enumeração são **literais**: use-os byte a byte, com a mesma grafia e caixa.
4. Quando algo não estiver definido, escolha o comportamento mais simples que **não viole** nenhum item deste documento e registre a decisão em um comentário `# DECISÃO:` no código.
5. Entregue código completo e executável. Proibido: `TODO`, `pass` como implementação, pseudocódigo, trechos omitidos ("...").
6. Formato da resposta: os arquivos da estrutura do §5, cada um com caminho relativo e conteúdo completo.

## 2. Contexto

### 2.1 Objetivo do serviço
Conduzir leilões entre empresas do portal: receber lances, aplicar as regras do leilão e definir o vencedor, publicando os eventos que alimentam o serviço de Pedidos.

### 2.2 Posição na arquitetura
O serviço de Mercado (Matching Engine) decide que uma demanda será negociada por leilão e publica `leilao_iniciado`. Este serviço consome o evento, abre o leilão, recebe lances pela API REST (via API Gateway) e, ao encerrar, publica `negociacao_fechada`, que o serviço de Pedidos usa para criar o pedido (passos 5 → 6 → 7 do fluxo principal do negócio). A cada lance aceito publica `lance_realizado`.

```text
Mercado ──[leilao_iniciado]──► Negociação/Leilão ──[lance_realizado]────► (assinantes)
Frontend ─► API Gateway ─REST─►        │          ──[negociacao_fechada]─► Pedidos
                                       └──────────[negociacao_dlq]──────► (operação)
```

## 3. Escopo

### 3.1 Dentro do escopo
- Abertura de leilão a partir do evento `leilao_iniciado`.
- Leilão **REVERSO** (empresas com perfil FORNECEDOR disputam vender; vence o **menor** lance).
- Leilão **DIRETO** (empresas com perfil COMPRADOR disputam comprar; vence o **maior** lance).
- Registro, validação e listagem de lances; consulta do leilão.
- Encerramento do leilão por um ADMIN e definição do vencedor.
- Publicação dos eventos `lance_realizado`, `negociacao_fechada` e `negociacao_dlq`.
- Endpoint de saúde.

### 3.2 Fora do escopo (não implementar)
- Venda direta e propostas fora de leilão.
- Encerramento automático por agendador (o encerramento é sempre um comando explícito — API-05).
- Autenticação/emissão de tokens (feita pelo API Gateway).
- Persistência em banco de dados, cliente Kafka real, cancelamento de leilão, edição ou exclusão de lances.

## 4. Glossário

| Termo | Definição precisa |
|---|---|
| Leilão | Disputa por uma demanda, identificada por `leilao_id`, com tipo, preço inicial, incremento mínimo e instante de encerramento. |
| Lance | Oferta de valor feita por uma empresa em um leilão. |
| Melhor lance | REVERSO: o lance de **menor** valor. DIRETO: o lance de **maior** valor. Pelas regras RN-04/RN-05, é sempre o último lance aceito. |
| Líder | Empresa autora do melhor lance atual. |
| Incremento mínimo | Diferença mínima, em valor absoluto, entre um novo lance e o melhor lance atual. |
| Valor monetário | Número decimal com no máximo 2 casas, representado em JSON como **string** (ex.: `"1000.00"`). |
| Instante | Data/hora em UTC no formato ISO-8601 com sufixo `Z`, sem frações de segundo (ex.: `"2026-10-17T12:00:00Z"`). |
| Agora | Valor retornado por `clock.now()` (porta Clock). O serviço nunca usa o relógio do sistema. |
| Leilão aceitando lances | `status == "ABERTO"` **e** `agora < encerra_em`. |

## 5. Restrições técnicas

| Item | Valor obrigatório |
|---|---|
| Linguagem / versão | Python 3.12 |
| Framework | FastAPI (com Pydantic v2, se usado) |
| Dependências permitidas | Biblioteca padrão do Python, `fastapi`, `pydantic`, `starlette`. Nenhuma outra. |
| Persistência | Em memória, **por instância** criada por `create_app`. Proibido estado global de módulo compartilhado entre instâncias. |
| Estrutura de arquivos | `app/__init__.py` e `app/main.py` obrigatórios; outros módulos dentro de `app/` são permitidos. |
| Ponto de entrada | `app.main.create_app(event_bus: EventBus, clock: Clock) -> fastapi.FastAPI` |
| Formato de data/hora | Instante (ver glossário). |
| Formato monetário | Valor monetário (ver glossário). Toda aritmética e comparação com `decimal.Decimal`; proibido `float`. Respostas sempre com exatamente 2 casas (`"100"` recebido → `"100.00"` devolvido). |

### 5.1 Portas (interfaces de infraestrutura)

```python
from datetime import datetime
from typing import Callable, Protocol

class EventBus(Protocol):
    def publish(self, topic: str, key: str, message: dict) -> None: ...
    def subscribe(self, topic: str, handler: Callable[[dict], None]) -> None: ...

class Clock(Protocol):
    def now(self) -> datetime: ...   # datetime com timezone UTC
```

- `create_app` deve chamar `event_bus.subscribe("leilao_iniciado", handler)` durante a criação da aplicação.
- O `handler` recebe a mensagem completa (envelope, §7.3) como `dict` e **nunca** deve propagar exceção.
- Toda publicação usa `event_bus.publish(topic, key, message)`, com `message` no formato de envelope (§7.4).
- As implementações concretas das portas são fornecidas por quem chama `create_app`; o serviço não as implementa.
- `publish` pode ser síncrono e pode, no mesmo fluxo de execução, chamar handlers inscritos. O serviço não pode entrar em deadlock nesse caso (use `threading.RLock` ou publique fora da seção crítica).
- Ordem dentro de uma operação de escrita: validar → alterar o estado em memória → publicar o evento. Falhas lançadas por `publish` estão fora do escopo (o adaptador real usará *transactional outbox*).
- `clock.now()` sempre retorna `datetime` com fuso; se vier sem fuso, tratar como UTC.

## 6. Modelo de domínio

### 6.1 Entidades

#### Leilao
| Atributo | Tipo | Obrigatório | Restrições / origem |
|---|---|---|---|
| leilao_id | string | Sim | Vem do evento; não vazio; único. |
| demanda_id | string | Sim | Vem do evento; não vazio. |
| produto_id | string | Sim | Vem do evento; não vazio. |
| quantidade | inteiro | Sim | Vem do evento; > 0. |
| tipo | enum | Sim | `"REVERSO"` ou `"DIRETO"` (campo `tipo_leilao` do evento). |
| preco_inicial | valor monetário | Sim | > 0. REVERSO: preço-teto. DIRETO: preço mínimo. |
| incremento_minimo | valor monetário | Sim | > 0. |
| encerra_em | instante | Sim | Vem do evento. |
| status | enum | Sim | `"ABERTO"`, `"ENCERRADO"` ou `"DESERTO"`. Inicial: `"ABERTO"`. |
| lances | lista de Lance | Sim | Inicialmente vazia. |

#### Lance
| Atributo | Tipo | Obrigatório | Restrições / origem |
|---|---|---|---|
| lance_id | string | Sim | UUID4 gerado pelo serviço. |
| leilao_id | string | Sim | Leilão ao qual pertence. |
| empresa_id | string | Sim | Cabeçalho `X-Empresa-Id`. |
| valor | valor monetário | Sim | Corpo da requisição. |
| sequencia | inteiro | Sim | 1 para o primeiro lance aceito do leilão, incrementa de 1 em 1. |
| criado_em | instante | Sim | `clock.now()` no momento da aceitação. |

### 6.2 Estados e transições

| Estado atual | Evento / comando | Condição | Próximo estado |
|---|---|---|---|
| (inexistente) | `leilao_iniciado` válido | `leilao_id` ainda não existe | ABERTO |
| ABERTO | API-05 encerrar | possui ≥ 1 lance | ENCERRADO |
| ABERTO | API-05 encerrar | possui 0 lances | DESERTO |
| ENCERRADO / DESERTO | qualquer | — | (estado final, sem transições) |

`agora >= encerra_em` **não** altera o `status`; apenas faz o leilão deixar de aceitar lances.

## 7. Contratos de interface

### 7.1 Autenticação e contexto da requisição
O API Gateway valida o JWT e repassa dois cabeçalhos: `X-Empresa-Id` (string não vazia) e `X-Perfil` (um de `COMPRADOR`, `FORNECEDOR`, `TRANSPORTADORA`, `ADMIN`). Em todas as rotas exceto `/health`: se algum dos dois faltar, estiver vazio, ou `X-Perfil` não for um dos quatro valores → `401 NAO_AUTENTICADO`.

### 7.2 API REST

| ID | Método | Rota | Perfis | Sucesso | Erros possíveis (na ordem de verificação) |
|---|---|---|---|---|---|
| API-01 | GET | `/health` | público | 200 | — |
| API-02 | GET | `/leiloes/{leilao_id}` | todos | 200 | 401 → 404 |
| API-03 | GET | `/leiloes/{leilao_id}/lances` | todos | 200 | 401 → 404 |
| API-04 | POST | `/leiloes/{leilao_id}/lances` | ver RN-03 | 201 | 401 → 404 → 403 → 409 `LEILAO_ENCERRADO` → 422 `VALOR_INVALIDO` → 409 `LANCE_JA_LIDER` → 422 `LANCE_INSUFICIENTE` |
| API-05 | POST | `/leiloes/{leilao_id}/encerrar` | ADMIN | 200 | 401 → 404 → 403 → 409 |

#### API-01 — Saúde
Resposta 200: `{"status": "UP"}`

#### API-02 — Consultar leilão
Resposta 200:
```json
{
  "leilao_id": "LEI-001",
  "demanda_id": "DEM-10",
  "produto_id": "PROD-7",
  "quantidade": 500,
  "tipo": "REVERSO",
  "preco_inicial": "1000.00",
  "incremento_minimo": "10.00",
  "encerra_em": "2026-10-20T18:00:00Z",
  "status": "ABERTO",
  "aceitando_lances": true,
  "melhor_lance": {
    "lance_id": "3f0c7a9e-2b1d-4c55-9a43-6a1d2f0e8b11",
    "empresa_id": "FORN-A",
    "valor": "990.00",
    "sequencia": 1
  },
  "total_lances": 1
}
```
- `melhor_lance` é `null` quando não há lances.
- `melhor_lance.empresa_id` segue RN-09 (sigilo).

#### API-03 — Listar lances
Resposta 200 (ordenado por `sequencia` crescente; lista vazia → `{"itens": []}`):
```json
{
  "itens": [
    {
      "lance_id": "3f0c7a9e-2b1d-4c55-9a43-6a1d2f0e8b11",
      "leilao_id": "LEI-001",
      "empresa_id": "FORN-A",
      "valor": "990.00",
      "sequencia": 1,
      "criado_em": "2026-10-17T12:00:00Z"
    }
  ]
}
```
- `empresa_id` de cada item segue RN-09 (sigilo).

#### API-04 — Registrar lance
Cabeçalhos: `X-Empresa-Id`, `X-Perfil`, opcional `Idempotency-Key` (RN-10).
Requisição:
```json
{ "valor": "990.00" }
```
Resposta 201 (sem mascaramento — é o próprio lance do solicitante):
```json
{
  "lance_id": "3f0c7a9e-2b1d-4c55-9a43-6a1d2f0e8b11",
  "leilao_id": "LEI-001",
  "empresa_id": "FORN-A",
  "valor": "990.00",
  "sequencia": 1,
  "criado_em": "2026-10-17T12:00:00Z"
}
```

#### API-05 — Encerrar leilão
Sem corpo. Resposta 200 — com vencedor:
```json
{
  "leilao_id": "LEI-001",
  "status": "ENCERRADO",
  "resultado": "VENCEDOR_DEFINIDO",
  "vencedor_empresa_id": "FORN-B",
  "valor_vencedor": "980.00",
  "lance_vencedor_id": "9b2e...",
  "total_lances": 2
}
```
Resposta 200 — sem lances:
```json
{
  "leilao_id": "LEI-002",
  "status": "DESERTO",
  "resultado": "DESERTO",
  "vencedor_empresa_id": null,
  "valor_vencedor": null,
  "lance_vencedor_id": null,
  "total_lances": 0
}
```

### 7.3 Eventos consumidos

| Tópico | Produtor | Chave | Ação | Em caso de mensagem inválida |
|---|---|---|---|---|
| `leilao_iniciado` | Mercado | `leilao_id` | RF-01 | Publicar em `negociacao_dlq` (RN-02) |

Exemplo de mensagem recebida pelo handler:
```json
{
  "event_id": "0b6a1c1e-8d0f-4a37-9f5e-1f2b3c4d5e6f",
  "tipo": "leilao_iniciado",
  "versao": 1,
  "ocorrido_em": "2026-10-17T11:59:00Z",
  "payload": {
    "leilao_id": "LEI-001",
    "demanda_id": "DEM-10",
    "produto_id": "PROD-7",
    "quantidade": 500,
    "tipo_leilao": "REVERSO",
    "preco_inicial": "1000.00",
    "incremento_minimo": "10.00",
    "encerra_em": "2026-10-20T18:00:00Z"
  }
}
```

### 7.4 Eventos publicados

Envelope comum a todas as mensagens publicadas:

| Campo | Valor |
|---|---|
| event_id | UUID4 novo, único por mensagem publicada |
| tipo | igual ao nome do tópico |
| versao | `1` (inteiro) |
| ocorrido_em | instante = `clock.now()` |
| payload | objeto específico do tópico |

| Tópico | Quando | Chave de partição | Payload |
|---|---|---|---|
| `lance_realizado` | Lance aceito (RF-03) | `leilao_id` | `leilao_id`, `lance_id`, `empresa_id`, `valor`, `sequencia` |
| `negociacao_fechada` | Leilão encerrado (RF-06) | `leilao_id` | `leilao_id`, `demanda_id`, `resultado`, `vencedor_empresa_id`, `valor_vencedor`, `lance_vencedor_id`, `total_lances` |
| `negociacao_dlq` | Mensagem consumida inválida (RN-02) | `str(event_id)` da mensagem original, ou `"desconhecido"` se ausente, `null` ou vazio | `topico_origem`, `motivo` (string não vazia), `mensagem_original` (a mensagem recebida, intacta) |

Exemplo `lance_realizado`:
```json
{
  "event_id": "c1d2...",
  "tipo": "lance_realizado",
  "versao": 1,
  "ocorrido_em": "2026-10-17T12:00:00Z",
  "payload": {
    "leilao_id": "LEI-001",
    "lance_id": "3f0c7a9e-2b1d-4c55-9a43-6a1d2f0e8b11",
    "empresa_id": "FORN-A",
    "valor": "990.00",
    "sequencia": 1
  }
}
```
O payload de `negociacao_fechada` tem os mesmos valores dos campos homônimos da resposta da API-05, mais `demanda_id`.

## 8. Requisitos funcionais

### RF-01 — Abrir leilão a partir de evento
- **Prioridade:** Must
- **Enunciado (EARS):** Quando uma mensagem válida do tópico `leilao_iniciado` for recebida e o `leilao_id` ainda não existir, o serviço deve criar o leilão com status `ABERTO`.
- **Regras aplicáveis:** RN-01, RN-02
- **Interface:** tópico `leilao_iniciado`

```gherkin
# CA-01
Cenário: Evento válido abre leilão
  Dado que o leilão "LEI-001" não existe
  Quando o handler recebe leilao_iniciado com leilao_id "LEI-001", tipo_leilao "REVERSO", preco_inicial "1000.00", incremento_minimo "10.00", quantidade 500
  Então GET /leiloes/LEI-001 retorna 200 com status "ABERTO", tipo "REVERSO", preco_inicial "1000.00", incremento_minimo "10.00", quantidade 500 e total_lances 0

# CA-02
Cenário: Evento duplicado é ignorado (idempotência do consumidor)
  Dado que o leilão "LEI-001" já foi aberto com preco_inicial "1000.00"
  Quando o handler recebe novamente leilao_iniciado para "LEI-001" com preco_inicial "5000.00" e outro event_id
  Então o leilão continua com preco_inicial "1000.00"
  E nenhuma mensagem é publicada

# CA-03
Cenário: Tipo de leilão inválido vai para a DLQ
  Quando o handler recebe leilao_iniciado com event_id "E-9", leilao_id "LEI-X" e tipo_leilao "HOLANDES"
  Então GET /leiloes/LEI-X retorna 404
  E é publicada em "negociacao_dlq" uma mensagem com chave "E-9" e payload com topico_origem "leilao_iniciado", motivo não vazio e mensagem_original igual à mensagem recebida

# CA-04
Cenário: Campo obrigatório ausente vai para a DLQ sem exceção
  Quando o handler recebe leilao_iniciado sem o campo encerra_em
  Então o handler não lança exceção
  E é publicada uma mensagem em "negociacao_dlq"
  E o leilão não é criado
```

### RF-02 — Consultar leilão
- **Prioridade:** Must
- **Enunciado (EARS):** Quando um usuário autenticado solicitar `GET /leiloes/{leilao_id}`, o serviço deve retornar o estado atual do leilão.
- **Regras aplicáveis:** RN-08, RN-09
- **Interface:** API-02

```gherkin
# CA-05
Cenário: Consulta de leilão sem lances
  Dado o leilão "LEI-001" aberto, encerra_em no futuro e sem lances
  Quando um FORNECEDOR consulta GET /leiloes/LEI-001
  Então a resposta é 200 com todos os campos do exemplo da API-02, aceitando_lances true, melhor_lance null e total_lances 0

# CA-06
Cenário: Leilão inexistente
  Quando um usuário autenticado consulta GET /leiloes/NAO-EXISTE
  Então a resposta é 404 com erro.codigo "LEILAO_NAO_ENCONTRADO"

# CA-07
Cenário: Requisição sem autenticação
  Quando GET /leiloes/LEI-001 é chamado sem os cabeçalhos X-Empresa-Id e X-Perfil
  Então a resposta é 401 com erro.codigo "NAO_AUTENTICADO"

# CA-08
Cenário: Prazo vencido não muda o status
  Dado o leilão "LEI-001" ABERTO com encerra_em "2026-10-20T18:00:00Z"
  E o relógio marca "2026-10-20T18:00:00Z"
  Quando o leilão é consultado
  Então status é "ABERTO" e aceitando_lances é false
```

### RF-03 — Registrar lance
- **Prioridade:** Must
- **Enunciado (EARS):** Quando uma empresa autorizada enviar `POST /leiloes/{leilao_id}/lances` para um leilão aceitando lances com um valor que satisfaça as regras, o serviço deve registrar o lance, responder 201 e publicar `lance_realizado`.
- **Regras aplicáveis:** RN-03, RN-04, RN-05, RN-06, RN-07, RN-11
- **Interface:** API-04, tópico `lance_realizado`

```gherkin
# CA-09
Cenário: Primeiro lance válido em leilão reverso
  Dado o leilão REVERSO "LEI-001" com preco_inicial "1000.00" e relógio em "2026-10-17T12:00:00Z"
  Quando FORN-A (FORNECEDOR) envia valor "1000.00"
  Então a resposta é 201 com lance_id UUID, leilao_id "LEI-001", empresa_id "FORN-A", valor "1000.00", sequencia 1, criado_em "2026-10-17T12:00:00Z"

# CA-10
Cenário: Lance aceito publica evento
  Quando FORN-A envia lance válido "990.00" em "LEI-001"
  Então é publicada exatamente uma mensagem em "lance_realizado" com chave "LEI-001", envelope conforme §7.4 e payload com leilao_id, lance_id (igual ao da resposta), empresa_id, valor "990.00" e sequencia

# CA-11
Cenário: Primeiro lance acima do teto em leilão reverso
  Dado o leilão REVERSO com preco_inicial "1000.00"
  Quando FORN-A envia valor "1000.01"
  Então a resposta é 422 com erro.codigo "LANCE_INSUFICIENTE"

# CA-12
Cenário: Decremento mínimo em leilão reverso
  Dado o leilão REVERSO com incremento_minimo "10.00" e melhor lance "1000.00" de FORN-A
  Quando FORN-B envia valor "995.00"
  Então a resposta é 422 com erro.codigo "LANCE_INSUFICIENTE"
  Quando FORN-B envia valor "990.00"
  Então a resposta é 201

# CA-13
Cenário: Regras de valor em leilão direto
  Dado o leilão DIRETO com preco_inicial "500.00" e incremento_minimo "5.00"
  Quando COMP-A (COMPRADOR) envia "499.99"
  Então a resposta é 422 com erro.codigo "LANCE_INSUFICIENTE"
  Quando COMP-A envia "500.00"
  Então a resposta é 201
  Quando COMP-B envia "504.99"
  Então a resposta é 422 com erro.codigo "LANCE_INSUFICIENTE"
  Quando COMP-B envia "505.00"
  Então a resposta é 201

# CA-14
Cenário: Perfil não permitido para o tipo de leilão
  Quando um COMPRADOR envia lance em leilão REVERSO
  Então a resposta é 403 com erro.codigo "PERFIL_NAO_PERMITIDO"
  Quando um FORNECEDOR envia lance em leilão DIRETO
  Então a resposta é 403 com erro.codigo "PERFIL_NAO_PERMITIDO"
  Quando um ADMIN ou TRANSPORTADORA envia lance em qualquer leilão
  Então a resposta é 403 com erro.codigo "PERFIL_NAO_PERMITIDO"

# CA-15
Cenário: Líder não pode cobrir o próprio lance
  Dado que FORN-A é o líder do leilão REVERSO com "1000.00"
  Quando FORN-A envia "900.00"
  Então a resposta é 409 com erro.codigo "LANCE_JA_LIDER"

# CA-16
Cenário: Lance após o prazo
  Dado o leilão ABERTO com encerra_em "2026-10-20T18:00:00Z" e relógio em "2026-10-20T18:00:00Z"
  Quando um FORNECEDOR envia lance válido
  Então a resposta é 409 com erro.codigo "LEILAO_ENCERRADO"

# CA-17
Cenário: Lance em leilão já encerrado
  Dado o leilão com status "ENCERRADO" ou "DESERTO"
  Quando uma empresa autorizada envia lance
  Então a resposta é 409 com erro.codigo "LEILAO_ENCERRADO"

# CA-18
Cenário: Valor inválido
  Quando o corpo é qualquer um de: {"valor": 990}, {"valor": "abc"}, {"valor": "-5.00"}, {"valor": "0"}, {"valor": "0.00"}, {"valor": "10.123"}, {}, ou um JSON malformado
  Então a resposta é 422 com erro.codigo "VALOR_INVALIDO"

# CA-19
Cenário: Lance em leilão inexistente
  Quando um FORNECEDOR envia lance para "NAO-EXISTE"
  Então a resposta é 404 com erro.codigo "LEILAO_NAO_ENCONTRADO"

# CA-20
Cenário: Autenticação ausente ou inválida
  Quando o lance é enviado sem X-Empresa-Id, ou sem X-Perfil, ou com X-Perfil "HACKER"
  Então a resposta é 401 com erro.codigo "NAO_AUTENTICADO"

# CA-21
Cenário: Precedência de erros
  Quando um corpo inválido {"valor": "abc"} é enviado para um leilão inexistente
  Então a resposta é 404 "LEILAO_NAO_ENCONTRADO"
  Quando um corpo inválido é enviado por um COMPRADOR para um leilão REVERSO
  Então a resposta é 403 "PERFIL_NAO_PERMITIDO"
  Quando um corpo inválido é enviado para um leilão com prazo vencido
  Então a resposta é 409 "LEILAO_ENCERRADO"
  Quando o líder envia um valor que também é insuficiente
  Então a resposta é 409 "LANCE_JA_LIDER"

# CA-22
Cenário: Erro não altera estado nem publica evento
  Dado o leilão com 1 lance
  Quando um lance é rejeitado por qualquer erro
  Então total_lances continua 1 e nenhuma mensagem nova é publicada

# CA-23
Cenário: Consulta reflete o melhor lance
  Dado que FORN-A deu "1000.00" e FORN-B deu "990.00"
  Quando um ADMIN consulta o leilão
  Então melhor_lance tem empresa_id "FORN-B", valor "990.00", sequencia 2 e total_lances é 2
```

### RF-04 — Idempotência de lance
- **Prioridade:** Must
- **Enunciado (EARS):** Quando um `POST /leiloes/{leilao_id}/lances` chegar com um `Idempotency-Key` já usado com sucesso pela mesma empresa no mesmo leilão, o serviço deve retornar a resposta original sem registrar novo lance.
- **Regras aplicáveis:** RN-10
- **Interface:** API-04

```gherkin
# CA-24
Cenário: Reenvio com a mesma chave
  Dado que FORN-A enviou "990.00" com Idempotency-Key "K1" e recebeu 201
  Quando FORN-A reenvia a mesma requisição com Idempotency-Key "K1"
  Então a resposta é 201 com corpo idêntico ao da primeira
  E total_lances é 1
  E apenas uma mensagem foi publicada em "lance_realizado"

# CA-25
Cenário: Chaves diferentes ou empresas diferentes são independentes
  Dado que FORN-A enviou "990.00" com Idempotency-Key "K1"
  Quando FORN-B envia "980.00" com Idempotency-Key "K1"
  Então a resposta é 201 com novo lance_id e sequencia 2
```

### RF-05 — Listar lances
- **Prioridade:** Must
- **Enunciado (EARS):** Quando um usuário autenticado solicitar `GET /leiloes/{leilao_id}/lances`, o serviço deve retornar os lances em ordem crescente de `sequencia`, aplicando sigilo.
- **Regras aplicáveis:** RN-09
- **Interface:** API-03

```gherkin
# CA-26
Cenário: Listagem ordenada
  Dado que FORN-A deu "1000.00" e FORN-B deu "990.00"
  Quando um ADMIN lista os lances
  Então a resposta é 200 com "itens" contendo 2 lances, sequencias 1 e 2, com todos os campos do exemplo da API-03

# CA-27
Cenário: Sigilo entre concorrentes
  Dado que FORN-A deu "1000.00" e FORN-B deu "990.00"
  Quando FORN-A lista os lances
  Então o item 1 tem empresa_id "FORN-A" e o item 2 tem empresa_id "OCULTO"
  E ao consultar o leilão, FORN-A vê melhor_lance.empresa_id "OCULTO"
  E FORN-B vê melhor_lance.empresa_id "FORN-B"
```

### RF-06 — Encerrar leilão
- **Prioridade:** Must
- **Enunciado (EARS):** Quando um ADMIN solicitar `POST /leiloes/{leilao_id}/encerrar` para um leilão ABERTO, o serviço deve definir o resultado, mudar o status e publicar `negociacao_fechada`.
- **Regras aplicáveis:** RN-08, RN-12
- **Interface:** API-05, tópico `negociacao_fechada`

```gherkin
# CA-28
Cenário: Encerramento de leilão reverso com lances
  Dado o leilão REVERSO com lances "1000.00" (FORN-A) e "990.00" (FORN-B)
  Quando um ADMIN encerra o leilão
  Então a resposta é 200 com status "ENCERRADO", resultado "VENCEDOR_DEFINIDO", vencedor_empresa_id "FORN-B", valor_vencedor "990.00", lance_vencedor_id do lance de FORN-B e total_lances 2
  E GET do leilão retorna status "ENCERRADO" e aceitando_lances false

# CA-29
Cenário: Encerramento de leilão direto
  Dado o leilão DIRETO com lances "500.00" (COMP-A) e "510.00" (COMP-B)
  Quando um ADMIN encerra o leilão
  Então vencedor_empresa_id é "COMP-B" e valor_vencedor é "510.00"

# CA-30
Cenário: Leilão deserto
  Dado o leilão sem lances
  Quando um ADMIN encerra o leilão
  Então a resposta é 200 com status "DESERTO", resultado "DESERTO", vencedor_empresa_id null, valor_vencedor null, lance_vencedor_id null e total_lances 0

# CA-31
Cenário: Encerramento publica negociacao_fechada
  Quando um leilão é encerrado (com ou sem lances)
  Então é publicada exatamente uma mensagem em "negociacao_fechada" com chave igual ao leilao_id e payload com demanda_id e os mesmos valores da resposta para resultado, vencedor_empresa_id, valor_vencedor, lance_vencedor_id e total_lances

# CA-32
Cenário: Autorização do encerramento
  Quando um FORNECEDOR tenta encerrar
  Então a resposta é 403 "PERFIL_NAO_PERMITIDO"
  Quando a requisição não tem cabeçalhos
  Então a resposta é 401 "NAO_AUTENTICADO"
  Quando um ADMIN tenta encerrar "NAO-EXISTE"
  Então a resposta é 404 "LEILAO_NAO_ENCONTRADO"

# CA-33
Cenário: Encerrar duas vezes
  Dado o leilão já encerrado
  Quando um ADMIN tenta encerrar novamente
  Então a resposta é 409 "LEILAO_ENCERRADO" e nenhuma nova mensagem é publicada
```

### RF-07 — Saúde do serviço
- **Prioridade:** Must
- **Enunciado (EARS):** Quando `GET /health` for chamado, o serviço deve responder `200 {"status": "UP"}` sem exigir autenticação.
- **Interface:** API-01

```gherkin
# CA-34
Cenário: Health check
  Quando GET /health é chamado sem cabeçalhos
  Então a resposta é 200 com corpo {"status": "UP"}
```

## 9. Regras de negócio

| ID | Regra | Exemplo concreto |
|---|---|---|
| RN-01 | O leilão é identificado por `leilao_id`. Um segundo `leilao_iniciado` **válido** com o mesmo `leilao_id` é ignorado silenciosamente (não altera, não publica, não vai para DLQ). A validação da RN-02 é feita **antes** da verificação de duplicidade: mensagem inválida vai para a DLQ mesmo que o `leilao_id` já exista. | 2º evento LEI-001 com preço 5000.00 → preço continua 1000.00. |
| RN-02 | Mensagem de `leilao_iniciado` é inválida se: faltar `payload` ou qualquer campo do payload; `tipo_leilao` ∉ {REVERSO, DIRETO}; `quantidade` não for inteiro > 0; `preco_inicial` ou `incremento_minimo` não forem valor monetário > 0; `encerra_em` não for instante válido; algum campo string estiver vazio ou contiver apenas espaços. Mensagem inválida não cria leilão e é publicada em `negociacao_dlq`. | tipo_leilao "HOLANDES" → DLQ. |
| RN-03 | Perfil permitido para dar lance: REVERSO → apenas `FORNECEDOR`; DIRETO → apenas `COMPRADOR`. Demais → 403 `PERFIL_NAO_PERMITIDO`. | COMPRADOR em REVERSO → 403. |
| RN-04 | REVERSO: sem lances, o valor deve ser ≤ `preco_inicial`; com lances, deve ser ≤ melhor lance − `incremento_minimo`. Caso contrário → 422 `LANCE_INSUFICIENTE`. | teto 1000.00, inc 10.00, melhor 1000.00 → 990.00 aceito, 995.00 recusado. |
| RN-05 | DIRETO: sem lances, o valor deve ser ≥ `preco_inicial`; com lances, deve ser ≥ melhor lance + `incremento_minimo`. Caso contrário → 422 `LANCE_INSUFICIENTE`. | mínimo 500.00, inc 5.00, melhor 500.00 → 505.00 aceito, 504.99 recusado. |
| RN-06 | A empresa que é líder não pode dar novo lance → 409 `LANCE_JA_LIDER`. | FORN-A líder envia 900.00 → 409. |
| RN-07 | `valor` deve ser **string** que case com `^\d+(\.\d{1,2})?$` e represente número > 0. Número JSON, string fora do padrão, zero, ausência do campo, corpo não-objeto ou JSON malformado → 422 `VALOR_INVALIDO`. | `990` (número) → 422; `"990.5"` → aceito como `"990.50"`. |
| RN-08 | Lances só são aceitos se o leilão estiver aceitando lances (glossário). Caso contrário → 409 `LEILAO_ENCERRADO`. | relógio = encerra_em → 409. |
| RN-09 | Sigilo: nas respostas da API-02 (`melhor_lance.empresa_id`) e da API-03 (`itens[].empresa_id`), se o perfil do solicitante não for `ADMIN` e o lance não for da empresa do solicitante (`X-Empresa-Id`), o `empresa_id` é substituído pela string `"OCULTO"`. Eventos publicados nunca são mascarados. | FORN-A vê lance de FORN-B como "OCULTO". |
| RN-10 | Idempotência: a chave de idempotência é a tripla (`leilao_id`, `X-Empresa-Id`, `Idempotency-Key`). Somente respostas 201 são memorizadas. Repetição de uma tripla memorizada retorna o mesmo status e corpo, sem novo lance e sem novo evento — mesmo que, nesse meio-tempo, o lance tivesse se tornado inválido. Sem o cabeçalho, ou com valor vazio/só espaços, nada é memorizado. | K1 repetido → mesma resposta, total_lances 1. |
| RN-11 | Requisição rejeitada (qualquer 4xx) não altera estado e não publica evento. | — |
| RN-12 | Encerramento: com ≥ 1 lance → status `ENCERRADO`, resultado `VENCEDOR_DEFINIDO`, vencedor = melhor lance. Com 0 lances → status `DESERTO`, resultado `DESERTO`, campos de vencedor `null`. Pode ocorrer antes ou depois de `encerra_em`. Leilão não ABERTO → 409 `LEILAO_ENCERRADO`. | — |

## 10. Catálogo de erros

Formato único de erro (todas as respostas 4xx deste serviço):
```json
{"erro": {"codigo": "LEILAO_NAO_ENCONTRADO", "mensagem": "Leilão não encontrado"}}
```
`mensagem` é texto livre, não vazio, em português.

| Código | HTTP | Quando ocorre |
|---|---|---|
| NAO_AUTENTICADO | 401 | Cabeçalhos de contexto ausentes, vazios ou perfil desconhecido (§7.1). |
| PERFIL_NAO_PERMITIDO | 403 | Perfil sem permissão para a operação (RN-03; API-05 exige ADMIN). |
| LEILAO_NAO_ENCONTRADO | 404 | `leilao_id` não existe. |
| LEILAO_ENCERRADO | 409 | Leilão não está aceitando lances (RN-08) ou encerramento de leilão não ABERTO (RN-12). |
| LANCE_JA_LIDER | 409 | RN-06. |
| VALOR_INVALIDO | 422 | RN-07. |
| LANCE_INSUFICIENTE | 422 | RN-04 / RN-05. |

Respostas fora do catálogo: rota inexistente (404) e método não permitido (405) mantêm a resposta padrão do framework; a documentação automática do framework (`/docs`, `/openapi.json`) pode permanecer habilitada. Nenhuma dessas respostas faz parte da avaliação de conformidade.

**Ordem de verificação** — quando mais de um erro se aplica, retorna-se o primeiro da lista. Por isso a validação do corpo **não** pode ocorrer antes das verificações 1–4 (não use validação automática de corpo do framework que responda antes delas):
1. NAO_AUTENTICADO
2. LEILAO_NAO_ENCONTRADO
3. PERFIL_NAO_PERMITIDO
4. LEILAO_ENCERRADO
5. VALOR_INVALIDO
6. LANCE_JA_LIDER
7. LANCE_INSUFICIENTE

## 11. Requisitos não funcionais

| ID | Característica (ISO/IEC 25010) | Requisito | Métrica e limiar | Verificação |
|---|---|---|---|---|
| RNF-01 | Adequação funcional — exatidão | Aritmética monetária exata com `Decimal`. | Leilão REVERSO preco_inicial "0.30", incremento "0.10": lance "0.30" e depois lance "0.20" de outra empresa devem ser aceitos; `"100"` é devolvido como `"100.00"`. | CA-35 |
| RNF-02 | Interoperabilidade | Formato único de erro. | 100% das respostas 4xx no formato do §10 com `mensagem` string não vazia. | CA-36 |
| RNF-03 | Eficiência de desempenho | Processamento de lances em memória. | 300 lances sequenciais aceitos via API em menos de 3 s (cliente de teste em processo). | CA-37 |
| RNF-04 | Manutenibilidade — modularidade | Estado isolado por instância. | Duas aplicações criadas por `create_app` não compartilham leilões. | CA-38 |
| RNF-05 | Portabilidade | Somente dependências permitidas (§5). | Nenhum `import` fora da biblioteca padrão, `fastapi`, `pydantic`, `starlette` ou do próprio pacote `app`. | CA-39 |
| RNF-06 | Confiabilidade — ordenação | Eventos de um mesmo leilão na mesma partição. | 100% das mensagens `lance_realizado` e `negociacao_fechada` com `key == leilao_id`; envelope com `event_id` UUID único, `tipo` = tópico, `versao` 1, `ocorrido_em` = relógio. | CA-40 |

```gherkin
# CA-35
Cenário: Exatidão decimal
  Dado o leilão REVERSO com preco_inicial "0.30" e incremento_minimo "0.10"
  Quando FORN-A envia "0.30" e FORN-B envia "0.20"
  Então ambas as respostas são 201 e o valor devolvido para FORN-B é "0.20"
  E em um leilão DIRETO com preco_inicial "100.00", o lance "100" é devolvido como "100.00"

# CA-36
Cenário: Formato de erro
  Para cada resposta 4xx produzida pelos cenários de erro
  Então o corpo tem exatamente a chave "erro", com "codigo" e "mensagem" strings não vazias

# CA-37
Cenário: Desempenho
  Dado um leilão REVERSO com preco_inicial "100000.00" e incremento "1.00"
  Quando 300 lances válidos alternados entre FORN-A e FORN-B são enviados em sequência
  Então todos retornam 201 e o tempo total é inferior a 3 segundos

# CA-38
Cenário: Isolamento entre instâncias
  Dado duas aplicações criadas por create_app com barramentos diferentes
  Quando "LEI-001" é aberto apenas na primeira
  Então a segunda retorna 404 para GET /leiloes/LEI-001

# CA-39
Cenário: Dependências
  Ao inspecionar todos os arquivos .py do pacote app
  Então só há imports da biblioteca padrão, fastapi, pydantic, starlette ou do próprio app

# CA-40
Cenário: Envelope e chave de partição
  Quando dois lances são aceitos e o leilão é encerrado
  Então as 3 mensagens publicadas têm key "LEI-001", event_id UUID distintos, tipo igual ao tópico, versao 1 e ocorrido_em igual ao relógio
```

## 12. Matriz de rastreabilidade

| Requisito | Regras | Interfaces | Critérios de aceitação |
|---|---|---|---|
| RF-01 | RN-01, RN-02 | `leilao_iniciado`, `negociacao_dlq` | CA-01 a CA-04 |
| RF-02 | RN-08, RN-09 | API-02 | CA-05 a CA-08 |
| RF-03 | RN-03 a RN-08, RN-11 | API-04, `lance_realizado` | CA-09 a CA-23 |
| RF-04 | RN-10 | API-04 | CA-24, CA-25 |
| RF-05 | RN-09 | API-03 | CA-26, CA-27 |
| RF-06 | RN-12 | API-05, `negociacao_fechada` | CA-28 a CA-33 |
| RF-07 | — | API-01 | CA-34 |
| RNF-01 a RNF-06 | — | todas | CA-35 a CA-40 |

## 13. Premissas, decisões e questões em aberto

| ID | Tipo | Descrição | Decisão |
|---|---|---|---|
| Q-01 | Premissa | O API Gateway já autenticou o usuário. | O serviço confia nos cabeçalhos `X-Empresa-Id`/`X-Perfil`. |
| Q-02 | Decisão | Empate de valores. | Impossível: RN-04/RN-05 exigem diferença ≥ incremento > 0. |
| Q-03 | Decisão | Encerramento automático no prazo. | Fora do escopo; prazo vencido só bloqueia lances (RN-08). |
| Q-04 | Decisão | Concorrência. | Operações sobre um mesmo leilão devem ser serializadas (ex.: `threading.RLock` por instância). |
| Q-05 | Decisão (piloto) | Evento inválido com `leilao_id` já existente: DLQ ou ignorar? | DLQ — validação antes da duplicidade (RN-01). |
| Q-06 | Decisão (piloto) | `Idempotency-Key` vazio. | Equivale a ausente (RN-10). |
| Q-07 | Decisão (piloto) | Reentrância do `publish` e ordem estado/evento. | §5.1: sem deadlock; validar → alterar → publicar. |
| Q-08 | Decisão (piloto) | Rotas inexistentes, 405 e `/docs`. | Padrão do framework (§10). |
| Q-09 | Decisão (piloto) | `event_id` não-string na chave da DLQ; strings só com espaços. | `str(event_id)`; espaços = vazio (RN-02). |

## 14. Checklist de prontidão (Definition of Ready) — preenchido pelo QA

- [x] Nenhum `{{ }}` restante; comentários de orientação removidos.
- [x] Todo RF tem enunciado EARS, prioridade e ≥ 2 CAs (feliz + erro). *(RF-07 é trivial: 1 CA.)*
- [x] Todo CA usa valores concretos e resultado observável.
- [x] Todo código de erro citado em CA existe no §10 e vice-versa.
- [x] Ordem de verificação de erros definida para cada endpoint.
- [x] Todo campo de exemplo JSON existe na tabela da entidade (§6) e vice-versa.
- [x] Todo tópico citado tem produtor/consumidor, chave e exemplo.
- [x] Toda dependência externa está modelada como porta (§5.1).
- [x] Todo RNF tem métrica, limiar e forma de verificação.
- [x] Matriz de rastreabilidade completa.
- [x] Não há palavras vagas sem quantificação.
- [x] Seção 13 sem questões abertas.

## 15. Histórico de versões

| Versão | Data | Autor | Mudança |
|---|---|---|---|
| 1.0 | 2026-10-17 | Grupo de QA | Criação (usada no piloto P1/P2). |
| 1.1 | 2026-10-17 | Grupo de QA | Fase F8 após o piloto: 9 decisões `# DECISÃO:` tomadas pelas LLMs viraram regras explícitas (Q-05 a Q-09; RN-01, RN-02, RN-10, §5.1, §7.4, §10). Nenhum CA alterado. |
