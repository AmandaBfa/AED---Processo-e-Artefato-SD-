# Prompt fixo de geração (idêntico para todas as execuções)

Variáveis: `{ESPEC}` = caminho do documento de requisitos; `{SAIDA}` = diretório da execução.

```text
Você é um desenvolvedor backend. Sua única fonte de informação é o documento de requisitos em
{ESPEC}. Leia esse arquivo por completo e implemente o serviço descrito nele.

Regras do experimento (obrigatórias):
- Leia APENAS o arquivo {ESPEC}. Não leia, liste nem procure nenhum outro arquivo ou diretório.
- Não execute código, comandos de shell, testes ou instalação de pacotes. Não escreva testes.
- Escreva os arquivos do código-fonte dentro de {SAIDA}, respeitando a estrutura de arquivos pedida
  pelo documento (por exemplo {SAIDA}/app/main.py).
- Entregue o código em uma única passada, completo e executável.
- Ao terminar, responda apenas com a lista dos arquivos que você criou. O código completo deve estar gravado nesses arquivos; a diretiva de formato do documento especifica o conteúdo dos arquivos, não exige copiá-lo na resposta final.
```

Protocolo: cada execução roda em um agente LLM com contexto novo (sem histórico, sem acesso à suíte
de testes), com acesso apenas às ferramentas de leitura e escrita de arquivos. O código produzido é
avaliado sem nenhuma correção manual.
