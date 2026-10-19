"""Reanálise descritiva dos CSVs históricos, sem sobrescrever resultados originais.

As probabilidades abaixo são condicionais aos números nos CSVs. A execução
original do software gerado não pode ser verificada sem seus artefatos.
"""
import csv
from itertools import combinations
from math import comb
from pathlib import Path
from statistics import mean, median

RES = Path(__file__).resolve().parent / "resultados"


def ler(nome):
    with (RES / nome).open(encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    if len(linhas) != 6:
        raise ValueError(f"Esperadas seis execuções em {nome}; encontradas {len(linhas)}")
    for linha in linhas:
        aprovados = int(linha["ca_atendidos"])
        falhos = [x for x in linha["ca_falhos"].split(";") if x]
        if aprovados + len(falhos) != 40 or abs(float(linha["C_ca"]) - aprovados / 40) > 1e-9:
            raise ValueError(f"Linha inconsistente em {nome}: {linha['impl']}")
    return [float(linha["C_ca"]) for linha in linhas]


def permutacao_unilateral(tratamento, controle):
    """Permuta rótulos entre as 12 execuções; válido sob permutabilidade."""
    todos = tratamento + controle
    observado = mean(tratamento) - mean(controle)
    extremos = 0
    for indices in combinations(range(len(todos)), len(tratamento)):
        indice = set(indices)
        diferenca = mean(todos[i] for i in indice) - mean(
            todos[i] for i in range(len(todos)) if i not in indice
        )
        extremos += diferenca >= observado - 1e-12
    return extremos, comb(len(todos), len(tratamento))


def main():
    t = ler("conformidade_tratamento.csv")
    c = ler("conformidade_controle.csv")
    extremos, total = permutacao_unilateral(t, c)
    print(f"Tratamento: n=6, média={mean(t):.4f}, mediana={median(t):.4f}; valores={t}")
    print(f"Controle: n=6, média={mean(c):.4f}, mediana={median(c):.4f}; valores={c}")
    print(f"Diferença descritiva de médias: {mean(t) - mean(c):.4f}")
    print(f"Execuções do tratamento >= 0,85: {sum(x >= 0.85 for x in t)}/6")
    print(f"Permutação unilateral não bloqueada T > C: {extremos}/{total} = {extremos/total:.6f}")
    print("Limite: a permutação supõe execuções permutáveis; o desenho usou três modelos como blocos.")
    print("Limite: os CSVs não substituem código gerado, logs e resultados individuais de teste.")


if __name__ == "__main__":
    main()
