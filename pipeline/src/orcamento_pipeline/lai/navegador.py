"""O navegador dos pedidos: um Chromium visível, com perfil próprio (os logins, como o do gov.br, ficam guardados
entre uma execução e outra), e as pausas em que a pessoa age: login, CAPTCHA e a conferência antes de enviar."""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

PERFIL = Path.home() / ".config" / "orcamento-br" / "lai-navegador"
ALERTAS: list[str] = []   # o texto dos alertas (alert/confirm) que o site mostrou nesta execução
ENSAIO = False   # ensaio: preenche e para antes de enviar; as pausas não esperam ninguém


@contextlib.contextmanager
def abrir(visivel: bool = True):
    """Uma página num Chromium com o perfil dos pedidos. visivel=False só para inspecionar formulários."""
    from playwright.sync_api import sync_playwright

    PERFIL.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PERFIL), headless=not visivel, locale="pt-BR", viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,   # alguns órgãos têm certificado incompleto (sem a cadeia intermediária)
        )
        try:
            pagina = ctx.pages[0] if ctx.pages else ctx.new_page()
            pagina.set_default_timeout(60_000)
            ALERTAS.clear()

            def alerta(d):   # o Playwright fecha os alertas sem mostrar: aqui eles aparecem no terminal
                ALERTAS.append(d.message)
                print(f"\n  O site disse: {d.message}", flush=True)
                d.accept()

            pagina.on("dialog", alerta)
            yield pagina
        finally:
            ctx.close()


def assentar(pagina, segundos: float = 10) -> None:
    """Espera a página parar de carregar, mas sem travar: muitos sites nunca param (estatísticas, chat, polling)."""
    try:
        pagina.wait_for_load_state("networkidle", timeout=segundos * 1000)
    except Exception:   # noqa: BLE001 — o tempo acabou: segue com o que já carregou
        pass


def esperar_pessoa(motivo: str) -> None:
    """Para e espera a pessoa fazer algo no navegador (login, CAPTCHA). O script nunca resolve nem contorna isso."""
    if ENSAIO:
        print(f"  (ensaio) pausa: {motivo}")
        return
    input(f"\n>>> {motivo}\n    Faça isso na janela do navegador e aperte Enter aqui para continuar. ")


def confirmar(pergunta: str) -> bool:
    return input(f"\n>>> {pergunta} [s/N] ").strip().lower() in ("s", "sim")


CAMPOS_JS = """
() => {
  const rotulo = (el) => {
    if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l) return l.innerText.trim(); }
    const pai = el.closest('label'); if (pai) return pai.innerText.trim();
    return (el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.title || '').trim();
  };
  const visivel = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  return [...document.querySelectorAll('input, select, textarea, button')]
    .filter((el) => el.type !== 'hidden')
    .map((el) => ({
      tag: el.tagName.toLowerCase(), tipo: el.type || '', nome: el.name || '', id: el.id || '',
      rotulo: rotulo(el).slice(0, 80), obrigatorio: el.required, visivel: visivel(el),
      opcoes: el.tagName === 'SELECT' ? [...el.options].slice(0, 15).map((o) => o.text.trim()) : undefined,
      texto: el.tagName === 'BUTTON' || el.type === 'submit' ? (el.innerText || el.value || '').trim().slice(0, 40) : undefined,
    }));
}
"""


def inspecionar(url: str, saida: Path | None = None) -> list[dict]:
    """Lista os campos de um formulário (também dentro dos iframes) e grava uma captura, para escrever o adaptador."""
    with abrir(visivel=False) as pagina:
        pagina.goto(url, wait_until="networkidle")
        campos = []
        for quadro in pagina.frames:
            try:
                for c in quadro.evaluate(CAMPOS_JS):
                    c["quadro"] = quadro.url if quadro != pagina.main_frame else ""
                    campos.append(c)
            except Exception:   # noqa: BLE001 — quadro de outro domínio que não deixa ler
                continue
        if saida:
            saida.parent.mkdir(parents=True, exist_ok=True)
            pagina.screenshot(path=str(saida.with_suffix(".png")), full_page=True)
            saida.write_text(json.dumps(campos, ensure_ascii=False, indent=1), encoding="utf-8")
        return campos
