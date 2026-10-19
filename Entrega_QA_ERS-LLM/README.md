# Entrega — Processo de Análise de Requisitos para Geração de Código por LLM

**Disciplina:** Sistemas Distribuídos · **Sistema:** Portal B2B Distribuído · **Grupo:** Testes / QA

**Integrantes:** Amanda Barbosa; Kayky Momoli; Lavínia Maria Moreira; Gabriel Jonas Lucio; Matheus Silva Pains; Igor Santos; Nicole Gomes C Yssob; Igor Nascimento Balduíno; Antonio Calixto.

| Entregável | Arquivo |
|---|---|
| 1. Processo | `01_Processo_Analise_Requisitos.md` |
| 2. Artefato (modelo do documento de requisitos) | `02_Template_Documento_Requisitos.md` |
| 3. Instruções de preenchimento | `03_Instrucoes_Preenchimento.md` |
| 4. Relatório técnico do experimento | `04_Relatorio_Tecnico_Experimento.md` |

Anexos em `experimento/`: documento preenchido (`especificacao/ESP-NEG-001_Negociacao_Leilao.md`), documento de controle, prompt de geração, suíte de testes de aceitação, avaliador, análise estatística e resultados.

## Estado após auditoria de QA (18/10/2026)

O relatório e os CSVs registram resultados históricos declarados pelo grupo. O pacote **não inclui** as implementações geradas, a referência, os mutantes, o documento piloto v1.0 e os logs/XMLs individuais; por isso um terceiro não consegue confirmar ou reproduzir os 40/40 relatados somente com estes arquivos. Veja o adendo da seção 11 do relatório.

A especificação v1.1, o prompt histórico, a suíte e os CSVs foram mantidos para rastreabilidade. `experimento/especificacao/ESP-NEG-001_v1.2_rascunho.md` e `experimento/prompt_geracao_v1.2_proposta.md` são propostas para **nova rodada**, ainda não aprovadas para geração. Processo, template e guia foram revisados como proposta v1.2. Os resultados antigos não se aplicam automaticamente a essa versão.

O `experimento/avaliar.py` atual verifica a quantidade de casos esperados por CA, detecta falha do instrumento e aceita `--evidencias <diretório>` para guardar XML e saídas do pytest. Foi alterado depois do experimento; seu hash não corresponde ao manifesto histórico. `experimento/analise_estatistica_revisada.py` reanalisa os CSVs sem sobrescrever o resultado original. A execução dos scripts depende de um ambiente Python e das implementações, ausentes neste workspace.
