"""Avalia a conformidade de uma ou mais implementações contra a suíte de aceitação.

Uso:  python3 avaliar.py <dir_impl> [<dir_impl> ...] [--csv saida.csv]
                         [--evidencias diretorio]

Para cada implementação, executa pytest em subprocesso isolado (IMPL_DIR=<dir>),
agrega os resultados por critério de aceitação (CA) e calcula:
  C_ca  = CAs atendidos / 40                       (métrica primária)
  C_rf  = requisitos com todos os CAs atendidos / 13 (métrica estrita, secundária)
"""
import csv
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

AQUI = os.path.dirname(os.path.abspath(__file__))
TESTES = os.path.join(AQUI, "testes")
TOTAL_CA = 40
# CA-18 é parametrizado em oito casos; os demais têm um caso cada.
CASOS_ESPERADOS = {n: (8 if n == 18 else 1) for n in range(1, TOTAL_CA + 1)}
REQ_CA = {
    "RF-01": range(1, 5), "RF-02": range(5, 9), "RF-03": range(9, 24),
    "RF-04": range(24, 26), "RF-05": range(26, 28), "RF-06": range(28, 34),
    "RF-07": [34], "RNF-01": [35], "RNF-02": [36], "RNF-03": [37],
    "RNF-04": [38], "RNF-05": [39], "RNF-06": [40],
}


def avaliar(impl, evidencias=None):
    impl = os.path.abspath(impl)
    if not os.path.isfile(os.path.join(impl, "app", "main.py")):
        raise FileNotFoundError(f"Implementação sem app/main.py: {impl}")
    with tempfile.TemporaryDirectory() as temporario:
        tmp = evidencias or temporario
        os.makedirs(tmp, exist_ok=True)
        xml = os.path.join(tmp, "r.xml")
        env = dict(os.environ, IMPL_DIR=impl, PYTHONDONTWRITEBYTECODE="1")
        processo = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                        f"--junitxml={xml}", "--timeout=60"] if _tem_timeout() else
                       [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                        f"--junitxml={xml}"],
                       cwd=TESTES, env=env, capture_output=True, text=True)
        if evidencias:
            Path(tmp, "pytest.stdout.txt").write_text(processo.stdout, encoding="utf-8")
            Path(tmp, "pytest.stderr.txt").write_text(processo.stderr, encoding="utf-8")
        if not os.path.isfile(xml):
            raise RuntimeError(f"pytest não produziu XML (saída {processo.returncode}): {processo.stderr[-500:]}")
        ca_ok = {n: True for n in range(1, TOTAL_CA + 1)}
        ca_visto = {n: 0 for n in ca_ok}
        falhas = {}
        for tc in ET.parse(xml).getroot().iter("testcase"):
            m = re.match(r"test_CA(\d+)", tc.get("name", ""))
            if not m:
                if tc.find("failure") is not None or tc.find("error") is not None:
                    raise RuntimeError(f"Falha fora dos CAs mapeados: {tc.get('name', '')}")
                continue
            n = int(m.group(1))
            if n not in ca_ok:
                raise RuntimeError(f"Teste com CA inesperado: CA{n:02d}")
            ca_visto[n] += 1
            erro = tc.find("failure")
            if erro is None:
                erro = tc.find("error")
            if erro is None:
                erro = tc.find("skipped")
            if erro is not None:
                ca_ok[n] = False
                msg = (erro.get("message") or "").splitlines()
                falhas.setdefault(n, (msg[0] if msg else "")[:160])
        for n in ca_ok:  # coleta parcial nunca aprova um CA
            if ca_visto[n] != CASOS_ESPERADOS[n]:
                ca_ok[n] = False
                falhas.setdefault(n, f"casos registrados: {ca_visto[n]}/{CASOS_ESPERADOS[n]}")
        if processo.returncode not in (0, 1):
            raise RuntimeError(f"pytest falhou na avaliação (saída {processo.returncode}): {processo.stderr[-500:]}")
    atendidos = sum(ca_ok.values())
    req_ok = {r: all(ca_ok[c] for c in cas) for r, cas in REQ_CA.items()}
    return {
        "impl": os.path.basename(impl.rstrip("/")),
        "ca_atendidos": atendidos,
        "C_ca": atendidos / TOTAL_CA,
        "req_atendidos": sum(req_ok.values()),
        "C_rf": sum(req_ok.values()) / len(REQ_CA),
        "ca_falhos": ";".join(f"CA{n:02d}" for n, ok in ca_ok.items() if not ok),
        "detalhe": falhas,
        "status": "avaliado",
    }


def _tem_timeout():
    try:
        import pytest_timeout  # noqa: F401
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    args = sys.argv[1:]
    saida = None
    evidencias = None
    if "--csv" in args:
        i = args.index("--csv")
        saida = args[i + 1]
        args = args[:i] + args[i + 2:]
    if "--evidencias" in args:
        i = args.index("--evidencias")
        evidencias = args[i + 1]
        args = args[:i] + args[i + 2:]
    if not args:
        raise SystemExit("Informe ao menos um diretório de implementação")
    linhas = []
    for d in args:
        pasta = os.path.join(evidencias, os.path.basename(os.path.normpath(d))) if evidencias else None
        r = avaliar(d, pasta)
        linhas.append(r)
        print(f"{r['impl']:<14} C_ca={r['C_ca']:.3f} ({r['ca_atendidos']}/40)  "
              f"C_rf={r['C_rf']:.3f} ({r['req_atendidos']}/13)  falhos: {r['ca_falhos'] or '-'}")
        for n, msg in sorted(r["detalhe"].items()):
            print(f"      CA{n:02d}: {msg}")
    if saida:
        with open(saida, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["impl", "ca_atendidos", "C_ca", "req_atendidos",
                                              "C_rf", "ca_falhos"])
            w.writeheader()
            for r in linhas:
                w.writerow({k: r[k] for k in w.fieldnames})
