"""Testes de aceitação derivados dos critérios CA-01..CA-40 da ESP-NEG-001.

Convenção: cada função é nomeada test_CA<NN>_...; um CA é considerado ATENDIDO
somente se todos os casos de teste com o seu prefixo passarem.
Suíte congelada antes da geração de código (ver SHA-256 no relatório).
"""
import ast
import os
import sys
import time
import uuid
from datetime import timedelta

import pytest

from conftest import (ADMIN, COMP_A, COMP_B, ENCERRA, ENCERRA_STR, FORN_A, FORN_B,
                      T0_STR, TRANSP, FakeBus, FakeClock, H, _REMOVE, codigo,
                      evento_leilao)

LANCES = "/leiloes/{}/lances"


def lance(client, headers, valor, leilao="LEI-001", **extra_headers):
    h = dict(headers)
    h.update(extra_headers)
    return client.post(LANCES.format(leilao), json={"valor": valor}, headers=h)


def eh_uuid4(s):
    try:
        return uuid.UUID(str(s)).version == 4
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------- RF-01
def test_CA01_evento_valido_abre_leilao(client, abrir):
    abrir()
    r = client.get("/leiloes/LEI-001", headers=FORN_A)
    assert r.status_code == 200
    b = r.json()
    assert b["status"] == "ABERTO"
    assert b["tipo"] == "REVERSO"
    assert b["preco_inicial"] == "1000.00"
    assert b["incremento_minimo"] == "10.00"
    assert b["quantidade"] == 500
    assert b["total_lances"] == 0


def test_CA02_evento_duplicado_ignorado(client, abrir, bus):
    abrir()
    abrir(preco_inicial="5000.00")
    r = client.get("/leiloes/LEI-001", headers=FORN_A)
    assert r.json()["preco_inicial"] == "1000.00"
    assert bus.published == []


def test_CA03_tipo_invalido_vai_para_dlq(client, bus):
    msg = evento_leilao("LEI-X", event_id="E-9", tipo_leilao="HOLANDES")
    bus.deliver("leilao_iniciado", msg)
    assert client.get("/leiloes/LEI-X", headers=FORN_A).status_code == 404
    dlq = bus.on("negociacao_dlq")
    assert len(dlq) == 1
    key, m = dlq[0]
    assert key == "E-9"
    p = m["payload"]
    assert p["topico_origem"] == "leilao_iniciado"
    assert isinstance(p["motivo"], str) and p["motivo"].strip()
    assert p["mensagem_original"] == msg


def test_CA04_campo_ausente_dlq_sem_excecao(client, bus):
    msg = evento_leilao("LEI-Y", encerra_em=_REMOVE)
    bus.deliver("leilao_iniciado", msg)  # não pode lançar exceção
    assert len(bus.on("negociacao_dlq")) == 1
    assert client.get("/leiloes/LEI-Y", headers=FORN_A).status_code == 404


# --------------------------------------------------------------------------- RF-02
def test_CA05_consulta_sem_lances(client, abrir):
    abrir()
    r = client.get("/leiloes/LEI-001", headers=FORN_A)
    assert r.status_code == 200
    b = r.json()
    esperado = {
        "leilao_id": "LEI-001", "demanda_id": "DEM-10", "produto_id": "PROD-7",
        "quantidade": 500, "tipo": "REVERSO", "preco_inicial": "1000.00",
        "incremento_minimo": "10.00", "encerra_em": ENCERRA_STR, "status": "ABERTO",
        "aceitando_lances": True, "melhor_lance": None, "total_lances": 0,
    }
    for k, v in esperado.items():
        assert k in b, k
        assert b[k] == v, k


def test_CA06_leilao_inexistente(client):
    r = client.get("/leiloes/NAO-EXISTE", headers=FORN_A)
    assert r.status_code == 404
    assert codigo(r) == "LEILAO_NAO_ENCONTRADO"


def test_CA07_sem_autenticacao(client, abrir):
    abrir()
    r = client.get("/leiloes/LEI-001")
    assert r.status_code == 401
    assert codigo(r) == "NAO_AUTENTICADO"


def test_CA08_prazo_vencido_nao_muda_status(client, abrir, clock):
    abrir()
    clock.set(ENCERRA)
    b = client.get("/leiloes/LEI-001", headers=FORN_A).json()
    assert b["status"] == "ABERTO"
    assert b["aceitando_lances"] is False


# --------------------------------------------------------------------------- RF-03
def test_CA09_primeiro_lance_valido(client, abrir):
    abrir()
    r = lance(client, FORN_A, "1000.00")
    assert r.status_code == 201
    b = r.json()
    assert eh_uuid4(b["lance_id"])
    assert b["leilao_id"] == "LEI-001"
    assert b["empresa_id"] == "FORN-A"
    assert b["valor"] == "1000.00"
    assert b["sequencia"] == 1
    assert b["criado_em"] == T0_STR


def test_CA10_lance_publica_evento(client, abrir, bus):
    abrir()
    r = lance(client, FORN_A, "990.00")
    assert r.status_code == 201
    msgs = bus.on("lance_realizado")
    assert len(msgs) == 1
    key, m = msgs[0]
    assert key == "LEI-001"
    for campo in ("event_id", "tipo", "versao", "ocorrido_em", "payload"):
        assert campo in m
    assert m["tipo"] == "lance_realizado"
    p = m["payload"]
    assert p["leilao_id"] == "LEI-001"
    assert p["lance_id"] == r.json()["lance_id"]
    assert p["empresa_id"] == "FORN-A"
    assert p["valor"] == "990.00"
    assert p["sequencia"] == 1


def test_CA11_primeiro_lance_acima_do_teto(client, abrir):
    abrir()
    r = lance(client, FORN_A, "1000.01")
    assert r.status_code == 422
    assert codigo(r) == "LANCE_INSUFICIENTE"


def test_CA12_decremento_minimo_reverso(client, abrir):
    abrir()
    assert lance(client, FORN_A, "1000.00").status_code == 201
    r = lance(client, FORN_B, "995.00")
    assert r.status_code == 422
    assert codigo(r) == "LANCE_INSUFICIENTE"
    assert lance(client, FORN_B, "990.00").status_code == 201


def test_CA13_regras_leilao_direto(client, abrir):
    abrir("LEI-D", tipo_leilao="DIRETO", preco_inicial="500.00", incremento_minimo="5.00")
    r = lance(client, COMP_A, "499.99", "LEI-D")
    assert r.status_code == 422 and codigo(r) == "LANCE_INSUFICIENTE"
    assert lance(client, COMP_A, "500.00", "LEI-D").status_code == 201
    r = lance(client, COMP_B, "504.99", "LEI-D")
    assert r.status_code == 422 and codigo(r) == "LANCE_INSUFICIENTE"
    assert lance(client, COMP_B, "505.00", "LEI-D").status_code == 201


def test_CA14_perfil_nao_permitido(client, abrir):
    abrir("LEI-R")
    abrir("LEI-D", tipo_leilao="DIRETO", preco_inicial="500.00", incremento_minimo="5.00")
    casos = [
        (COMP_A, "900.00", "LEI-R"),
        (FORN_A, "600.00", "LEI-D"),
        (ADMIN, "900.00", "LEI-R"), (ADMIN, "600.00", "LEI-D"),
        (TRANSP, "900.00", "LEI-R"), (TRANSP, "600.00", "LEI-D"),
    ]
    for h, v, lid in casos:
        r = lance(client, h, v, lid)
        assert r.status_code == 403, (h, lid)
        assert codigo(r) == "PERFIL_NAO_PERMITIDO"


def test_CA15_lider_nao_cobre_proprio_lance(client, abrir):
    abrir()
    assert lance(client, FORN_A, "1000.00").status_code == 201
    r = lance(client, FORN_A, "900.00")
    assert r.status_code == 409
    assert codigo(r) == "LANCE_JA_LIDER"


def test_CA16_lance_apos_prazo(client, abrir, clock):
    abrir()
    clock.set(ENCERRA)
    r = lance(client, FORN_A, "900.00")
    assert r.status_code == 409
    assert codigo(r) == "LEILAO_ENCERRADO"


def test_CA17_lance_em_leilao_encerrado_ou_deserto(client, abrir):
    abrir("LEI-E")
    abrir("LEI-S")
    assert lance(client, FORN_A, "1000.00", "LEI-E").status_code == 201
    assert client.post("/leiloes/LEI-E/encerrar", headers=ADMIN).status_code == 200
    assert client.post("/leiloes/LEI-S/encerrar", headers=ADMIN).status_code == 200
    for lid in ("LEI-E", "LEI-S"):
        r = lance(client, FORN_B, "900.00", lid)
        assert r.status_code == 409, lid
        assert codigo(r) == "LEILAO_ENCERRADO"


@pytest.mark.parametrize("corpo", [
    {"valor": 990}, {"valor": "abc"}, {"valor": "-5.00"}, {"valor": "0"},
    {"valor": "0.00"}, {"valor": "10.123"}, {}, "MALFORMADO",
], ids=["numero", "abc", "negativo", "zero", "zero_2c", "3casas", "vazio", "json_malformado"])
def test_CA18_valor_invalido(client, abrir, corpo):
    abrir()
    if corpo == "MALFORMADO":
        h = dict(FORN_A)
        h["Content-Type"] = "application/json"
        r = client.post(LANCES.format("LEI-001"), content=b'{"valor": ', headers=h)
    else:
        r = client.post(LANCES.format("LEI-001"), json=corpo, headers=FORN_A)
    assert r.status_code == 422
    assert codigo(r) == "VALOR_INVALIDO"


def test_CA19_lance_leilao_inexistente(client):
    r = lance(client, FORN_A, "900.00", "NAO-EXISTE")
    assert r.status_code == 404
    assert codigo(r) == "LEILAO_NAO_ENCONTRADO"


def test_CA20_autenticacao_ausente_ou_invalida(client, abrir):
    abrir()
    for h in ({"X-Perfil": "FORNECEDOR"}, {"X-Empresa-Id": "FORN-A"},
              {"X-Empresa-Id": "FORN-A", "X-Perfil": "HACKER"}):
        r = client.post(LANCES.format("LEI-001"), json={"valor": "900.00"}, headers=h)
        assert r.status_code == 401, h
        assert codigo(r) == "NAO_AUTENTICADO"


def test_CA21_precedencia_de_erros(client, abrir, clock):
    abrir("LEI-001")
    abrir("LEI-T")
    r = lance(client, FORN_A, "abc", "NAO-EXISTE")
    assert r.status_code == 404 and codigo(r) == "LEILAO_NAO_ENCONTRADO"
    r = lance(client, COMP_A, "abc", "LEI-001")
    assert r.status_code == 403 and codigo(r) == "PERFIL_NAO_PERMITIDO"
    assert lance(client, FORN_A, "1000.00", "LEI-001").status_code == 201
    r = lance(client, FORN_A, "1000.00", "LEI-001")  # líder e insuficiente
    assert r.status_code == 409 and codigo(r) == "LANCE_JA_LIDER"
    clock.set(ENCERRA + timedelta(seconds=1))
    r = lance(client, FORN_B, "abc", "LEI-T")
    assert r.status_code == 409 and codigo(r) == "LEILAO_ENCERRADO"


def test_CA22_erro_nao_altera_estado_nem_publica(client, abrir, bus):
    abrir()
    assert lance(client, FORN_A, "1000.00").status_code == 201
    n = len(bus.published)
    rejeitados = [
        lance(client, FORN_B, "995.00"),       # insuficiente
        lance(client, FORN_A, "900.00"),       # líder
        lance(client, COMP_A, "900.00"),       # perfil
        lance(client, FORN_B, "x"),            # inválido
    ]
    assert all(400 <= r.status_code < 500 for r in rejeitados)
    assert client.get("/leiloes/LEI-001", headers=ADMIN).json()["total_lances"] == 1
    assert len(bus.published) == n


def test_CA23_consulta_reflete_melhor_lance(client, abrir):
    abrir()
    lance(client, FORN_A, "1000.00")
    r2 = lance(client, FORN_B, "990.00")
    b = client.get("/leiloes/LEI-001", headers=ADMIN).json()
    assert b["total_lances"] == 2
    ml = b["melhor_lance"]
    assert ml["empresa_id"] == "FORN-B"
    assert ml["valor"] == "990.00"
    assert ml["sequencia"] == 2
    assert ml["lance_id"] == r2.json()["lance_id"]


# --------------------------------------------------------------------------- RF-04
def test_CA24_reenvio_mesma_chave(client, abrir, bus):
    abrir()
    r1 = lance(client, FORN_A, "990.00", **{"Idempotency-Key": "K1"})
    r2 = lance(client, FORN_A, "990.00", **{"Idempotency-Key": "K1"})
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json() == r2.json()
    assert client.get("/leiloes/LEI-001", headers=ADMIN).json()["total_lances"] == 1
    assert len(bus.on("lance_realizado")) == 1


def test_CA25_chave_igual_empresa_diferente(client, abrir):
    abrir()
    r1 = lance(client, FORN_A, "990.00", **{"Idempotency-Key": "K1"})
    r2 = lance(client, FORN_B, "980.00", **{"Idempotency-Key": "K1"})
    assert r2.status_code == 201
    assert r2.json()["lance_id"] != r1.json()["lance_id"]
    assert r2.json()["sequencia"] == 2


# --------------------------------------------------------------------------- RF-05
def test_CA26_listagem_ordenada(client, abrir):
    abrir()
    a = lance(client, FORN_A, "1000.00").json()
    b = lance(client, FORN_B, "990.00").json()
    r = client.get(LANCES.format("LEI-001"), headers=ADMIN)
    assert r.status_code == 200
    itens = r.json()["itens"]
    assert [i["sequencia"] for i in itens] == [1, 2]
    for item, esperado, emp, val in ((itens[0], a, "FORN-A", "1000.00"),
                                     (itens[1], b, "FORN-B", "990.00")):
        assert item["lance_id"] == esperado["lance_id"]
        assert item["leilao_id"] == "LEI-001"
        assert item["empresa_id"] == emp
        assert item["valor"] == val
        assert item["criado_em"] == T0_STR


def test_CA27_sigilo_entre_concorrentes(client, abrir):
    abrir()
    lance(client, FORN_A, "1000.00")
    lance(client, FORN_B, "990.00")
    itens = client.get(LANCES.format("LEI-001"), headers=FORN_A).json()["itens"]
    assert itens[0]["empresa_id"] == "FORN-A"
    assert itens[1]["empresa_id"] == "OCULTO"
    assert client.get("/leiloes/LEI-001", headers=FORN_A).json()["melhor_lance"]["empresa_id"] == "OCULTO"
    assert client.get("/leiloes/LEI-001", headers=FORN_B).json()["melhor_lance"]["empresa_id"] == "FORN-B"


# --------------------------------------------------------------------------- RF-06
def test_CA28_encerramento_reverso(client, abrir):
    abrir()
    lance(client, FORN_A, "1000.00")
    vb = lance(client, FORN_B, "990.00").json()
    r = client.post("/leiloes/LEI-001/encerrar", headers=ADMIN)
    assert r.status_code == 200
    b = r.json()
    assert b["leilao_id"] == "LEI-001"
    assert b["status"] == "ENCERRADO"
    assert b["resultado"] == "VENCEDOR_DEFINIDO"
    assert b["vencedor_empresa_id"] == "FORN-B"
    assert b["valor_vencedor"] == "990.00"
    assert b["lance_vencedor_id"] == vb["lance_id"]
    assert b["total_lances"] == 2
    g = client.get("/leiloes/LEI-001", headers=ADMIN).json()
    assert g["status"] == "ENCERRADO"
    assert g["aceitando_lances"] is False


def test_CA29_encerramento_direto(client, abrir):
    abrir("LEI-D", tipo_leilao="DIRETO", preco_inicial="500.00", incremento_minimo="5.00")
    lance(client, COMP_A, "500.00", "LEI-D")
    lance(client, COMP_B, "510.00", "LEI-D")
    b = client.post("/leiloes/LEI-D/encerrar", headers=ADMIN).json()
    assert b["vencedor_empresa_id"] == "COMP-B"
    assert b["valor_vencedor"] == "510.00"


def test_CA30_leilao_deserto(client, abrir):
    abrir()
    r = client.post("/leiloes/LEI-001/encerrar", headers=ADMIN)
    assert r.status_code == 200
    b = r.json()
    assert b["status"] == "DESERTO"
    assert b["resultado"] == "DESERTO"
    assert b["vencedor_empresa_id"] is None
    assert b["valor_vencedor"] is None
    assert b["lance_vencedor_id"] is None
    assert b["total_lances"] == 0


def test_CA31_encerramento_publica_negociacao_fechada(client, abrir, bus):
    abrir("LEI-001")
    abrir("LEI-002")
    lance(client, FORN_A, "1000.00", "LEI-001")
    for lid in ("LEI-001", "LEI-002"):
        resp = client.post(f"/leiloes/{lid}/encerrar", headers=ADMIN).json()
        msgs = [(k, m) for k, m in bus.on("negociacao_fechada") if m["payload"]["leilao_id"] == lid]
        assert len(msgs) == 1, lid
        key, m = msgs[0]
        assert key == lid
        p = m["payload"]
        assert p["demanda_id"] == "DEM-10"
        for campo in ("resultado", "vencedor_empresa_id", "valor_vencedor",
                      "lance_vencedor_id", "total_lances"):
            assert p[campo] == resp[campo], (lid, campo)


def test_CA32_autorizacao_do_encerramento(client, abrir):
    abrir()
    r = client.post("/leiloes/LEI-001/encerrar", headers=FORN_A)
    assert r.status_code == 403 and codigo(r) == "PERFIL_NAO_PERMITIDO"
    r = client.post("/leiloes/LEI-001/encerrar")
    assert r.status_code == 401 and codigo(r) == "NAO_AUTENTICADO"
    r = client.post("/leiloes/NAO-EXISTE/encerrar", headers=ADMIN)
    assert r.status_code == 404 and codigo(r) == "LEILAO_NAO_ENCONTRADO"


def test_CA33_encerrar_duas_vezes(client, abrir, bus):
    abrir()
    assert client.post("/leiloes/LEI-001/encerrar", headers=ADMIN).status_code == 200
    n = len(bus.published)
    r = client.post("/leiloes/LEI-001/encerrar", headers=ADMIN)
    assert r.status_code == 409 and codigo(r) == "LEILAO_ENCERRADO"
    assert len(bus.published) == n


# --------------------------------------------------------------------------- RF-07
def test_CA34_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "UP"}


# --------------------------------------------------------------------------- RNFs
def test_CA35_exatidao_decimal(client, abrir):
    abrir("LEI-C", preco_inicial="0.30", incremento_minimo="0.10")
    assert lance(client, FORN_A, "0.30", "LEI-C").status_code == 201
    r = lance(client, FORN_B, "0.20", "LEI-C")
    assert r.status_code == 201
    assert r.json()["valor"] == "0.20"
    abrir("LEI-D", tipo_leilao="DIRETO", preco_inicial="100.00", incremento_minimo="1.00")
    r = lance(client, COMP_A, "100", "LEI-D")
    assert r.status_code == 201
    assert r.json()["valor"] == "100.00"


def test_CA36_formato_de_erro(client, abrir, clock):
    abrir("LEI-001")
    abrir("LEI-T")
    lance(client, FORN_A, "1000.00")
    respostas = [
        client.get("/leiloes/LEI-001"),                       # 401
        client.get("/leiloes/NAO-EXISTE", headers=FORN_A),    # 404
        lance(client, COMP_A, "900.00"),                      # 403
        lance(client, FORN_A, "900.00"),                      # 409 líder
        lance(client, FORN_B, "abc"),                         # 422 valor
        lance(client, FORN_B, "999.00"),                      # 422 insuficiente
    ]
    clock.set(ENCERRA)
    respostas.append(lance(client, FORN_B, "900.00", "LEI-T"))  # 409 encerrado
    for r in respostas:
        assert 400 <= r.status_code < 500
        b = r.json()
        assert set(b.keys()) == {"erro"}, b
        assert isinstance(b["erro"]["codigo"], str) and b["erro"]["codigo"].strip()
        assert isinstance(b["erro"]["mensagem"], str) and b["erro"]["mensagem"].strip()


def test_CA37_desempenho_300_lances(client, abrir):
    abrir("LEI-P", preco_inicial="100000.00", incremento_minimo="1.00")
    inicio = time.perf_counter()
    for i in range(300):
        h = FORN_A if i % 2 == 0 else FORN_B
        r = lance(client, h, f"{100000 - i}.00", "LEI-P")
        assert r.status_code == 201, (i, r.text)
    assert time.perf_counter() - inicio < 3.0


def test_CA38_isolamento_entre_instancias():
    from fastapi.testclient import TestClient
    from app.main import create_app
    b1, b2 = FakeBus(), FakeBus()
    c1 = TestClient(create_app(b1, FakeClock()))
    c2 = TestClient(create_app(b2, FakeClock()))
    b1.deliver("leilao_iniciado", evento_leilao("LEI-001"))
    assert c1.get("/leiloes/LEI-001", headers=FORN_A).status_code == 200
    assert c2.get("/leiloes/LEI-001", headers=FORN_A).status_code == 404


def test_CA39_somente_dependencias_permitidas():
    from conftest import IMPL_DIR
    permitidos = set(sys.stdlib_module_names) | {"fastapi", "pydantic", "starlette", "app"}
    raiz = os.path.join(IMPL_DIR, "app")
    proibidos = []
    for dirpath, _, files in os.walk(raiz):
        for f in files:
            if not f.endswith(".py"):
                continue
            tree = ast.parse(open(os.path.join(dirpath, f), encoding="utf-8").read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    mods = [node.module or ""]
                else:
                    continue
                for m in mods:
                    if m.split(".")[0] not in permitidos:
                        proibidos.append((f, m))
    assert proibidos == []


def test_CA40_envelope_e_chave_de_particao(client, abrir, bus):
    abrir()
    lance(client, FORN_A, "1000.00")
    lance(client, FORN_B, "990.00")
    client.post("/leiloes/LEI-001/encerrar", headers=ADMIN)
    msgs = [(t, k, m) for t, k, m in bus.published
            if t in ("lance_realizado", "negociacao_fechada")]
    assert len(msgs) == 3
    ids = set()
    for t, k, m in msgs:
        assert k == "LEI-001"
        assert eh_uuid4(m["event_id"])
        ids.add(m["event_id"])
        assert m["tipo"] == t
        assert m["versao"] == 1 and not isinstance(m["versao"], bool)
        assert m["ocorrido_em"] == T0_STR
    assert len(ids) == 3
