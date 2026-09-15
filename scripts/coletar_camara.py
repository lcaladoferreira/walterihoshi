#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coleta dados oficiais da Câmara dos Deputados para o acervo.

Baixa as proposições de autoria de Walter Ihoshi (id 141560) da API de
Dados Abertos e salva em data/bruto/proposicoes_camara.json, para uso na
curadoria (o site consome apenas dados validados em data/, nunca o bruto).

Uso:
    python3 scripts/coletar_camara.py [--paginas N]

A rede do ambiente pode restringir acessos diretos; em caso de falha o
script registra o erro e sai sem quebrar rotinas de build (exit 0).
"""
import argparse
import json
import os
import sys
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "data", "bruto", "proposicoes_camara.json")
API = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
ID_DEPUTADO = 141560  # Walter Ihoshi


def baixar(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "acervo-walter-ihoshi/1.0 (coleta pública de dados parlamentares)",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paginas", type=int, default=6, help="número de páginas de 100 itens")
    args = parser.parse_args()

    propostas = []
    url = ("%s?idDeputadoAutor=%d&itens=100&ordenarPor=id&ordem=ASC" % (API, ID_DEPUTADO))
    paginas = 0
    try:
        while url and paginas < args.paginas:
            dados = baixar(url)
            propostas.extend(dados.get("dados", []))
            links = {l.get("rel"): l.get("href") for l in dados.get("links", [])}
            url = links.get("next")
            paginas += 1
    except Exception as e:  # noqa: BLE001
        print("AVISO: não foi possível acessar a API da Câmara neste ambiente (%s)." % e)
        print("A coleta é opcional para o build; os dados curados em data/ permanecem válidos.")
        return 0

    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    with open(DESTINO, "w", encoding="utf-8") as f:
        json.dump({"coletado_em": __import__("datetime").date.today().isoformat(),
                   "total": len(propostas), "proposicoes": propostas}, f, ensure_ascii=False, indent=1)
    print("Coletadas %d proposições de autoria (id %d) -> %s" % (len(propostas), ID_DEPUTADO, DESTINO))

    # resumo por tipo, para conferência da curadoria
    tipos = {}
    for p in propostas:
        tipos[p.get("siglaTipo", "?")] = tipos.get(p.get("siglaTipo", "?"), 0) + 1
    print("Resumo por tipo:", json.dumps(tipos, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
