"""A ponte entre o comando `lai` e a extensão do Chrome (pipeline/lai-extensao/): um servidor HTTP só no próprio
computador (127.0.0.1:8765), com uma senha de uso único por pedido.

1. O comando guarda os passos do pedido sob uma senha e abre o formulário no Chrome com `#lai=<senha>` no endereço.
2. A extensão vê a senha, pede os passos (GET /pedido?senha=...), preenche e avisa (POST /evento, "preenchido").
3. A pessoa confere e clica em enviar. A extensão lê a página de confirmação e manda o trecho com o protocolo
   (POST /evento, "resultado").

O servidor só aceita conexões do próprio computador e só responde a quem tem a senha; os passos (com os dados da pessoa)
saem uma vez só e são apagados.
"""

from __future__ import annotations

import json
import queue
import secrets
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PORTA = 8765


class Ponte:
    def __init__(self, passos: list[dict], pronto: str = "", porta: int = PORTA):
        self.senha = secrets.token_urlsafe(24)
        self._pedido: dict | None = {"passos": passos, "pronto": pronto}
        self.eventos: queue.Queue[dict] = queue.Queue()
        ponte = self

        class Tratador(BaseHTTPRequestHandler):
            def log_message(self, *args):   # silêncio no terminal
                pass

            def _responder(self, codigo: int, corpo: dict) -> None:
                dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
                self.send_response(codigo)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            def do_GET(self):
                u = urlparse(self.path)
                senha = parse_qs(u.query).get("senha", [""])[0]
                if u.path != "/pedido" or not secrets.compare_digest(senha, ponte.senha) or ponte._pedido is None:
                    return self._responder(404, {"erro": "nada aqui"})
                pedido, ponte._pedido = ponte._pedido, None   # uso único
                self._responder(200, pedido)

            def do_POST(self):
                try:
                    corpo = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
                except ValueError:
                    return self._responder(400, {"erro": "json"})
                if urlparse(self.path).path != "/evento" or not secrets.compare_digest(str(corpo.get("senha", "")), ponte.senha):
                    return self._responder(404, {"erro": "nada aqui"})
                ponte.eventos.put({k: v for k, v in corpo.items() if k != "senha"})
                self._responder(200, {"ok": True})

        self._servidor = ThreadingHTTPServer(("127.0.0.1", porta), Tratador)
        self._fio = threading.Thread(target=self._servidor.serve_forever, daemon=True)

    def __enter__(self) -> "Ponte":
        self._fio.start()
        return self

    def __exit__(self, *exc) -> None:
        self._servidor.shutdown()
        self._servidor.server_close()

    def endereco(self, url: str) -> str:
        return f"{url.split('#')[0]}#lai={self.senha}"

    def abrir_no_chrome(self, url: str) -> None:
        subprocess.run(["open", "-a", "Google Chrome", self.endereco(url)], check=True)

    def esperar(self, tipo: str, segundos: float) -> dict | None:
        """O próximo evento do tipo pedido (preenchido, erro, resultado), ou None se o tempo acabar."""
        try:
            while True:
                ev = self.eventos.get(timeout=segundos)
                if ev.get("tipo") in (tipo, "erro"):
                    return ev
        except queue.Empty:
            return None
