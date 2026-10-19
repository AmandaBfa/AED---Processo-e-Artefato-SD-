"""Análise estatística do experimento (teste de hipótese).

Entrada: resultados/conformidade_tratamento.csv e resultados/conformidade_controle.csv
         (gerados por avaliar.py; coluna C_ca = conformidade por critério de aceitação).
Saída:   resultados/analise_estatistica.txt

H1 (principal)    H0: μ_T ≤ 0,85   vs  H1: μ_T > 0,85     (amostra única, unilateral)
H2 (comparativa)  H0: μ_T ≤ μ_C    vs  H1: μ_T > μ_C      (duas amostras independentes, unilateral)
α = 0,05
"""
import csv
import os
import statistics as st
import sys

from scipy import stats

AQUI = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(AQUI, "resultados")
ALFA, P0, TOTAL_CA = 0.05, 0.85, 40


def ler(nome, col="C_ca"):
    with open(os.path.join(RES, nome), encoding="utf-8") as f:
        return [(r["impl"], float(r[col]), int(r["ca_atendidos"])) for r in csv.DictReader(f)]


def cliffs_delta(a, b):
    gt = sum(1 for x in a for y in b if x > y)
    lt = sum(1 for x in a for y in b if x < y)
    return (gt - lt) / (len(a) * len(b))


def descr(nome, xs):
    return (f"{nome}: n={len(xs)}  média={st.mean(xs):.4f}  mediana={st.median(xs):.4f}  "
            f"dp={st.stdev(xs):.4f}  mín={min(xs):.4f}  máx={max(xs):.4f}")


def main():
    out = []
    p = out.append
    T = ler("conformidade_tratamento.csv")
    C = ler("conformidade_controle.csv")
    t = [x[1] for x in T]
    c = [x[1] for x in C]

    p("=== Estatística descritiva (C_ca) ===")
    p(descr("Tratamento (ESP-NEG-001 v1.1)", t))
    p(descr("Controle   (documento tradicional)", c))
    p("")

    p("=== H1: μ_T > 0,85 (unilateral, α = 0,05) ===")
    if st.stdev(t) == 0:
        p("Variância nula: teste t indefinido; usar Wilcoxon e binomial.")
    else:
        tt = stats.ttest_1samp(t, P0, alternative="greater")
        n = len(t)
        se = st.stdev(t) / n ** 0.5
        lim = st.mean(t) - stats.t.ppf(1 - ALFA, n - 1) * se
        p(f"t de Student (1 amostra): t={tt.statistic:.4f}  gl={n-1}  p={tt.pvalue:.6f}")
        p(f"Limite inferior unilateral de 95% para μ_T: {lim:.4f}")
    w = stats.wilcoxon([x - P0 for x in t], alternative="greater", method="exact")
    p(f"Wilcoxon postos sinalizados (exato) vs 0,85: W={w.statistic}  p={w.pvalue:.6f}")
    sucessos = sum(x[2] for x in T)
    tentativas = TOTAL_CA * len(T)
    b = stats.binomtest(sucessos, tentativas, P0, alternative="greater")
    ci = b.proportion_ci(confidence_level=0.95, method="exact")
    p(f"Binomial exato (CAs agregados): {sucessos}/{tentativas} = {sucessos/tentativas:.4f}  "
      f"p={b.pvalue:.6g}  limite inferior do IC95% unilateral (Clopper-Pearson) = {ci.low:.4f}")
    p("(o binomial agregado supõe independência entre CAs; é apresentado como análise de apoio)")
    abaixo = sum(1 for x in t if x < P0)
    p(f"Execuções do tratamento abaixo de 0,85: {abaixo} de {len(t)}")
    p("")

    p("=== H2: μ_T > μ_C (unilateral, α = 0,05) ===")
    mw = stats.mannwhitneyu(t, c, alternative="greater", method="exact")
    p(f"Mann-Whitney U (exato): U={mw.statistic}  p={mw.pvalue:.6f}")
    if st.stdev(t) > 0 or st.stdev(c) > 0:
        wt = stats.ttest_ind(t, c, equal_var=False, alternative="greater")
        p(f"t de Welch: t={wt.statistic:.4f}  p={wt.pvalue:.6g}")
    d = cliffs_delta(t, c)
    mag = "grande" if abs(d) >= 0.474 else "médio" if abs(d) >= 0.33 else "pequeno" if abs(d) >= 0.147 else "desprezível"
    p(f"Tamanho de efeito δ de Cliff = {d:.3f} ({mag})")
    p(f"Diferença de médias = {st.mean(t) - st.mean(c):.4f}")
    p("")

    p("=== Por modelo gerador (tratamento | controle) ===")
    for mod in ("haiku", "sonnet", "opus"):
        tv = [x[1] for x in T if mod in x[0]]
        cv = [x[1] for x in C if mod in x[0]]
        if tv:
            p(f"{mod:<7} T={', '.join(f'{v:.3f}' for v in tv)}   C={', '.join(f'{v:.3f}' for v in cv)}")

    texto = "\n".join(out)
    print(texto)
    with open(os.path.join(RES, "analise_estatistica.txt"), "w", encoding="utf-8") as f:
        f.write(texto + "\n")


if __name__ == "__main__":
    sys.exit(main())
