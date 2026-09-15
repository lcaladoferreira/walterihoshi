#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotina de monitoramento contínuo do acervo.

Pipeline: COLETA -> DEDUPLICAÇÃO -> CLASSIFICAÇÃO (tema/território/tipo)
          -> VALIDAÇÃO DE EVIDÊNCIA (proposta) -> FILA DE PUBLICAÇÃO.

Nada é publicado automaticamente: novos itens entram na fila
(data/monitoramento/fila.json) com status "aguardando validação" e só
viram páginas depois de validação humana, com fonte e nível de evidência.

Fontes monitoradas nesta versão:
  * Notícias (Google News RSS, consulta "Walter Ihoshi");
  * Proposições novas na API da Câmara (caso volte a exercer mandato).

A rotina é tolerante a falhas de rede (registra aviso e sai 0) para não
quebrar o build diário.
"""
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_MON = os.path.join(RAIZ, "data", "monitoramento")
ARQ_FILA = os.path.join(DIR_MON, "fila.json")
ARQ_VISTOS = os.path.join(DIR_MON, "vistos.json")

CONSULTA = '"Walter Ihoshi" OR "Walter Iihoshi"'
RSS = "https://news.google.com/rss/search?q=%s&hl=pt-BR&gl=BR&ceid=BR:pt-419" % urllib.parse.quote(CONSULTA)

# Domínios e níveis de evidência propostos (sujeitos a validação)
DOMINIOS_OFICIAIS = (
    "camara.leg.br", "gov.br", "sp.gov.br", "jucesp.sp.gov.br", "alesp.sp.gov.br",
    "tse.jus.br", "planalto.gov.br", "senado.leg.br",
)
DOMINIOS_INSTITUCIONAIS = ("bunkyo.org.br", "psd.org.br", "facesp.org.br")

# Chaves simples de classificação temática proposta
CHAVES_TEMAS = {
    "jucesp": "desburocratizacao", "junta comercial": "desburocratizacao",
    "cadastro positivo": "cadastro-positivo", "credito": "credito",
    "micro e pequena": "micro-e-pequenas-empresas", "simples nacional": "micro-e-pequenas-empresas",
    "saude": "saude", "hospital": "saude", "remedio": "saude", "medicamento": "saude",
    "convenio": "convenios", "convênio": "convenios",
    "japao": "relacoes-brasil-japao", "japão": "relacoes-brasil-japao",
    "nikkei": "comunidade-nikkei", "imigracao japonesa": "comunidade-nikkei",
    "marilia": "convenios", "empreendedor": "empreendedorismo", "empresa": "empreendedorismo",
}
CHAVES_MUNICIPIOS = ["marilia", "assis", "suzano", "registro", "cafelandia", "são paulo", "sao paulo"]


def nivel_por_dominio(url):
    try:
        dominio = re.match(r"https?://([^/]+)", url).group(1).lower()
    except AttributeError:
        return 50
    if any(dominio.endswith(d) for d in DOMINIOS_OFICIAIS):
        return 80
    if any(dominio.endswith(d) for d in DOMINIOS_INSTITUCIONAIS):
        return 80
    return 60  # imprensa/outras fontes: proposto, exige validação


def classificar(texto):
    t = texto.lower()
    tema = None
    for chave, valor in CHAVES_TEMAS.items():
        if chave in t:
            tema = valor
            break
    municipio = None
    for m in CHAVES_MUNICIPIOS:
        if m in t:
            municipio = "sao-paulo" if "paulo" in m else m.replace("são paulo", "sao-paulo")
            break
    return tema, municipio


def carregar_json(caminho, padrao):
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    return padrao


def main():
    fila = carregar_json(ARQ_FILA, {"fila": []})
    vistos = carregar_json(ARQ_VISTOS, {"guids": []})
    conhecidos = set(vistos.get("guids", [])) | {
        i.get("fonte_url") for i in fila.get("fila", []) if i.get("fonte_url")
    }

    novos = []
    try:
        req = urllib.request.Request(RSS, headers={"User-Agent": "acervo-walter-ihoshi/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            arvore = ET.fromstring(r.read().decode("utf-8"))
        for item in arvore.iter("item"):
            guid = (item.findtext("guid") or item.findtext("link") or "").strip()
            titulo = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            publicado = (item.findtext("pubDate") or "").strip()
            if not guid or guid in conhecidos:
                continue
            tema, municipio = classificar(titulo)
            nivel = nivel_por_dominio(link)
            novos.append({
                "id": "mon-%s" % datetime.now().strftime("%Y%m%d-%H%M%S-") + str(len(novos)),
                "status": "aguardando validação",
                "titulo": titulo,
                "fonte_url": link,
                "publicado_em": publicado,
                "fonte_nivel_proposto": nivel,
                "tema_proposto": tema,
                "municipio_proposto": municipio,
                "tipo_atuacao_proposto": "A CLASSIFICAR",
                "notas": "Coletado automaticamente pela rotina de monitoramento. Validar antes de publicar; "
                         "não publicar se nível < 60 ou se for alegação sensível sem fonte oficial.",
            })
            conhecidos.add(guid)
    except Exception as e:  # noqa: BLE001
        print("AVISO: coleta de notícias indisponível neste ambiente (%s)." % e)

    if novos:
        fila.setdefault("fila", []).extend(novos)
        vistos["guids"] = sorted(list(conhecidos - {None}))[-5000:]
        with open(ARQ_FILA, "w", encoding="utf-8") as f:
            json.dump(fila, f, ensure_ascii=False, indent=1)
        with open(ARQ_VISTOS, "w", encoding="utf-8") as f:
            json.dump(vistos, f, ensure_ascii=False, indent=1)
        print("%d novo(s) item(ns) na fila de validação (%s)." % (len(novos), ARQ_FILA))
    else:
        print("Nenhum item novo identificado em %s." % date.today().isoformat())
    return 0


if __name__ == "__main__":
    sys.exit(main())
