#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotina de monitoramento contínuo do acervo (clipping diário).

Pipeline: COLETA -> DEDUPLICAÇÃO -> CLASSIFICAÇÃO (tema/território)
          -> PUBLICAÇÃO NO CLIPPING (/clipping/) + FILA DE VALIDAÇÃO.

Duas saídas distintas:

1. data/monitoramento/clipping.json — menções do dia na imprensa e em
   fontes oficiais. Publicadas automaticamente na página /clipping/ como
   MENÇÕES (com link para a fonte original), claramente separadas dos
   registros verificados do acervo.

2. data/monitoramento/fila.json — itens provenientes de fontes oficiais
   ou institucionais, candidatos a novos REGISTROS do acervo. Nada vira
   registro sem validação curatorial (fonte, tipo de atuação, evidência).

Consultas monitoradas (Google News RSS, cobre imprensa nacional e regional):
  * "Walter Ihoshi"
  * "Walter Iihoshi"  (grafias do nome civil)
  * "Walter Shindi"

A rotina é tolerante a falhas de rede (avisa e sai 0) para não quebrar o
build diário do GitHub Actions.
"""
import hashlib
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime
from email.utils import parsedate_to_datetime

try:
    from zoneinfo import ZoneInfo
    FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")
except Exception:  # noqa: BLE001
    FUSO_BRASILIA = None

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_MON = os.path.join(RAIZ, "data", "monitoramento")
ARQ_FILA = os.path.join(DIR_MON, "fila.json")
ARQ_VISTOS = os.path.join(DIR_MON, "vistos.json")
ARQ_CLIPPING = os.path.join(DIR_MON, "clipping.json")

CONSULTAS = ['"Walter Ihoshi"', '"Walter Iihoshi"', '"Walter Shindi"']
RSS_BASE = "https://news.google.com/rss/search?q=%s&hl=pt-BR&gl=BR&ceid=BR:pt-419"

DOMINIOS_OFICIAIS = (
    "camara.leg.br", "gov.br", "sp.gov.br", "jucesp.sp.gov.br", "alesp.sp.gov.br",
    "tse.jus.br", "planalto.gov.br", "senado.leg.br", "câmara.leg.br",
)
DOMINIOS_INSTITUCIONAIS = ("bunkyo.org.br", "psd.org.br", "facesp.org.br", "santacasamarilia.com.br")

CHAVES_TEMAS = {
    "jucesp": "desburocratizacao", "junta comercial": "desburocratizacao",
    "cadastro positivo": "cadastro-positivo", "crédito": "credito", "credito": "credito",
    "micro e pequena": "micro-e-pequenas-empresas", "simples nacional": "micro-e-pequenas-empresas",
    "pequenos negócios": "micro-e-pequenas-empresas", "pequenas empresas": "micro-e-pequenas-empresas",
    "saúde": "saude", "saude": "saude", "hospital": "saude", "remédio": "saude", "remedio": "saude",
    "medicamento": "saude", "oncol": "saude",
    "convênio": "convenios", "convenio": "convenios", "convênios": "convenios",
    "japão": "relacoes-brasil-japao", "japao": "relacoes-brasil-japao", "nikkei": "comunidade-nikkei",
    "imigração japonesa": "comunidade-nikkei", "imigracao japonesa": "comunidade-nikkei",
    "japan fest": "comunidade-nikkei", "bunkyo": "comunidade-nikkei",
    "marília": None, "marilia": None,  # município apenas
    "empreendedor": "empreendedorismo", "empresa": "empreendedorismo", "abertura de empresas": "empreendedorismo",
    "segurança": "seguranca", "seguranca": "seguranca", "educação": "educacao", "educacao": "educacao",
    "instituto federal": "educacao",
}
CHAVES_MUNICIPIOS = {
    "marília": "marilia", "marilia": "marilia", "assis": "assis", "suzano": "suzano",
    "registro": "registro", "cafelândia": "cafelandia", "cafelandia": "cafelandia",
    "são paulo": "sao-paulo", "sao paulo": "sao-paulo",
}

MAX_ITENS = 500
MAX_DIAS = 90


def dominio_da(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower() if m else ""


def nivel_por_dominio(url):
    d = dominio_da(url)
    if not d:
        return 50
    if any(d.endswith(x) for x in DOMINIOS_OFICIAIS):
        return 90
    if any(d.endswith(x) for x in DOMINIOS_INSTITUCIONAIS):
        return 80
    if "news.google" in d:
        return 60  # agregador; nível definitivo vem do veículo de destino
    return 60


def classificar(texto):
    t = (texto or "").lower()
    tema = None
    for chave, valor in CHAVES_TEMAS.items():
        if chave in t and valor:
            tema = valor
            break
    municipio = None
    for chave, valor in CHAVES_MUNICIPIOS.items():
        if chave in t:
            municipio = valor
            break
    return tema, municipio


def data_do_item(pubdate):
    try:
        dt = parsedate_to_datetime(pubdate)
        if FUSO_BRASILIA and dt.tzinfo:
            dt = dt.astimezone(FUSO_BRASILIA)
        elif FUSO_BRASILIA:
            dt = dt.replace(tzinfo=FUSO_BRASILIA)
        return dt.date().isoformat()
    except Exception:  # noqa: BLE001
        return date.today().isoformat()


def carregar_json(caminho, padrao):
    if os.path.exists(caminho):
        try:
            with open(caminho, encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # noqa: BLE001
            return padrao
    return padrao


def coletar():
    """Coleta itens de todas as consultas; devolve lista de menções."""
    itens = []
    for consulta in CONSULTAS:
        url = RSS_BASE % urllib.parse.quote(consulta)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "acervo-walter-ihoshi/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                arvore = ET.fromstring(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print("AVISO: consulta indisponível neste ambiente (%s): %s" % (consulta, e))
            continue
        for item in arvore.iter("item"):
            guid = (item.findtext("guid") or item.findtext("link") or "").strip()
            titulo = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            if not guid or not titulo:
                continue
            fonte = (item.findtext("source") or "").strip() or dominio_da(link) or "veículo não identificado"
            tema, municipio = classificar(titulo)
            nivel = nivel_por_dominio(link)
            # no agregador Google News o nível real é do veículo; usa 60 até validação
            itens.append({
                "id": "clip-" + re.sub(r"[^a-z0-9]", "", hashlib_md5(guid))[:16],
                "data": data_do_item(item.findtext("pubDate") or ""),
                "titulo": titulo,
                "link": link,
                "fonte": fonte,
                "fonte_nivel": nivel,
                "tema_proposto": tema,
                "municipio_proposto": municipio,
                "coletado_em": date.today().isoformat(),
            })
    return itens


def hashlib_md5(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def main():
    fila = carregar_json(ARQ_FILA, {"fila": []})
    vistos = carregar_json(ARQ_VISTOS, {"guids": []})
    clipping = carregar_json(ARQ_CLIPPING, {"atualizado_em": None, "itens": []})

    conhecidos = set(vistos.get("guids", []))
    por_id = {i["id"]: i for i in clipping.get("itens", [])}

    novos = coletar()
    ineditos = []
    vistos_novos = []
    for item in novos:
        chave = item["id"]
        if chave in conhecidos or chave in por_id:
            continue
        ineditos.append(item)
        vistos_novos.append(chave)

    if ineditos:
        por_id.update({i["id"]: i for i in ineditos})
        clipping["itens"] = sorted(por_id.values(), key=lambda x: (x.get("data", ""), x.get("titulo", "")), reverse=True)
        # mantém janela de dias e limite de itens
        corte = date.today().toordinal() - MAX_DIAS
        clipping["itens"] = [i for i in clipping["itens"]
                             if date.fromisoformat(i["data"][:10]).toordinal() >= corte][-MAX_ITENS:]
        clipping["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
        os.makedirs(DIR_MON, exist_ok=True)
        with open(ARQ_CLIPPING, "w", encoding="utf-8") as f:
            json.dump(clipping, f, ensure_ascii=False, indent=1)
        with open(ARQ_VISTOS, "w", encoding="utf-8") as f:
            json.dump({"guids": sorted(set(vistos.get("guids", [])) | set(vistos_novos))[-8000:]}, f, ensure_ascii=False, indent=1)

        # candidatos a registro do acervo: apenas fontes oficiais/institucionais
        for item in ineditos:
            d = dominio_da(item["link"])
            oficial = any(d.endswith(x) for x in DOMINIOS_OFICIAIS + DOMINIOS_INSTITUCIONAIS)
            if oficial:
                fila.setdefault("fila", []).append({
                    "id": "mon-%s" % item["id"],
                    "status": "aguardando validação",
                    "titulo": item["titulo"],
                    "fonte_url": item["link"],
                    "fonte_nivel_proposto": item["fonte_nivel"],
                    "tema_proposto": item["tema_proposto"],
                    "municipio_proposto": item["municipio_proposto"],
                    "tipo_atuacao_proposto": "A CLASSIFICAR",
                    "notas": "Coletado automaticamente. Validar fonte, tipo de atuação e resultado antes de "
                             "transformar em registro do acervo.",
                })
        with open(ARQ_FILA, "w", encoding="utf-8") as f:
            json.dump(fila, f, ensure_ascii=False, indent=1)

        print("Clipping: %d menções inéditas incorporadas (%s). Total: %d." %
              (len(ineditos), date.today().isoformat(), len(clipping["itens"])))
        oficiais = sum(1 for i in ineditos if any(dominio_da(i["link"]).endswith(x)
                                                  for x in DOMINIOS_OFICIAIS + DOMINIOS_INSTITUCIONAIS))
        print("Fila de validação: %d candidato(s) de fonte oficial/institucional." % oficiais)
    else:
        clipping["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
        os.makedirs(DIR_MON, exist_ok=True)
        with open(ARQ_CLIPPING, "w", encoding="utf-8") as f:
            json.dump(clipping, f, ensure_ascii=False, indent=1)
        print("Nenhuma menção inédita em %s." % date.today().isoformat())
    return 0


if __name__ == "__main__":
    import urllib.parse  # noqa: F401  (usado em coletar)
    sys.exit(main())
