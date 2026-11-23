import datetime as dt

from orcamento_pipeline.lai import registro
from orcamento_pipeline.lai.cli import FICTICIA, ler_pedido
from orcamento_pipeline.lai.formularios import FORMULARIOS, Pedido, achar_protocolo


def test_protocolo_na_pagina():
    assert achar_protocolo("Seu pedido foi registrado. Protocolo: 2026.11.000123") == "2026.11.000123"
    assert achar_protocolo("Número do protocolo 01015.003440/2026-60 gerado") == "01015.003440/2026-60"
    assert achar_protocolo("Manifestação nº 45871 registrada com sucesso") == "45871"
    assert achar_protocolo("Obrigado pelo contato.") is None


def test_pedido_le_assunto_e_assina(tmp_path):
    arq = tmp_path / "p.txt"
    arq.write_text("Assunto: Folha dos municípios\n\nPrezados,\n\nTexto.\n\nAtenciosamente,\n{nome}\n{email}\n", encoding="utf-8")
    p = ler_pedido("TCE-SE", arq, FICTICIA)
    assert p.assunto == "Folha dos municípios"
    assert p.texto.endswith("Teste Ensaio\nteste@example.com")
    assert "Teste Ensaio" not in p.sem_assinatura   # o campo público do TCE-RS vai sem o nome
    assert p.com_assunto.startswith("Assunto: Folha dos municípios\n\nPrezados,")


def test_registro_sem_dado_pessoal_e_prazos(tmp_path):
    arq = tmp_path / "registro.csv"
    linha = registro.anotar("ALMG", "Verba", "formulário", "123", enviado=dt.date(2026, 11, 23), arquivo=arq)
    assert linha["prazo"] == "2026-12-13" and linha["prazo_prorrogado"] == "2026-12-23"
    assert set(linha) == set(registro.COLUNAS)
    assert registro.vencidos(dt.date(2026, 12, 24), arquivo=arq)[0]["orgao"] == "ALMG"
    assert registro.vencidos(dt.date(2026, 12, 20), arquivo=arq) == []


def test_textos_prontos_tem_formulario():
    from pathlib import Path
    pasta = Path(__file__).resolve().parents[2] / "docs" / "pedidos-lai" / "textos" / "custo-dos-mandatos"
    for arq in pasta.glob("*.txt"):
        assert arq.stem in FORMULARIOS
        assert arq.read_text(encoding="utf-8").startswith("Assunto: ")


def test_pedido_sem_assinatura_quando_nao_ha():
    assert Pedido("X", "a", "só o texto").sem_assinatura == "só o texto"


def test_ponte_senha_e_uso_unico():
    import json
    import urllib.error
    import urllib.request

    from orcamento_pipeline.lai.ponte import Ponte

    with Ponte([{"acao": "preencher", "seletor": "#a", "valor": "x"}], porta=8799) as ponte:
        base = "http://127.0.0.1:8799"
        try:
            urllib.request.urlopen(f"{base}/pedido?senha=errada")
            raise AssertionError("aceitou senha errada")
        except urllib.error.HTTPError as e:
            assert e.code == 404
        ok = json.loads(urllib.request.urlopen(f"{base}/pedido?senha={ponte.senha}").read())
        assert ok["passos"][0]["valor"] == "x"
        try:
            urllib.request.urlopen(f"{base}/pedido?senha={ponte.senha}")   # segunda vez: já foi
            raise AssertionError("entregou duas vezes")
        except urllib.error.HTTPError as e:
            assert e.code == 404
        req = urllib.request.Request(f"{base}/evento", json.dumps({"senha": ponte.senha, "tipo": "preenchido"}).encode(),
                                     {"Content-Type": "application/json"})
        urllib.request.urlopen(req)
        assert ponte.esperar("preenchido", 2) == {"tipo": "preenchido"}


def test_caixa_casa_dominio_do_orgao():
    from orcamento_pipeline.lai.caixa import _casa, _dominio

    assert _dominio("e-mail para ouvidoria@al.to.leg.br") == "al.to.leg.br"
    assert _dominio("formulário: https://www.almg.gov.br/apps/fale-com/assembleia") == "almg.gov.br"
    assert _casa("almg.gov.br", "almg.gov.br")
    assert _casa("mail.almg.gov.br", "almg.gov.br")
    assert not _casa("tcese.tc.br", "tce.se.gov.br")
    assert not _casa("inout.email", "almg.gov.br")
