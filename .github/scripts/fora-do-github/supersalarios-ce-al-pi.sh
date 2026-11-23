#!/usr/bin/env bash
# Cópia do que está instalado na máquina de casa (usuário claude, ~/bin/ e /etc/systemd/system/).
# Acima do teto, Executivo estadual: a carga mensal de CE, AL e PI, que recusam os servidores do GitHub (CE responde
# 403; AL e PI não aceitam a conexão) e respondem daqui, pela conexão normal da casa, sem proxy.
#
# Roda no dia 24 (timer supersalarios-ce-al-pi.timer), um dia antes do workflow supersalarios-estados.yml do GitHub.
# Baixa do release "dados-supersalarios-estados" o cache dos três estados (somas por órgão e mês, nenhum dado de
# pessoa), roda `supersalarios-estados --uf CE,AL,PI` e, se entrou mês novo, sobe o cache de volta para o release. No
# dia 25, o workflow do GitHub monta o arquivo com eles e abre o pull request em rascunho para conferir.
#
#   ENVIAR=0 ~/bin/supersalarios-ce-al-pi.sh   # roda sem subir nada (teste)
set -euo pipefail

REPO=guilhermeprokisch/orcamento-brasileiro
RELEASE=dados-supersalarios-estados
DIR="$HOME/orcamento-brasileiro"
UFS="ce al pi"
ENVIAR="${ENVIAR:-1}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export PATH="$HOME/.local/bin:$PATH"

cd "$DIR"
git fetch -q origin
git reset -q --hard origin/main   # esta cópia só lê: nada é commitado aqui

CACHE=data/raw/supersalarios-estados
mkdir -p "$CACHE"
for uf in $UFS; do
  rm -rf "${CACHE:?}/$uf"
  if curl -fsSL -o "$TMP/estados-$uf.tar" "https://github.com/$REPO/releases/download/$RELEASE/estados-$uf.tar"; then
    tar -xf "$TMP/estados-$uf.tar" -C "$CACHE"
  fi
  echo "$uf: $(find "$CACHE/$uf" -name '[0-9]*.json.gz' 2>/dev/null | wc -l) meses no cache"
done
antes="$(find $(printf "$CACHE/%s " $UFS) -name '[0-9]*.json.gz' 2>/dev/null | sort | xargs -r sha256sum | sha256sum)"

uv run --project pipeline supersalarios-estados --uf CE,AL,PI 2>&1 | grep -E "^  (CE|AL|PI) |falhou|^(CE|AL|PI) 20" || true

depois="$(find $(printf "$CACHE/%s " $UFS) -name '[0-9]*.json.gz' 2>/dev/null | sort | xargs -r sha256sum | sha256sum)"
if [ "$antes" = "$depois" ]; then
  echo "nenhum mês novo em CE, AL e PI"
  exit 0
fi
for uf in $UFS; do
  tar --exclude='._*' -cf "$TMP/novo-$uf.tar" -C "$CACHE" "$uf"
  mv "$TMP/novo-$uf.tar" "$TMP/estados-$uf.tar"
done
if [ "$ENVIAR" != 1 ]; then
  echo "mês novo, mas ENVIAR=0: nada foi para o release"
  exit 0
fi
gh release upload "$RELEASE" $(printf "$TMP/estados-%s.tar " $UFS) --clobber -R "$REPO"
echo "cache de CE, AL e PI enviado ao release $RELEASE"
