"""Os dados de quem faz o pedido. A Lei de Acesso exige a identificação do requerente, e cada formulário pede uma
parte disso (nome, CPF, documento, endereço). Ficam num arquivo local, fora do repositório, legível só pelo dono:
~/.config/orcamento-br/lai.toml. Nada daqui vai para o git, para o registro dos pedidos ou para a saída do terminal."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

ARQUIVO = Path.home() / ".config" / "orcamento-br" / "lai.toml"

MODELO = """\
# Dados de quem faz os pedidos pela Lei de Acesso à Informação (uv run --extra lai lai enviar ...).
# Este arquivo fica só neste computador. Preencha o que tiver; cada formulário usa uma parte.
nome = ""
cpf = ""                 # 000.000.000-00
nascimento = ""          # DD/MM/AAAA
sexo = ""                # Masculino ou Feminino (alguns formulários perguntam; pode deixar vazio)
escolaridade = ""        # ex.: Ensino Superior (opcional)
rg = ""                  # número do documento de identidade
rg_orgao = ""            # órgão emissor, ex.: SSP
rg_uf = ""               # UF do documento, ex.: SP
email = ""
ddd = ""                 # só os dígitos, ex.: 11
telefone = ""            # só os dígitos, sem o DDD
cep = ""
uf = ""                  # sigla, ex.: SP
municipio = ""
logradouro = ""
numero = ""
complemento = ""
bairro = ""
# Cópia do documento de identidade (PDF ou imagem), para os formulários que pedem anexo (TCE-RS):
documento = ""           # caminho do arquivo, ex.: /Users/eu/Documentos/rg.pdf
documento_verso = ""     # se o verso for um arquivo à parte
"""


@dataclass
class Pessoa:
    nome: str = ""
    cpf: str = ""
    nascimento: str = ""
    sexo: str = ""
    escolaridade: str = ""
    rg: str = ""
    rg_orgao: str = ""
    rg_uf: str = ""
    email: str = ""
    ddd: str = ""
    telefone: str = ""
    cep: str = ""
    uf: str = ""
    municipio: str = ""
    logradouro: str = ""
    numero: str = ""
    complemento: str = ""
    bairro: str = ""
    documento: str = ""
    documento_verso: str = ""

    @property
    def telefone_completo(self) -> str:
        return f"({self.ddd}) {self.telefone}" if self.ddd else self.telefone

    def faltam(self, campos: list[str]) -> list[str]:
        return [c for c in campos if not getattr(self, c)]


def criar_modelo() -> Path:
    """Cria o arquivo de configuração vazio (só se não existir), com permissão 600."""
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    if not ARQUIVO.exists():
        ARQUIVO.write_text(MODELO, encoding="utf-8")
    os.chmod(ARQUIVO, 0o600)
    return ARQUIVO


def carregar(arquivo: Path = ARQUIVO) -> Pessoa:
    if not arquivo.exists():
        raise SystemExit(f"Falta {arquivo}. Rode `uv run --extra lai lai configurar` e preencha os seus dados.")
    dados = tomllib.loads(arquivo.read_text(encoding="utf-8"))
    validos = {f.name for f in fields(Pessoa)}
    return Pessoa(**{k: str(v).strip() for k, v in dados.items() if k in validos})
