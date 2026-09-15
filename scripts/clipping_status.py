#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exibe no HTML do clipping a data/hora real da última coleta em Brasília."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    BRASILIA = ZoneInfo("America/Sao_Paulo")
except Exception:  # noqa: BLE001
    BRASILIA = timezone.utc

RAIZ = Path(__file__).resolve().parent.parent
CLIPPING_JSON = RAIZ / "data" / "monitoramento" / "clipping.json"
CLIPPING_HTML = RAIZ / "public" / "clipping" / "index.html"


def formatar_timestamp(valor):
    if not valor:
        return None
    dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    # O GitHub Actions roda em UTC; timestamps antigos do monitorar.py eram
    # gravados sem offset, portanto são interpretados como UTC antes da conversão.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(BRASILIA)
    return dt.strftime("%d/%m/%Y às %H:%M")


def main():
    if not CLIPPING_JSON.exists() or not CLIPPING_HTML.exists():
        print("Clipping status: arquivos ainda não existem; nada a fazer.")
        return 0

    dados = json.loads(CLIPPING_JSON.read_text(encoding="utf-8"))
    exibicao = formatar_timestamp(dados.get("atualizado_em"))
    if not exibicao:
        print("Clipping status: atualizado_em ausente; nada a fazer.")
        return 0

    html = CLIPPING_HTML.read_text(encoding="utf-8")
    novo_bloco = (
        '<p class="clipping-atualizado" role="status">'
        'Última atualização do clipping: <strong>%s</strong> (Brasília). '
        'Atualização automática: 08:17 e 20:17.</p>' % exibicao
    )

    # Primeiro substitui o texto legado em qualquer contêiner.
    padrao_texto = re.compile(r'Última coleta:\s*<strong>.*?</strong>\.', re.I | re.S)
    if padrao_texto.search(html):
        html = padrao_texto.sub(
            'Última atualização do clipping: <strong>%s</strong> (Brasília). Atualização automática: 08:17 e 20:17.' % exibicao,
            html,
            count=1,
        )
    elif "Última atualização do clipping:" not in html:
        # Fallback: insere imediatamente depois do H1 do clipping.
        html = re.sub(
            r'(<h1[^>]*>.*?</h1>)',
            r'\1' + novo_bloco,
            html,
            count=1,
            flags=re.I | re.S,
        )

    CLIPPING_HTML.write_text(html, encoding="utf-8")
    if "Última atualização do clipping:" not in html or "08:17 e 20:17" not in html:
        raise RuntimeError("Indicador de atualização do clipping não foi aplicado")

    print("Clipping status OK: %s (Brasília)." % exibicao)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
