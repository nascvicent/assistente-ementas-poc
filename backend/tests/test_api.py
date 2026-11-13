from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import EMENTA_VALIDA
from tests.test_ingestao import VOTO_COM_EMENTA

cliente = TestClient(app)


def test_saude():
    assert cliente.get("/saude").json()["status"] == "ok"


def test_ingestao_txt_remove_ementa():
    r = cliente.post("/ingestao", files={"arquivo": ("voto.txt", VOTO_COM_EMENTA.encode(), "text/plain")})
    corpo = r.json()
    assert r.status_code == 200
    assert corpo["ementa_removida"]["texto"].startswith("EMENTA:")
    assert "EMENTA" not in corpo["paginas"][0]["texto"]


def test_ingestao_formato_invalido():
    r = cliente.post("/ingestao", files={"arquivo": ("voto.rtf", b"x", "application/rtf")})
    assert r.status_code == 415


def test_linter():
    assert cliente.post("/linter", json={"ementa": EMENTA_VALIDA}).json()["total"] == 0
    r = cliente.post("/linter", json={"ementa": EMENTA_VALIDA.replace("1. Auditoria", "1. Trata-se de Auditoria")}).json()
    assert r["achados"][0]["codigo"] == "E06"
