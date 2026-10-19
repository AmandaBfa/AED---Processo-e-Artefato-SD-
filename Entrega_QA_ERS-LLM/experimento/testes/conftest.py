"""Harness de conformidade — ESP-NEG-001 (Negociação/Leilão).

Dublês das portas definidas no §5.1 da especificação e fixtures comuns.
A implementação avaliada é carregada do diretório indicado em IMPL_DIR.
"""
import copy
import os
import uuid
import sys
from datetime import datetime, timezone

import pytest

IMPL_DIR = os.environ.get("IMPL_DIR")
if not IMPL_DIR:
    raise RuntimeError("Defina IMPL_DIR com o diretório que contém o pacote app/")
sys.path.insert(0, os.path.abspath(IMPL_DIR))

T0 = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)
T0_STR = "2026-10-17T12:00:00Z"
ENCERRA_STR = "2026-10-20T18:00:00Z"
ENCERRA = datetime(2026, 10, 20, 18, 0, 0, tzinfo=timezone.utc)


class FakeClock:
    def __init__(self, now=T0):
        self._now = now

    def now(self):
        return self._now

    def set(self, dt):
        self._now = dt


class FakeBus:
    def __init__(self):
        self.handlers = {}
        self.published = []  # (topic, key, message)

    def subscribe(self, topic, handler):
        self.handlers.setdefault(topic, []).append(handler)

    def publish(self, topic, key, message):
        self.published.append((topic, key, copy.deepcopy(message)))

    def deliver(self, topic, message):
        for h in self.handlers.get(topic, []):
            h(copy.deepcopy(message))

    def on(self, topic):
        return [(k, m) for t, k, m in self.published if t == topic]


def evento_leilao(leilao_id="LEI-001", event_id=None, **payload_overrides):
    payload = {
        "leilao_id": leilao_id,
        "demanda_id": "DEM-10",
        "produto_id": "PROD-7",
        "quantidade": 500,
        "tipo_leilao": "REVERSO",
        "preco_inicial": "1000.00",
        "incremento_minimo": "10.00",
        "encerra_em": ENCERRA_STR,
    }
    for k, v in payload_overrides.items():
        if v is _REMOVE:
            payload.pop(k, None)
        else:
            payload[k] = v
    return {
        "event_id": event_id or str(uuid.uuid4()),
        "tipo": "leilao_iniciado",
        "versao": 1,
        "ocorrido_em": "2026-10-17T11:59:00Z",
        "payload": payload,
    }


class _Remove:
    pass


_REMOVE = _Remove()


def H(empresa, perfil, **extra):
    h = {"X-Empresa-Id": empresa, "X-Perfil": perfil}
    h.update(extra)
    return h


FORN_A = H("FORN-A", "FORNECEDOR")
FORN_B = H("FORN-B", "FORNECEDOR")
COMP_A = H("COMP-A", "COMPRADOR")
COMP_B = H("COMP-B", "COMPRADOR")
ADMIN = H("ADM-1", "ADMIN")
TRANSP = H("TRA-1", "TRANSPORTADORA")


def codigo(resp):
    return resp.json()["erro"]["codigo"]


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def bus():
    return FakeBus()


@pytest.fixture
def client(bus, clock):
    from fastapi.testclient import TestClient
    from app.main import create_app

    return TestClient(create_app(bus, clock))


@pytest.fixture
def abrir(bus):
    def _abrir(leilao_id="LEI-001", **kw):
        bus.deliver("leilao_iniciado", evento_leilao(leilao_id, **kw))
    return _abrir
