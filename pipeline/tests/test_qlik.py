"""Testes do cliente Qlik (websocket + paginação) e do resumo de AC e SC, sem rede: um servidor falso local.

    uv run python -m unittest discover -s tests
"""

from __future__ import annotations

import base64
import hashlib
import json
import socket
import struct
import threading
import unittest
from unittest import mock

from orcamento_pipeline import pagamentos as pb
from orcamento_pipeline import pagamentos_qlik as pq
from orcamento_pipeline import qlik
from orcamento_pipeline.qlik import ErroQlik, Sessao, Websocket


# ---------- lado do servidor (quadros sem máscara, como manda a RFC) ----------

def quadro_servidor(opcode: int, dado: bytes, fim: bool = True) -> bytes:
    n = len(dado)
    if n < 126:
        tam = bytes([n])
    elif n < 1 << 16:
        tam = bytes([126]) + struct.pack(">H", n)
    else:
        tam = bytes([127]) + struct.pack(">Q", n)
    return bytes([(0x80 if fim else 0) | opcode]) + tam + dado


class SocketFalso:
    """Entrega bytes prontos e guarda o que o cliente envia."""

    def __init__(self, entrada: bytes):
        self.entrada, self.enviado = entrada, b""

    def recv(self, n):
        r, self.entrada = self.entrada[:n], self.entrada[n:]
        return r

    def sendall(self, d):
        self.enviado += d

    def close(self):
        pass


def ler_quadro_cliente(dado: bytes) -> tuple[int, bytes, bytes]:
    """(opcode, conteúdo desmascarado, resto)"""
    b1, b2 = dado[0], dado[1]
    assert b2 & 0x80, "quadro do cliente sem máscara"
    n, i = b2 & 0x7F, 2
    if n == 126:
        n, i = struct.unpack(">H", dado[2:4])[0], 4
    elif n == 127:
        n, i = struct.unpack(">Q", dado[2:10])[0], 10
    mascara = dado[i:i + 4]
    corpo = bytes(b ^ mascara[j % 4] for j, b in enumerate(dado[i + 4:i + 4 + n]))
    return b1 & 0x0F, corpo, dado[i + 4 + n:]


class TestWebsocket(unittest.TestCase):
    def test_quadro_do_cliente_e_mascarado_em_todos_os_tamanhos(self):
        for n in (0, 5, 125, 126, 70_000):
            dado = bytes(range(256)) * (n // 256) + bytes(range(n % 256))
            op, corpo, resto = ler_quadro_cliente(qlik.quadro(qlik.TEXTO, dado))
            self.assertEqual((op, corpo, resto), (qlik.TEXTO, dado, b""))

    def test_mascarar_e_reversivel(self):
        m = b"\x01\x02\x03\x04"
        self.assertEqual(qlik.mascarar(qlik.mascarar(b"abcdefg", m), m), b"abcdefg")
        self.assertEqual(qlik.mascarar(b"", m), b"")

    def test_junta_fragmentos_e_responde_ping(self):
        grande = json.dumps({"x": "a" * 100_000}).encode()
        entrada = (quadro_servidor(qlik.PING, b"oi")
                   + quadro_servidor(qlik.TEXTO, grande[:70_000], fim=False)
                   + quadro_servidor(qlik.PONG, b"")
                   + quadro_servidor(qlik.CONTINUACAO, grande[70_000:]))
        sock = SocketFalso(entrada)
        ws = Websocket(sock)
        self.assertEqual(ws.receber(), grande.decode())
        op, corpo, _ = ler_quadro_cliente(sock.enviado)
        self.assertEqual((op, corpo), (qlik.PONG, b"oi"))

    def test_sobra_do_cabecalho_e_lida_primeiro(self):
        msg = quadro_servidor(qlik.TEXTO, b'{"a":1}')
        ws = Websocket(SocketFalso(msg[3:]), sobra=msg[:3])
        self.assertEqual(ws.receber(), '{"a":1}')

    def test_fechamento_do_servidor_vira_erro(self):
        ws = Websocket(SocketFalso(quadro_servidor(qlik.FECHAR, struct.pack(">H", 1008) + b"limite")))
        with self.assertRaisesRegex(ErroQlik, "1008: limite"):
            ws.receber()

    def test_conexao_cortada_vira_erro(self):
        with self.assertRaises(ErroQlik):
            Websocket(SocketFalso(b"\x81")).receber()


# ---------- servidor Qlik falso, numa thread, em localhost ----------

class QlikFalso:
    """Responde ao handshake e a um punhado de métodos do Engine, como o servidor de verdade."""

    def __init__(self, linhas: int = 0, largura: int = 5, status: str = "101 Switching Protocols", tabelas=None):
        self.linhas, self.largura, self.status = linhas, largura, status
        self.tabelas = tabelas or {"EMPENHO": (linhas, ["NUMERO_EMPENHO", "NOME_CREDOR", "valor_pago"])}
        self.pedidos: list[dict] = []
        self.srv = socket.create_server(("127.0.0.1", 0))
        self.porta = self.srv.getsockname()[1]
        threading.Thread(target=self._atender, daemon=True).start()

    def _atender(self):
        conn, _ = self.srv.accept()
        self.srv.close()
        with conn:
            self._conversar(conn)

    def _conversar(self, conn):
        cab = b""
        while b"\r\n\r\n" not in cab:
            cab += conn.recv(4096)
        chave = next(l.split(":", 1)[1].strip() for l in cab.decode().split("\r\n") if l.lower().startswith("sec-websocket-key"))
        aceite = base64.b64encode(hashlib.sha1((chave + qlik.GUID_WS).encode()).digest()).decode()
        conn.sendall(f"HTTP/1.1 {self.status}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: {aceite}\r\n\r\n".encode())
        if not self.status.startswith("101"):
            return
        # O servidor de verdade manda um aviso logo de cara.
        conn.sendall(quadro_servidor(qlik.TEXTO, b'{"jsonrpc":"2.0","method":"OnAuthenticationInformation","params":{}}'))
        buf = b""
        while True:
            while True:
                try:
                    op, corpo, buf = ler_quadro_cliente(buf)
                    break
                except (IndexError, struct.error):
                    d = conn.recv(1 << 16)
                    if not d:
                        return
                    buf += d
            if op == qlik.FECHAR:
                return
            pedido = json.loads(corpo)
            self.pedidos.append(pedido)
            resposta = {"jsonrpc": "2.0", "id": pedido["id"]}
            resposta.update(self._responder(pedido))
            conn.sendall(quadro_servidor(qlik.TEXTO, json.dumps({"jsonrpc": "2.0", "method": "OnConnected"}).encode()))
            conn.sendall(quadro_servidor(qlik.TEXTO, json.dumps(resposta).encode()))

    def _responder(self, p):
        m = p["method"]
        if m == "OpenDoc":
            return {"result": {"qReturn": {"qType": "Doc", "qHandle": 1}}}
        if m == "GetTablesAndKeys":
            return {"result": {"qtr": [{"qName": t, "qNoOfRows": n, "qFields": [{"qName": f} for f in fs]} for t, (n, fs) in self.tabelas.items()]}}
        if m == "GetField":
            return {"result": {"qReturn": {"qHandle": 7}}}
        if m == "SelectValues":
            return {"result": {"qReturn": p["params"][0][0]["qText"] != "nada"}}
        if m == "CreateSessionObject":
            return {"result": {"qReturn": {"qHandle": 9}}}
        if m == "GetLayout":
            return {"result": {"qLayout": {"qHyperCube": {"qSize": {"qcx": self.largura, "qcy": self.linhas}}}}}
        if m == "GetHyperCubeData":
            pag = p["params"][1][0]
            matriz = [[{"qText": f"E{i}"}] + [{"qText": f"d{i}"}] * (self.largura - 3) + [{"qText": str(i), "qNum": float(i)}, {"qText": "-", "qNum": "NaN", "qIsNull": True}]
                      for i in range(pag["qTop"], pag["qTop"] + pag["qHeight"])]
            return {"result": {"qDataPages": [{"qMatrix": matriz}]}}
        if m in ("DestroySessionObject", "ClearAll"):
            return {"result": {}}
        return {"error": {"code": -1, "message": "método desconhecido", "parameter": m}}

    def sessao(self) -> Sessao:
        ws = Websocket.conectar("127.0.0.1", "/app/x", porta=self.porta, timeout=10, contexto=None)
        return Sessao("127.0.0.1", "x", pausa=0, ws=ws)


class TestSessao(unittest.TestCase):
    def test_paginacao_le_todas_as_linhas_uma_vez(self):
        srv = QlikFalso(linhas=4_321, largura=5)
        with srv.sessao() as s:
            doc = s.abrir_doc()
            total = []
            linhas = list(s.ler_tabela(doc, ["NUMERO_EMPENHO", "a", "b"], ["Sum(x)", "Sum(y)"], total=total))
        self.assertEqual(total, [4_321])
        self.assertEqual([l[0] for l in linhas], [f"E{i}" for i in range(4_321)])
        self.assertEqual(linhas[10], ["E10", "d10", "d10", 10.0, None])   # medida vira número; vazia vira None
        paginas = [p["params"][1][0] for p in srv.pedidos if p["method"] == "GetHyperCubeData"]
        # 10 mil células por página, 5 colunas: 2 mil linhas por vez, a última com o que sobra.
        self.assertEqual([(p["qTop"], p["qHeight"]) for p in paginas], [(0, 2000), (2000, 2000), (4000, 321)])
        self.assertTrue(all(p["qWidth"] * p["qHeight"] <= qlik.CELULAS_POR_PAGINA for p in paginas))
        # A tabela é apagada no fim, e com o mesmo id com que foi criada.
        criada = next(p for p in srv.pedidos if p["method"] == "CreateSessionObject")["params"][0]["qInfo"]["qId"]
        self.assertEqual(srv.pedidos[-1]["method"], "DestroySessionObject")
        self.assertEqual(srv.pedidos[-1]["params"], [criada])

    def test_tabela_vazia_nao_pede_paginas(self):
        srv = QlikFalso(linhas=0)
        with srv.sessao() as s:
            self.assertEqual(list(s.ler_tabela(s.abrir_doc(), ["a", "b", "c"], ["x", "y"])), [])
        self.assertFalse([p for p in srv.pedidos if p["method"] == "GetHyperCubeData"])

    def test_ano_vai_como_numero(self):
        srv = QlikFalso()
        with srv.sessao() as s:
            doc = s.abrir_doc()
            s.selecionar(doc, "ano_empenho", [2025])
            s.selecionar(doc, "NOME_ENTE", ["RIO BRANCO"])
            with self.assertRaises(ErroQlik):
                s.selecionar(doc, "NOME_ENTE", ["nada"])
        sel = [p["params"][0] for p in srv.pedidos if p["method"] == "SelectValues"]
        self.assertEqual(sel[0], [{"qText": "2025", "qIsNumeric": True, "qNumber": 2025}])
        self.assertEqual(sel[1], [{"qText": "RIO BRANCO"}])

    def test_campo_que_sumiu_para_a_carga(self):
        srv = QlikFalso()
        with srv.sessao() as s:
            doc = s.abrir_doc()
            s.conferir_campos(doc, {"EMPENHO": ["NUMERO_EMPENHO", "valor_pago"]})
            with self.assertRaisesRegex(ErroQlik, "EMPENHO.CREDOR.*tabela PAGAMENTO"):
                s.conferir_campos(doc, {"EMPENHO": ["CREDOR"], "PAGAMENTO": ["x"]})

    def test_erro_do_engine_vira_excecao(self):
        srv = QlikFalso()
        with srv.sessao() as s:
            with self.assertRaisesRegex(ErroQlik, "Inventado"):
                s.chamar("Inventado", 1)

    def test_servidor_que_recusa_o_websocket(self):
        srv = QlikFalso(status="403 Forbidden")
        with self.assertRaisesRegex(ErroQlik, "403"):
            Websocket.conectar("127.0.0.1", "/app/x", porta=srv.porta, timeout=10, contexto=None)


# ---------- resumo (as regras da Paraíba) ----------

CPF = "52998224725"            # CPF válido de exemplo (não é de ninguém)
CNPJ_A = "11222333000181"      # matriz
CNPJ_A2 = "11222333000262"     # filial da mesma empresa
CNPJ_B = "45997418000153"


def emp(chave, doc, nome, pago, tipo="Pessoa Jurídica", grupo="3", modalidade="90", elemento="39", unidade="Prefeitura", empenhado=None):
    return pq.linha([chave, unidade, doc, nome, tipo, grupo, modalidade, elemento, pago if empenhado is None else empenhado, pago])


class TestResumo(unittest.TestCase):
    def test_classifica_e_nunca_guarda_cpf(self):
        linhas = [
            emp("1", CNPJ_A, "CONSTRUTORA A LTDA", 100.0),
            emp("2", CNPJ_A2, "CONSTRUTORA A LTDA FILIAL", 50.0),
            emp("3", CNPJ_B, "", 70.0),                               # sem nome: o site completa pelo CNPJ
            emp("4", CPF, "FULANA DE TAL", 30.0, tipo="Pessoa Física", elemento="36"),
            emp("5", CNPJ_B, "PREFEITURA MUNICIPAL DE X", 500.0, grupo="1", elemento="11"),   # folha
            emp("6", CNPJ_B, "INSTITUTO NACIONAL DO SEGURO SOCIAL", 80.0, grupo="1", elemento="13"),
            emp("7", CNPJ_B, "BANCO DO BRASIL S/A", 40.0),
            emp("8", CNPJ_B, "FUNDO PREVIDENCIARIO", 300.0, modalidade="91", elemento="13"),   # entre unidades
            emp("9", CNPJ_A, "CONSTRUTORA A LTDA", 999.0, unidade="Consórcio Intermunicipal de Saúde"),
            emp("10", CNPJ_A, "CONSTRUTORA A LTDA", 0.0, empenhado=20.0),                      # só empenhado
        ]
        r, fora = pq.resumir(linhas)
        self.assertEqual(fora, {"linhas": 10, "consorcios": 999.0})
        self.assertEqual(r["pago"], 100 + 50 + 70 + 30 + 500 + 80 + 40)
        self.assertEqual(r["intra"], 300)
        self.assertEqual(r["n"], 7)
        t = dict(zip(pb.TIPOS, r["tipos"]))
        self.assertEqual(t, {"Fornecedores": 220, "Pessoas físicas": 30, "Folha de pagamento": 500, "Previdência": 80,
                             "Dívida e bancos": 40, "Outros órgãos públicos": 0})
        self.assertEqual((r["pessoas"], r["empresas"]), (1, 2))
        # Matriz e filial juntas, pela raiz do CNPJ; o nome mais comum que não é vazio.
        self.assertEqual(r["credores"], [["CONSTRUTORA A LTDA", CNPJ_A, 150, 2], ["", CNPJ_B, 70, 1]])
        texto = json.dumps(r, ensure_ascii=False)
        self.assertNotIn(CPF, texto)
        self.assertNotIn("FULANA", texto)

    def test_pessoa_fisica_dita_pelo_tribunal_vale_mais_que_os_digitos(self):
        # Um CNPJ válido marcado como pessoa física (MEI cadastrado pelo CPF do dono) fica nas pessoas.
        r, _ = pq.resumir([emp("1", CNPJ_A, "JOAO DA SILVA", 10.0, tipo="PESSOA_FISICA")])
        self.assertEqual((r["pessoas"], r["empresas"], r["credores"]), (1, 0, []))

    def test_linha_normaliza_codigos_e_vazios(self):
        l = pq.linha(["E1", None, "11.222.333/0001-81", "  NOME   COM  ESPACOS ", "PESSOA_JURIDICA", "3", "90", "4", None, None])
        self.assertEqual((l.doc, l.nome, l.elemento, l.pessoa_fisica, l.pago, l.empenhado),
                         (CNPJ_A, "NOME COM ESPACOS", "04", False, 0.0, 0.0))

    def test_nome_pelo_cnpj_usa_o_cache(self):
        cache = {CNPJ_B: "EMPRESA B LTDA"}
        self.assertEqual(pq.nome_do_cnpj(CNPJ_B, cache), "EMPRESA B LTDA")
        self.assertEqual(pq.formatar_cnpj(CNPJ_A), "11.222.333/0001-81")


class TestCarga(unittest.TestCase):
    def test_conexao_que_cai_reabre_e_repete_a_cidade(self):
        aberturas, chamadas = [], []

        class SessaoFalsa:
            def __exit__(self, *a):
                pass

        def abrir(painel, ano, pausa):
            aberturas.append(1)
            return SessaoFalsa(), 1, {"Empenho": (10, [])}

        def ler(s, doc, painel, ano, nome, medidas):
            chamadas.append(nome)
            if len(chamadas) == 2:   # a segunda cidade cai na primeira tentativa
                raise ErroQlik("o servidor fechou a conexão")
            return {"pago": 1}, {"linhas": 1}

        with mock.patch.object(pq, "abrir", abrir), mock.patch.object(pq, "ler_municipio", ler), \
                mock.patch.object(pq, "municipios", lambda s, d, p: ["A", "B", "C"]), mock.patch("builtins.print"):
            r, sem = pq.carregar(pq.SC, 2025, None, 0, {"A": "1", "B": "2", "C": "3"}, espera=0)
        self.assertEqual(chamadas, ["A", "B", "B", "C"])
        self.assertEqual(len(aberturas), 2)
        self.assertEqual((sorted(r), sem), (["1", "2", "3"], []))

    def test_desiste_depois_de_algumas_tentativas(self):
        class SessaoFalsa:
            def __exit__(self, *a):
                pass

        def ler(*a):
            raise ErroQlik("fora do ar")

        with mock.patch.object(pq, "abrir", lambda *a: (SessaoFalsa(), 1, {})), mock.patch.object(pq, "ler_municipio", ler), \
                mock.patch.object(pq, "municipios", lambda s, d, p: ["A"]), mock.patch("builtins.print"):
            with self.assertRaisesRegex(ErroQlik, "fora do ar"):
                pq.carregar(pq.SC, 2025, None, 0, {"A": "1"}, tentativas=3, espera=0)


if __name__ == "__main__":
    unittest.main()
