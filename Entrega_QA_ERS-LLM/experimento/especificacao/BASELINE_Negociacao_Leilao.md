# Documento de Requisitos — Serviço de Negociação / Leilão

> Documento de controle (grupo C do experimento). Representa uma especificação "tradicional",
> escrita sem o processo proposto: histórias de usuário e descrição em prosa. Contém a **mesma
> intenção de negócio** da ESP-NEG-001 e o contrato mínimo de integração necessário para que o
> código possa ser executado pelo harness de testes, mas não contém catálogo de erros, ordem de
> verificação, critérios de aceitação em Gherkin, exemplos JSON completos nem diretivas para a LLM.

## 1. Visão geral

O serviço de Negociação/Leilão faz parte do Portal B2B distribuído (microsserviços + Kafka). Quando o
serviço de Mercado decide que uma demanda será negociada por leilão, ele publica o evento
`leilao_iniciado`. Este serviço abre o leilão, recebe os lances das empresas e, quando o leilão é
encerrado, define o vencedor e publica `negociacao_fechada` para o serviço de Pedidos. A cada lance
aceito é publicado `lance_realizado`.

Existem dois tipos de leilão:
- **Reverso**: fornecedores disputam para vender; ganha o menor preço.
- **Direto**: compradores disputam para comprar; ganha o maior preço.

## 2. Tecnologia e integração

- Python 3.12 com FastAPI. Usar somente a biblioteca padrão, fastapi, pydantic e starlette.
- Dados em memória (sem banco), separados por instância da aplicação.
- Arquivos obrigatórios: `app/__init__.py` e `app/main.py`.
- A aplicação deve ser criada pela função `app.main.create_app(event_bus, clock)`, que retorna um `FastAPI`.
- `event_bus` tem os métodos `publish(topic: str, key: str, message: dict)` e
  `subscribe(topic: str, handler)`; o handler recebe a mensagem como `dict`. O serviço deve se inscrever
  no tópico `leilao_iniciado` ao ser criado.
- `clock` tem o método `now()` que retorna um `datetime` UTC; usar sempre ele para obter a hora atual.
- O API Gateway autentica o usuário e repassa os cabeçalhos `X-Empresa-Id` e `X-Perfil`
  (COMPRADOR, FORNECEDOR, TRANSPORTADORA ou ADMIN).

Rotas:
- `GET /health`
- `GET /leiloes/{leilao_id}`
- `GET /leiloes/{leilao_id}/lances`
- `POST /leiloes/{leilao_id}/lances` (corpo com o campo `valor`)
- `POST /leiloes/{leilao_id}/encerrar`

Tópicos: consome `leilao_iniciado`; publica `lance_realizado`, `negociacao_fechada` e, para mensagens
inválidas, `negociacao_dlq`.

A mensagem de `leilao_iniciado` contém `event_id`, `tipo`, `versao`, `ocorrido_em` e um `payload` com
`leilao_id`, `demanda_id`, `produto_id`, `quantidade`, `tipo_leilao` (REVERSO ou DIRETO),
`preco_inicial`, `incremento_minimo` e `encerra_em`. As mensagens publicadas devem seguir o mesmo
formato de envelope.

## 3. Histórias de usuário

**HU1 — Abrir leilão.** Como serviço de Mercado, quero que o leilão seja aberto quando eu publicar
`leilao_iniciado`, para que as empresas possam dar lances. Eventos repetidos não devem duplicar o
leilão. Eventos com dados inválidos devem ser enviados para a fila de mensagens inválidas.

**HU2 — Consultar leilão.** Como usuário do portal, quero ver os dados do leilão, seu status, se ainda
aceita lances, qual o melhor lance e quantos lances existem.

**HU3 — Dar lance.** Como fornecedor (leilão reverso) ou comprador (leilão direto), quero dar lances.
- No reverso o primeiro lance não pode passar do preço inicial e cada lance seguinte deve ser menor que
  o melhor lance em pelo menos o incremento mínimo. No direto é o contrário: o primeiro lance deve ser
  pelo menos o preço inicial e cada lance seguinte deve superar o melhor em pelo menos o incremento.
- Quem já está ganhando não pode dar outro lance em seguida.
- Não é possível dar lances depois do prazo ou em leilão encerrado.
- O valor do lance deve ser positivo e ter no máximo duas casas decimais.
- Outros perfis não podem dar lances.
- Para evitar duplicidade por reenvio de rede, o cliente pode mandar o cabeçalho `Idempotency-Key`.

**HU4 — Ver lances.** Como usuário, quero ver a lista de lances em ordem. Por sigilo, empresas
concorrentes não devem ver quem deu os lances dos outros; o administrador vê tudo.

**HU5 — Encerrar leilão.** Como administrador, quero encerrar o leilão e ver o vencedor. Se ninguém
deu lance, o leilão fica deserto.

**HU6 — Monitorar.** Como operação, quero um endpoint de saúde.

## 4. Requisitos não funcionais

- Valores monetários devem ser tratados com precisão.
- Os erros devem ser retornados com códigos HTTP adequados e mensagem clara.
- O serviço deve ser rápido.
- Os eventos de um mesmo leilão devem manter a ordem no Kafka.
