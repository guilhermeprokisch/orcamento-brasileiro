"""Conversa com painéis Qlik pela mesma conexão que o navegador usa (websocket + JSON-RPC do "Engine").

Alguns Tribunais de Contas (AC, SC) publicam os empenhos das prefeituras só num painel Qlik, sem
arquivo para baixar. O painel abre sem login, e o servidor responde a qualquer programa que fale o
protocolo dele. Não é uma API oficial: pode mudar sem aviso, por isso `conferir_campos` deve rodar
antes de cada carga. Os servidores desses tribunais só aceitam acesso do Brasil.

Só biblioteca padrão. O websocket (RFC 6455) é o mínimo que o Qlik precisa: texto, mensagens
fragmentadas, ping/pong e fechamento.

    with Sessao("qlik.tceac.tc.br", "7e2eb635-…") as s:
        doc = s.abrir_doc()
        s.selecionar(doc, "ano_empenho", [2025])
        for linha in s.ler_tabela(doc, ["NUMERO_EMPENHO", "NOME_CREDOR"], ["Sum(valor_pago)"]):
            ...
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import time
from collections.abc import Iterator
from typing import Any

from .fontes import CONTEXTO_TLS

GUID_WS = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
CELULAS_POR_PAGINA = 10_000   # limite do Qlik por chamada de GetHyperCubeData

TEXTO, BINARIO, FECHAR, PING, PONG, CONTINUACAO = 0x1, 0x2, 0x8, 0x9, 0xA, 0x0


class ErroQlik(RuntimeError):
    pass


class Websocket:
    """Cliente websocket mínimo sobre um socket já conectado (TLS ou não)."""

    def __init__(self, sock, sobra: bytes = b""):
        self.sock = sock
        self.buf = sobra

    @classmethod
    def conectar(cls, host: str, caminho: str, porta: int = 443, timeout: float = 120, contexto: ssl.SSLContext | None = CONTEXTO_TLS) -> "Websocket":
        try:
            sock = socket.create_connection((host, porta), timeout=timeout)
        except OSError as e:
            raise ErroQlik(f"não consegui conectar a {host} ({e}); estes servidores só aceitam acesso do Brasil") from e
        try:
            if contexto is not None:
                sock = contexto.wrap_socket(sock, server_hostname=host)
            return cls._abrir(sock, host, caminho)
        except BaseException:
            sock.close()
            raise

    @classmethod
    def _abrir(cls, sock, host: str, caminho: str) -> "Websocket":
        chave = base64.b64encode(os.urandom(16)).decode()
        pedido = (
            f"GET {caminho} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {chave}\r\nSec-WebSocket-Version: 13\r\nOrigin: https://{host}\r\n"
            "User-Agent: Mozilla/5.0 (orcamentobrasileiro.com.br)\r\n\r\n"
        )
        sock.sendall(pedido.encode())
        cabecalho = b""
        while b"\r\n\r\n" not in cabecalho:
            dado = sock.recv(4096)
            if not dado:
                raise ErroQlik(f"{host} fechou a conexão antes de responder")
            cabecalho += dado
        cabecalho, sobra = cabecalho.split(b"\r\n\r\n", 1)
        status, *linhas = cabecalho.decode("latin-1").split("\r\n")
        if " 101 " not in status + " ":
            raise ErroQlik(f"{host} recusou o websocket: {status} (estes servidores só aceitam acesso do Brasil)")
        campos = {k.strip().lower(): v.strip() for k, _, v in (l.partition(":") for l in linhas)}
        esperado = base64.b64encode(hashlib.sha1((chave + GUID_WS).encode()).digest()).decode()
        if campos.get("sec-websocket-accept") != esperado:
            raise ErroQlik(f"{host}: resposta do websocket com chave errada")
        return cls(sock, sobra)

    def _exato(self, n: int) -> bytes:
        while len(self.buf) < n:
            dado = self.sock.recv(1 << 16)
            if not dado:
                raise ErroQlik("o servidor fechou a conexão")
            self.buf += dado
        r, self.buf = self.buf[:n], self.buf[n:]
        return r

    def _quadro(self) -> tuple[bool, int, bytes]:
        b1, b2 = self._exato(2)
        n = b2 & 0x7F
        if n == 126:
            n = struct.unpack(">H", self._exato(2))[0]
        elif n == 127:
            n = struct.unpack(">Q", self._exato(8))[0]
        mascara = self._exato(4) if b2 & 0x80 else None
        dado = self._exato(n)
        if mascara:
            dado = mascarar(dado, mascara)
        return bool(b1 & 0x80), b1 & 0x0F, dado

    def _enviar_quadro(self, opcode: int, dado: bytes) -> None:
        self.sock.sendall(quadro(opcode, dado))

    def enviar(self, texto: str) -> None:
        self._enviar_quadro(TEXTO, texto.encode())

    def receber(self) -> str:
        """A próxima mensagem de texto inteira (junta os fragmentos; responde a pings no caminho)."""
        partes: list[bytes] = []
        while True:
            fim, opcode, dado = self._quadro()
            if opcode == PING:
                self._enviar_quadro(PONG, dado)
                continue
            if opcode == PONG:
                continue
            if opcode == FECHAR:
                codigo = struct.unpack(">H", dado[:2])[0] if len(dado) >= 2 else None
                raise ErroQlik(f"o servidor fechou o websocket ({codigo}: {dado[2:].decode(errors='replace')})")
            if opcode not in (TEXTO, BINARIO, CONTINUACAO):
                raise ErroQlik(f"quadro de websocket desconhecido: {opcode}")
            partes.append(dado)
            if fim:
                return b"".join(partes).decode()

    def fechar(self) -> None:
        try:
            self._enviar_quadro(FECHAR, struct.pack(">H", 1000))
        except OSError:
            pass
        self.sock.close()


def mascarar(dado: bytes, mascara: bytes) -> bytes:
    # XOR com a máscara de 4 bytes, rápido em mensagens grandes: um inteiro só.
    n = len(dado)
    m = (mascara * (n // 4 + 1))[:n]
    return (int.from_bytes(dado, "big") ^ int.from_bytes(m, "big")).to_bytes(n, "big")


def quadro(opcode: int, dado: bytes, mascara: bytes | None = None) -> bytes:
    """Um quadro do cliente: sempre final e sempre mascarado (a RFC exige do lado do cliente)."""
    mascara = mascara or os.urandom(4)
    n = len(dado)
    if n < 126:
        tam = bytes([0x80 | n])
    elif n < 1 << 16:
        tam = bytes([0x80 | 126]) + struct.pack(">H", n)
    else:
        tam = bytes([0x80 | 127]) + struct.pack(">Q", n)
    return bytes([0x80 | opcode]) + tam + mascara + mascarar(dado, mascara)


class Sessao:
    """Uma sessão anônima no Engine do Qlik: uma chamada de cada vez, com pausa entre as páginas."""

    def __init__(self, host: str, app: str, pausa: float = 1.0, ws: Websocket | None = None):
        self.host, self.app, self.pausa = host, app, pausa
        self.ws = ws
        self._id = 0

    def __enter__(self) -> "Sessao":
        if self.ws is None:
            self.ws = Websocket.conectar(self.host, f"/app/{self.app}")
        return self

    def __exit__(self, *exc) -> None:
        if self.ws:
            self.ws.fechar()

    def chamar(self, metodo: str, handle: int, *params: Any) -> dict:
        self._id += 1
        meu = self._id
        self.ws.enviar(json.dumps({"jsonrpc": "2.0", "id": meu, "method": metodo, "handle": handle, "params": list(params)}))
        while True:
            r = json.loads(self.ws.receber())
            if r.get("id") != meu:
                continue   # avisos do servidor (OnAuthenticationInformation, OnConnected, mudanças)
            if "error" in r:
                raise ErroQlik(f"{metodo}: {r['error'].get('message')} ({r['error'].get('parameter', '')})")
            return r["result"]

    def abrir_doc(self) -> int:
        return self.chamar("OpenDoc", -1, self.app)["qReturn"]["qHandle"]

    def tabelas(self, doc: int) -> dict[str, tuple[int, list[str]]]:
        """{tabela: (linhas, [campos])}, como o modelo de dados do painel está agora."""
        r = self.chamar("GetTablesAndKeys", doc, {"qcx": 1000, "qcy": 1000}, {"qcx": 0, "qcy": 0}, 30, True, False)
        return {t["qName"]: (t.get("qNoOfRows", 0), [f["qName"] for f in t["qFields"]]) for t in r["qtr"]}

    def conferir_campos(self, doc: int, esperados: dict[str, list[str]]) -> dict[str, tuple[int, list[str]]]:
        """Para a carga se o painel mudou: cada tabela tem de existir com os campos que o coletor lê."""
        tabelas = self.tabelas(doc)
        faltam = []
        for tabela, campos in esperados.items():
            if tabela not in tabelas:
                faltam.append(f"tabela {tabela}")
                continue
            faltam += [f"{tabela}.{c}" for c in campos if c not in tabelas[tabela][1]]
        if faltam:
            raise ErroQlik(f"o painel de {self.host} mudou; não achei: {', '.join(faltam)}")
        return tabelas

    def selecionar(self, doc: int, campo: str, valores: list) -> None:
        """Filtra o painel, como clicar num valor da lista. Números vão como número (o ano, por exemplo)."""
        h = self.chamar("GetField", doc, campo)["qReturn"]["qHandle"]
        itens = [{"qText": str(v), "qIsNumeric": True, "qNumber": v} if isinstance(v, (int, float)) else {"qText": v} for v in valores]
        if not self.chamar("SelectValues", h, itens, False, False).get("qReturn"):
            raise ErroQlik(f"não consegui selecionar {valores} em {campo}")

    def limpar(self, doc: int) -> None:
        self.chamar("ClearAll", doc, False)

    def valores(self, doc: int, campo: str, limite: int = 10_000) -> list[str]:
        """Os valores possíveis de um campo com a seleção atual (lista do filtro do painel)."""
        qid = f"orcamento-{self._id + 1}"
        lista = self.chamar("CreateSessionObject", doc, {
            "qInfo": {"qId": qid, "qType": "lista"},
            "qListObjectDef": {"qDef": {"qFieldDefs": [campo]}, "qInitialDataFetch": [{"qTop": 0, "qLeft": 0, "qWidth": 1, "qHeight": limite}]},
        })["qReturn"]["qHandle"]
        layout = self.chamar("GetLayout", lista)["qLayout"]["qListObject"]
        self.chamar("DestroySessionObject", doc, qid)
        return [l[0]["qText"] for p in layout["qDataPages"] for l in p["qMatrix"] if l[0]["qState"] in ("O", "S")]

    def ler_tabela(self, doc: int, dimensoes: list[str], medidas: list[str] = (), total: list[int] | None = None) -> Iterator[list]:
        """Monta uma tabela com a seleção atual e devolve as linhas, página por página.

        Cada linha é uma lista de valores: texto nas dimensões, número nas medidas (None quando vazio).
        O Qlik junta as linhas com as mesmas dimensões: inclua sempre uma chave (o número do empenho).
        `total`, se passado, recebe o número de linhas que o Qlik diz ter.
        """
        qid = f"orcamento-{self._id + 1}"
        defs = {
            "qInfo": {"qId": qid, "qType": "tabela"},
            "qHyperCubeDef": {
                "qDimensions": [{"qDef": {"qFieldDefs": [d]}, "qNullSuppression": False} for d in dimensoes],
                "qMeasures": [{"qDef": {"qDef": m}} for m in medidas],
                "qSuppressZero": False, "qSuppressMissing": False,
                "qInitialDataFetch": [],
            },
        }
        cubo = self.chamar("CreateSessionObject", doc, defs)["qReturn"]["qHandle"]
        try:
            layout = self.chamar("GetLayout", cubo)["qLayout"]["qHyperCube"]
            if layout.get("qError"):
                raise ErroQlik(f"tabela recusada: {layout['qError']}")
            linhas, largura = layout["qSize"]["qcy"], layout["qSize"]["qcx"]
            if total is not None:
                total.append(linhas)
            n_dim = len(dimensoes)
            altura = max(1, CELULAS_POR_PAGINA // largura)
            for topo in range(0, linhas, altura):
                if topo:
                    time.sleep(self.pausa)
                paginas = self.chamar("GetHyperCubeData", cubo, "/qHyperCubeDef",
                                      [{"qTop": topo, "qLeft": 0, "qWidth": largura, "qHeight": min(altura, linhas - topo)}])["qDataPages"]
                for linha in paginas[0]["qMatrix"]:
                    yield [celula(c, i >= n_dim) for i, c in enumerate(linha)]
        finally:
            self.chamar("DestroySessionObject", doc, qid)


def celula(c: dict, medida: bool):
    if c.get("qIsNull") or c.get("qText") == "-" and medida:
        return None
    if medida:
        n = c.get("qNum")
        return n if isinstance(n, (int, float)) else None
    return c.get("qText")
