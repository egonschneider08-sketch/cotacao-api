"""CotaFácil — landing page + painel de cotações em Streamlit.

Execução:  streamlit run app.py
Dados:     AwesomeAPI (https://docs.awesomeapi.com.br)
Tema:      .streamlit/config.toml
"""

import base64
import random
import re
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

API = "https://economia.awesomeapi.com.br/json"

PARES = {
    "USD-BRL": {"nome": "Dólar Americano", "sigla": "USD", "tipo": "Moedas"},
    "EUR-BRL": {"nome": "Euro", "sigla": "EUR", "tipo": "Moedas"},
    "GBP-BRL": {"nome": "Libra Esterlina", "sigla": "GBP", "tipo": "Moedas"},
    "ARS-BRL": {"nome": "Peso Argentino", "sigla": "ARS", "tipo": "Moedas"},
    "BTC-BRL": {"nome": "Bitcoin", "sigla": "BTC", "tipo": "Cripto"},
    "ETH-BRL": {"nome": "Ethereum", "sigla": "ETH", "tipo": "Cripto"},
}
FILTROS = ["Todas", "Moedas", "Cripto"]
PERIODOS = {"7 dias": 7, "30 dias": 30, "90 dias": 90, "6 meses": 180}
PADRAO_PAR = re.compile(r"[A-Z]{3,5}-[A-Z]{3}")

st.set_page_config(page_title="CotaFácil | Cotações em tempo real", page_icon="💱", layout="wide")

# ---------------------------------------------------------------- Estilo
st.markdown(
    """
    <style>
    header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], footer { display: none !important; }
    .block-container { max-width: 1120px; padding: 1rem 1rem 3rem; }
    html { scroll-behavior: smooth; }

    /* fundo da página: degradê de verde claro para branco (acompanha a rolagem) */
    .stApp { background: linear-gradient(180deg, #C9E9DA 0%, #FFFFFF 100%) fixed !important; }
    [data-testid="stAppViewContainer"] { background: transparent !important; }
    [data-testid="stMain"] {
        background: linear-gradient(180deg, #C9E9DA 0%, #E1F3EA 18%, #F4FAF7 45%, #FFFFFF 70%) local !important;
    }

    /* nav */
    .cf-nav { display: flex; align-items: center; justify-content: space-between; background: #fff;
        border: 1px solid #E3E7EC; border-radius: 12px; overflow: hidden; height: 60px; }
    .cf-logo { display: flex; align-items: center; height: 100%; padding: 0 1.4rem; background: #0F6E56;
        color: #fff !important; font-weight: 800; font-size: 1.15rem; letter-spacing: -.01em; text-decoration: none !important; }
    .cf-nav-note { margin-right: 1.5rem; color: #5B6675; font-size: .9rem; }

    /* abas: barra em pílula, opções de mesmo tamanho, centralizadas e com folga.
       Cobre o componente novo do Streamlit (react-aria) e o antigo (BaseWeb) pelos papéis ARIA. */
    [data-testid="stTabs"] { margin-top: .1rem; }
    [role="tablist"] { gap: 6px; background: #fff !important; border: 1px solid #E3E7EC; border-radius: 16px; padding: 7px;
        box-shadow: 0 10px 28px -18px rgba(7,59,46,.4); overflow-x: auto; overflow-y: clip; scrollbar-width: none; }
    [role="tablist"]::-webkit-scrollbar { display: none; }
    [role="tablist"]::after { display: none !important; }
    [role="tab"] { flex: 1 1 0 !important; min-width: 120px; height: 50px !important; padding: 0 1.2rem !important;
        display: flex !important; align-items: center; justify-content: center !important; gap: .5rem;
        border-radius: 11px !important; background: transparent !important; color: #5B6675 !important;
        position: relative; z-index: 1; isolation: isolate; transition: background-color .2s ease, color .2s ease; }
    [role="tab"] p { color: inherit !important; margin: 0 !important; font-weight: 600; font-size: .98rem; white-space: nowrap; text-align: center; }
    [role="tab"]:hover { background: rgba(15,110,86,.07) !important; color: #073B2E !important; }
    [role="tab"][aria-selected="true"] { color: #073B2E !important; }
    [role="tab"][aria-selected="true"] p { font-weight: 700; }
    /* o destaque da aba ativa vira uma pílula que desliza de uma aba para a outra */
    [role="tab"] .react-aria-SelectionIndicator { top: 0 !important; left: 0 !important; width: 100% !important;
        height: 100% !important; border-radius: 11px !important; z-index: -1; }
    [role="tab"][aria-selected="true"] .react-aria-SelectionIndicator { background-color: #DDF0E8 !important; }
    [data-baseweb="tab-highlight"] { background: #DDF0E8 !important; height: 100% !important; top: 0 !important;
        border-radius: 11px; z-index: 0; }
    [data-baseweb="tab-border"] { display: none; }
    [role="tabpanel"] { padding-top: 1.8rem !important; }
    @media (prefers-reduced-motion: no-preference) {
        [role="tabpanel"] { animation: cf-surge .45s cubic-bezier(.2,.8,.2,1) both; }
        @keyframes cf-surge { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
    }
    @media (max-width: 640px) {
        [role="tab"] { min-width: 104px; padding: 0 .9rem !important; }
    }
    /* iframe auxiliar (idioma da página) não deve ocupar espaço */
    [data-testid="stElementContainer"]:has(iframe[height="0"]) { display: none; }

    /* hero */
    .cf-hero { background: #073B2E; border-radius: 18px; overflow: hidden; color: #fff; margin-top: .5rem; }
    .cf-hero-top { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(0, .85fr); align-items: center;
        gap: 1rem; padding: clamp(2.2rem, 6vw, 4.2rem) clamp(1.4rem, 4vw, 3rem) 2.6rem; position: relative; z-index: 2; }
    .cf-art { display: flex; justify-content: center; }
    .cf-art img { width: min(100%, 340px); height: auto; display: block; }
    .cf-hero h1 { color: #fff; font-size: clamp(2.1rem, 5vw, 3.6rem); line-height: 1.05; letter-spacing: -.03em;
        font-weight: 800; max-width: 15ch; margin: 0; padding: 0; }
    .cf-hero p.lead { margin: 1rem 0 0; max-width: 46ch; font-size: 1.1rem; color: rgba(255,255,255,.82); }
    .cf-actions { margin-top: 1.6rem; display: flex; flex-wrap: wrap; gap: .75rem; }
    .cf-hint { display: inline-block; margin: 1.5rem 0 0; padding: .5rem 1rem; border: 1px solid rgba(255,255,255,.3);
        border-radius: 999px; font-size: .92rem; color: rgba(255,255,255,.88); }
    .cf-btn { display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: .55rem 1.4rem;
        border-radius: 8px; border: 2px solid transparent; font-weight: 600; text-decoration: none !important; }
    .cf-btn.mint { background: #8FE3C4; color: #073B2E !important; }
    .cf-btn.mint:hover { background: #fff; }
    .cf-btn.ghost { border-color: rgba(255,255,255,.55); color: #fff !important; }
    .cf-btn.ghost:hover { background: rgba(255,255,255,.12); border-color: #fff; }

    /* skyline: cada barra é um dia do dólar (só HTML/CSS, sem SVG inline) */
    .cf-sky { position: relative; height: clamp(180px, 24vw, 260px); }
    .cf-sky .nota { position: absolute; left: clamp(1.4rem, 4vw, 3rem); top: -2rem; z-index: 2; margin: 0;
        font-size: .85rem; color: rgba(255,255,255,.78); max-width: 60ch; }
    .cf-back { position: absolute; inset: 0; background-repeat: no-repeat; background-position: bottom; background-size: 100% 100%; }
    .cf-bars { position: absolute; inset: 0; display: flex; align-items: flex-end; gap: 6px; padding: 0 clamp(1rem, 3vw, 2rem); }
    .cf-bars .b { flex: 1; min-width: 0; background: #2A9478; border-radius: 4px 4px 0 0;
        transform-origin: 50% 100%; transition: background-color .12s; }
    .cf-bars .b:hover { background: #4DBF9F; }
    .cf-bars .b.hoje { background: #8FE3C4; }
    .cf-bars .b.hoje:hover { background: #fff; }
    @media (prefers-reduced-motion: no-preference) {
        .cf-bars .b { animation: cf-sobe .7s cubic-bezier(.2,.8,.2,1) both; }
        @keyframes cf-sobe { from { transform: scaleY(0); } to { transform: scaleY(1); } }
    }

    /* destaques */
    .cf-features { position: relative; z-index: 3; margin: -3.5rem 1.2rem 0; display: grid; grid-template-columns: repeat(3, 1fr);
        background: #fff; border: 1px solid #E3E7EC; border-radius: 14px; box-shadow: 0 18px 40px -18px rgba(7,59,46,.35); }
    .cf-feature { padding: 1.7rem 1.6rem 1.8rem; }
    .cf-feature + .cf-feature { border-left: 1px solid #E3E7EC; }
    .cf-feature img { width: 38px; height: 38px; display: block; margin-bottom: .9rem; }
    .cf-feature h2 { font-size: 1.05rem; letter-spacing: -.01em; margin: 0 0 .35rem; padding: 0; color: #1B2430; }
    .cf-feature p { margin: 0; color: #5B6675; font-size: .95rem; max-width: 34ch; }

    /* destaques da aba Início */
    .cf-quick { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
    .cf-q { background: #fff; border: 1px solid #E3E7EC; border-radius: 12px; padding: 1.1rem 1.25rem; display: flex; flex-direction: column; gap: .15rem; }
    .cf-q-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: .55rem; }
    .cf-q b { color: #1B2430; }
    .cf-q-price { font-size: 1.6rem; font-weight: 800; letter-spacing: -.02em; line-height: 1.15; color: #1B2430; font-variant-numeric: tabular-nums; }
    .cf-q small { color: #5B6675; font-variant-numeric: tabular-nums; }

    /* seções */
    .cf-sec { margin-top: .4rem; }
    .cf-sec + .cf-sec { margin-top: 2rem; }
    .cf-sec h2 { font-size: clamp(1.5rem, 3vw, 2rem); letter-spacing: -.02em; line-height: 1.15; margin: 0; padding: 0; color: #1B2430; }
    .cf-sec p { margin: .35rem 0 0; color: #5B6675; max-width: 52ch; }

    /* tabela de cotações */
    .cf-ledger { background: #fff; border: 1px solid #E3E7EC; border-radius: 12px; overflow: hidden; }
    .cf-row { display: grid; grid-template-columns: minmax(0, 2.2fr) 1fr 1fr 1fr; gap: 1rem; align-items: center;
        padding: .95rem 1.4rem; border-top: 1px solid #E3E7EC; }
    .cf-row.head { border-top: 0; background: #E3F1ED; color: #5B6675; font-size: .85rem; font-weight: 600; padding-block: .65rem; }
    .cf-row > :not(:first-child) { text-align: right; }
    .cf-coin { display: flex; align-items: center; gap: .85rem; min-width: 0; }
    .cf-badge { flex: none; width: 42px; height: 42px; border-radius: 10px; display: grid; place-items: center;
        background: #E3F1ED; color: #073B2E; font-weight: 800; font-size: .8rem; }
    .cf-coin b { display: block; line-height: 1.25; color: #1B2430; }
    .cf-coin small { color: #5B6675; font-size: .85rem; }
    .cf-price { font-weight: 700; font-size: 1.05rem; font-variant-numeric: tabular-nums; }
    .cf-sell { color: #5B6675; font-variant-numeric: tabular-nums; }
    .cf-chg { font-weight: 700; font-variant-numeric: tabular-nums; }
    .cf-chg.up { color: #0B6B45; } .cf-chg.down { color: #B42318; } .cf-chg.flat { color: #5B6675; }

    /* resultado do conversor */
    .cf-out { background: #0F6E56; color: #fff; border-radius: 12px; padding: 1.8rem; min-height: 100%;
        display: flex; flex-direction: column; justify-content: center; gap: .5rem; }
    .cf-out .lbl { color: rgba(255,255,255,.82); }
    .cf-out .big { font-size: clamp(1.8rem, 3.6vw, 2.6rem); font-weight: 800; letter-spacing: -.02em; line-height: 1.1; overflow-wrap: anywhere; }
    .cf-out .rate { color: rgba(255,255,255,.82); font-size: .9rem; margin-top: .5rem; }

    .cf-foot { margin-top: 3rem; padding-top: 1.2rem; border-top: 1px solid #E3E7EC; display: flex; flex-wrap: wrap;
        justify-content: space-between; gap: .6rem; color: #5B6675; font-size: .9rem; }
    .cf-foot b { color: #1B2430; }

    div.stButton > button { border-radius: 8px; font-weight: 500; }

    @media (max-width: 860px) {
        .cf-features { grid-template-columns: 1fr; margin-top: -2.5rem; }
        .cf-feature + .cf-feature { border-left: 0; border-top: 1px solid #E3E7EC; }
        .cf-quick { grid-template-columns: 1fr; }
        .cf-hero-top { grid-template-columns: 1fr; }
        .cf-art { order: -1; }
        .cf-art img { width: min(60%, 220px); }
    }
    @media (max-width: 640px) {
        .cf-art { display: none; }
        .cf-bars { gap: 3px; }
        .cf-nav-note { display: none; }
        .cf-row { grid-template-columns: minmax(0, 1fr) auto auto; gap: .75rem; padding-inline: 1rem; }
        .cf-sell { display: none; }
        .cf-badge { width: 38px; height: 38px; }
        .cf-btn { flex: 1 1 100%; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------ Dados
def _tratar_resposta(resposta: requests.Response):
    """Converte a resposta da API em (dados, erro)."""
    if resposta.status_code == 200:
        return resposta.json(), None

    if resposta.status_code == 404:
        try:
            erro = resposta.json()
            return None, f"Erro {erro.get('code')} ({erro.get('status')}): {erro.get('message')}"
        except ValueError:
            return None, "Moeda não encontrada. Confira o código e tente de novo."

    return None, f"A API respondeu com status {resposta.status_code}. Tente novamente em instantes."


@st.cache_data(ttl=30, show_spinner=False)
def consultar_moedas(pares: tuple[str, ...]):
    """Cotação atual de um ou mais pares. Retorna (dados, erro)."""
    try:
        resposta = requests.get(f"{API}/last/{','.join(pares)}", timeout=10)
    except requests.RequestException:
        return None, "Não foi possível conectar à API. Verifique sua internet e tente de novo."
    return _tratar_resposta(resposta)


@st.cache_data(ttl=300, show_spinner=False)
def consultar_historico(par: str, dias: int):
    """Histórico diário do par. Retorna (DataFrame, erro)."""
    try:
        resposta = requests.get(f"{API}/daily/{par}/{dias}", timeout=10)
    except requests.RequestException:
        return None, "Não foi possível carregar o histórico."

    dados, erro = _tratar_resposta(resposta)
    if erro:
        return None, erro
    if not dados:
        return None, "A API não retornou histórico para este par."

    df = pd.DataFrame(dados)
    df["data"] = pd.to_datetime(df["timestamp"].astype(int), unit="s")
    for coluna in ("bid", "high", "low"):
        df[coluna] = df[coluna].astype(float)
    return df.sort_values("data").reset_index(drop=True), None


# -------------------------------------------------------------- Formatação
def _casas(valor: float) -> int:
    return 2 if abs(valor) >= 1 else 4 if abs(valor) >= 0.01 else 6


def _br(texto: str) -> str:
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_reais(valor: float) -> str:
    return "R$ " + _br(f"{valor:,.{_casas(valor)}f}")


def formatar_numero(valor: float, casas: int = 2) -> str:
    return _br(f"{valor:,.{casas}f}")


def chave_api(par: str) -> str:
    return par.replace("-", "")


# ------------------------------------------------------------------- Hero
# O Streamlit remove <svg> inline do HTML. Por isso o skyline usa <div>s e os ícones
# viram imagens (data URI). As classes "notranslate" evitam que o Chrome traduza o
# texto da página (o Streamlit declara a página como inglês).
def icone_uri(corpo: str) -> str:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" fill="none" stroke="#0F6E56" '
        f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">{corpo}</svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


ICONES = {
    "historico": icone_uri(
        '<path d="M6 34h28"/><rect x="9" y="20" width="6" height="14" rx="1"/>'
        '<rect x="17" y="12" width="6" height="22" rx="1"/><rect x="25" y="6" width="6" height="28" rx="1"/>'
    ),
    "tempo": icone_uri('<circle cx="20" cy="20" r="14"/><path d="M20 11v9l6 4"/>'),
    "painel": icone_uri('<path d="M20 6a14 14 0 1 0 14 14H20z"/><path d="M26 4.5A14 14 0 0 1 35.5 14H26z"/>'),
}


@lru_cache(maxsize=1)
def imagem_moedas() -> str:
    """Ilustração das moedas (assets/moedas.png) como data URI; vazio se o arquivo não existir."""
    caminho = Path(__file__).parent / "assets" / "moedas.png"
    if not caminho.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(caminho.read_bytes()).decode()


@lru_cache(maxsize=1)
def fundo_css() -> str:
    """Prédios discretos atrás das barras, como imagem de fundo via CSS."""
    rnd, largura, altura = random.Random(11), 1200, 290
    partes = []
    for n, minimo, maximo, alfa in ((38, 40, 150, 0.05), (26, 70, 210, 0.08)):
        x, passo = -8.0, largura / n
        for _ in range(n):
            w = passo * (0.75 + rnd.random() * 0.7)
            h = minimo + rnd.random() * (maximo - minimo)
            partes.append(
                f'<rect x="{x:.1f}" y="{altura - h:.1f}" width="{w:.1f}" height="{h:.1f}" '
                f'fill="#fff" fill-opacity="{alfa}"/>'
            )
            x += w + 2
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" '
        f'preserveAspectRatio="none">{"".join(partes)}</svg>'
    )
    uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    return f'<style>.cf-back {{ background-image: url("{uri}"); }}</style>'


def serie_dolar():
    """Últimos 30 dias do dólar. Retorna (lista de (data, valor), exemplo?)."""
    historico, erro = consultar_historico("USD-BRL", 30)
    if erro or historico is None or len(historico) < 5:
        rnd, v, hoje = random.Random(5), 5.4, datetime.now()
        serie = []
        for i in range(30):
            v += (rnd.random() - 0.48) * 0.06
            serie.append((hoje - timedelta(days=29 - i), v))
        return serie, True
    return list(zip(historico["data"].dt.to_pydatetime(), historico["bid"])), False


def barras_html(serie) -> tuple[str, float, float]:
    """Cada barra é um dia do dólar; a última (hoje) fica em destaque. O valor aparece ao passar o mouse."""
    n = len(serie)
    valores = [v for _, v in serie]
    minimo, maximo = min(valores), max(valores)
    faixa = (maximo - minimo) or 1
    partes = []
    for i, (dia, v) in enumerate(serie):
        altura = 30 + (v - minimo) / faixa * 58  # de 30% a 88% da altura do skyline
        classe = "b hoje" if i == n - 1 else "b"
        partes.append(
            f'<div class="{classe}" style="height:{altura:.1f}%;animation-delay:{i * 22 + 150}ms" '
            f'title="{dia:%d/%m}: {formatar_reais(v)}"></div>'
        )
    return "".join(partes), minimo, maximo


def secao_hero():
    st.markdown(fundo_css(), unsafe_allow_html=True)

    serie, exemplo = serie_dolar()
    barras, minimo, maximo = barras_html(serie)
    nota = (
        "Sem conexão com a API: exibindo dados de exemplo."
        if exemplo
        else f"Dólar em 30 dias: de {formatar_reais(minimo)} a {formatar_reais(maximo)}. "
        "Passe o mouse sobre uma barra."
    )
    arte = (
        f'<div class="cf-art"><img src="{imagem_moedas()}" alt="Moedas em circulação: iene, euro e dólar"></div>'
        if imagem_moedas()
        else ""
    )
    st.html(
        f"""
        <div id="inicio" class="cf-hero notranslate" translate="no">
          <div class="cf-hero-top">
            <div class="cf-hero-copy">
              <h1>Dólar, euro e cripto sem complicação.</h1>
              <p class="lead">Veja a cotação de agora, compare com os últimos dias e converta valores em segundos.</p>
              <p class="cf-hint">Escolha uma aba acima para começar.</p>
            </div>
            {arte}
          </div>
          <div class="cf-sky">
            <p class="nota">{nota}</p>
            <div class="cf-back"></div>
            <div class="cf-bars" role="img" aria-label="Barras com o valor do dólar em reais nos últimos 30 dias">{barras}</div>
          </div>
        </div>
        <div class="cf-features notranslate" translate="no">
          <article class="cf-feature">
            <img src="{ICONES['historico']}" alt="">
            <h2>Histórico de 7 dias a 6 meses</h2>
            <p>Acompanhe a evolução de cada moeda e veja a média, o mínimo e o máximo do período.</p>
          </article>
          <article class="cf-feature">
            <img src="{ICONES['tempo']}" alt="">
            <h2>Atualização a cada 30 segundos</h2>
            <p>Os valores vêm direto da AwesomeAPI e se renovam sozinhos, sem você precisar recarregar.</p>
          </article>
          <article class="cf-feature">
            <img src="{ICONES['painel']}" alt="">
            <h2>Painel com todas as moedas</h2>
            <p>Compare moedas e criptomoedas lado a lado e baixe a tabela em CSV.</p>
          </article>
        </div>
        """
    )


# ---------------------------------------------------------------- Seções
def cabecalho(id_: str, titulo: str, texto: str):
    st.html(f'<div id="{id_}" class="cf-sec notranslate" translate="no"><h2>{titulo}</h2><p>{texto}</p></div>')


def variacao_fmt(v: float) -> tuple[str, str]:
    """Classe CSS e texto da variação (sinal e seta, para não depender só da cor)."""
    classe = "up" if v > 0 else "down" if v < 0 else "flat"
    marca = "▲ " if v > 0 else "▼ " if v < 0 else ""
    sinal = "+" if v > 0 else "−" if v < 0 else ""
    return classe, f"{marca}{sinal}{abs(v):.2f}%".replace(".", ",")


def card_html(info: dict, d: dict) -> str:
    classe, variacao = variacao_fmt(float(d["pctChange"]))
    return (
        '<div class="cf-q"><div class="cf-q-top">'
        f'<span class="cf-badge">{info["sigla"]}</span><span class="cf-chg {classe}">{variacao}</span></div>'
        f'<b>{info["nome"]}</b><span class="cf-q-price">{formatar_reais(float(d["bid"]))}</span>'
        f'<small>Venda {formatar_reais(float(d["ask"]))}</small></div>'
    )


@st.fragment(run_every=30)
def secao_destaques():
    cabecalho("destaques", "Em destaque agora", "Dólar, euro e Bitcoin, atualizados a cada 30 segundos.")
    pares = ("USD-BRL", "EUR-BRL", "BTC-BRL")
    dados, erro = consultar_moedas(pares)
    if erro:
        st.info(erro)
        return
    cartoes = "".join(card_html(PARES[c], dados[chave_api(c)]) for c in pares if chave_api(c) in dados)
    st.html(f'<div class="cf-quick notranslate" translate="no">{cartoes}</div>')


def linha_html(cod: str, info: dict, d: dict) -> str:
    bid, ask = float(d["bid"]), float(d["ask"])
    classe, variacao = variacao_fmt(float(d["pctChange"]))
    return (
        '<div class="cf-row">'
        f'<div class="cf-coin"><span class="cf-badge">{info["sigla"]}</span>'
        f'<span><b>{info["nome"]}</b><small>{cod}</small></span></div>'
        f'<span class="cf-price">{formatar_reais(bid)}</span>'
        f'<span class="cf-sell">{formatar_reais(ask)}</span>'
        f'<span class="cf-chg {classe}">{variacao}</span>'
        "</div>"
    )


@st.fragment(run_every=30)
def secao_cotacoes():
    """Tabela ao vivo: só este bloco é recarregado a cada 30 segundos."""
    cabecalho("cotacoes", "Cotações agora", "Compra e venda em reais, com a variação do dia.")
    filtro = st.segmented_control(
        "Filtrar por tipo", FILTROS, default="Todas", key="filtro", label_visibility="collapsed"
    ) or "Todas"

    dados, erro = consultar_moedas(tuple(PARES))
    if erro:
        st.error(erro + " A tabela tenta de novo em 30 segundos.")
        return

    linhas = "".join(
        linha_html(cod, info, dados[chave_api(cod)])
        for cod, info in PARES.items()
        if (filtro == "Todas" or info["tipo"] == filtro) and chave_api(cod) in dados
    )
    st.html(
        '<div class="cf-ledger notranslate" translate="no">'
        '<div class="cf-row head"><span>Moeda</span><span>Compra</span><span class="cf-sell">Venda</span><span>Variação</span></div>'
        f"{linhas}</div>"
    )
    st.caption(f"Atualizado às {datetime.now():%H:%M:%S}. Os valores se renovam a cada 30 segundos.")


def escolher_par(chave: str) -> str:
    """Seletor de moeda + campo opcional para outro par (ex.: JPY-BRL)."""
    escolha = st.selectbox(
        "Moeda",
        options=list(PARES),
        format_func=lambda c: f"{PARES[c]['nome']} ({PARES[c]['sigla']})",
        key=f"{chave}_sel",
    )
    outro = st.text_input(
        "Outro par (opcional)",
        placeholder="JPY-BRL",
        help="Formato MOEDA-MOEDA, por exemplo JPY-BRL.",
        key=f"{chave}_outro",
    ).strip().upper()

    if outro and not PADRAO_PAR.fullmatch(outro):
        st.warning("Formato inválido. Use algo como JPY-BRL; usando a moeda selecionada.")
        return escolha
    return outro or escolha


def secao_historico():
    cabecalho("historico", "Histórico", "Veja como a moeda se comportou no período e compare média, mínimo e máximo.")
    col_form, col_dados = st.columns([1, 2.4], gap="large")

    with col_form:
        par = escolher_par("hist")
        periodo = st.segmented_control("Período", list(PERIODOS), default="30 dias", key="hist_periodo") or "30 dias"

    with col_dados:
        dados, erro = consultar_moedas((par,))
        if erro:
            st.error(erro)
            return
        info = dados[chave_api(par)]
        compra, venda = float(info["bid"]), float(info["ask"])

        st.markdown(f"#### {info['name']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Compra", formatar_reais(compra), f"{float(info['pctChange']):+.2f}%")
        c2.metric("Venda", formatar_reais(venda))
        c3.metric("Spread", formatar_reais(venda - compra))

        historico, erro_hist = consultar_historico(par, PERIODOS[periodo])
        if erro_hist:
            st.info(erro_hist)
        else:
            st.line_chart(historico.set_index("data")["bid"], height=260, color="#0F6E56")
            h1, h2, h3 = st.columns(3)
            h1.metric("Média no período", formatar_reais(historico["bid"].mean()))
            h2.metric("Mínimo", formatar_reais(historico["bid"].min()))
            h3.metric("Máximo", formatar_reais(historico["bid"].max()))
        st.caption(f"Última atualização: {info['create_date']}")


def secao_conversor():
    cabecalho("conversor", "Converter valor", "Escolha a moeda, o sentido e o valor. O resultado usa a cotação mais recente.")
    esquerda, direita = st.columns([1.05, 1], gap="medium")

    with esquerda:
        with st.container(border=True):
            par = escolher_par("conv")
            base = par.split("-")[0]
            sentido = st.radio("Sentido", [f"{base} para reais", f"Reais para {base}"], horizontal=True)
            valor = st.number_input("Valor", min_value=0.0, value=100.0, step=10.0, format="%.2f")

    with direita:
        dados, erro = consultar_moedas((par,))
        if erro:
            st.error(erro)
            return
        info = dados[chave_api(par)]
        bid, ask = float(info["bid"]), float(info["ask"])
        cripto = PARES.get(par, {}).get("tipo") == "Cripto"

        if sentido.startswith(base):
            rotulo = f"{formatar_numero(valor)} {base} valem"
            grande = formatar_reais(valor * bid)
            taxa = f"Taxa de compra: {formatar_reais(bid)} por {base}."
        else:
            rotulo = f"R$ {formatar_numero(valor)} compram"
            grande = f"{formatar_numero(valor / ask if ask else 0, 8 if cripto else 4)} {base}"
            taxa = f"Taxa de venda: {formatar_reais(ask)} por {base}."

        st.html(
            f'<div class="cf-out notranslate" translate="no"><span class="lbl">{rotulo}</span><span class="big">{grande}</span>'
            f'<span class="rate">{taxa} Atualizado em {info["create_date"]}.</span></div>'
        )


def secao_painel():
    cabecalho("painel", "Exportar cotações", "Baixe a tabela atual em CSV para usar em planilhas.")
    dados, erro = consultar_moedas(tuple(PARES))
    if erro:
        st.error(erro)
        return
    linhas = [
        {
            "Tipo": info["tipo"],
            "Código": cod,
            "Moeda": info["nome"],
            "Compra (R$)": float(dados[chave_api(cod)]["bid"]),
            "Venda (R$)": float(dados[chave_api(cod)]["ask"]),
            "Variação (%)": float(dados[chave_api(cod)]["pctChange"]),
            "Atualizado": dados[chave_api(cod)]["create_date"],
        }
        for cod, info in PARES.items()
        if chave_api(cod) in dados
    ]
    tabela = pd.DataFrame(linhas)
    st.dataframe(
        tabela,
        hide_index=True,
        width="stretch",
        column_config={
            "Compra (R$)": st.column_config.NumberColumn(format="%.4f"),
            "Venda (R$)": st.column_config.NumberColumn(format="%.4f"),
            "Variação (%)": st.column_config.NumberColumn(format="%+.2f%%"),
        },
    )
    st.download_button(
        "Baixar CSV",
        tabela.to_csv(index=False).encode("utf-8"),
        file_name=f"cotacoes_{datetime.now():%Y%m%d_%H%M}.csv",
        mime="text/csv",
    )


# ------------------------------------------------------------------- Página
def declarar_idioma():
    """O Streamlit declara a página como inglês e o Chrome pode traduzir os rótulos das abas.
    Este script (em um iframe minúsculo) marca a página como pt-BR e "não traduzir".
    É um paliativo: se o Chrome já tiver traduzido, use "Nunca traduzir este site"."""
    script = (
        "<script>try{const d=window.parent.document;d.documentElement.lang='pt-BR';"
        "d.documentElement.setAttribute('translate','no');"
        "if(!d.querySelector('meta[name=google]')){const m=d.createElement('meta');"
        "m.name='google';m.content='notranslate';d.head.appendChild(m);}}catch(e){}</script>"
    )
    try:
        if hasattr(st, "iframe"):  # Streamlit recente
            st.iframe(script, width=1, height=1)
        else:  # versões mais antigas
            import streamlit.components.v1 as components

            components.html(script, height=0)
    except Exception:
        pass


st.html(
    """
    <nav class="cf-nav notranslate" translate="no" aria-label="CotaFácil">
      <span class="cf-logo">CotaFácil</span>
      <span class="cf-nav-note">Dados ao vivo da AwesomeAPI</span>
    </nav>
    """
)

aba_inicio, aba_cotacoes, aba_historico, aba_conversor, aba_exportar = st.tabs(
    [
        ":material/home: Início",
        ":material/show_chart: Cotações",
        ":material/history: Histórico",
        ":material/currency_exchange: Conversor",
        ":material/download: Exportar",
    ]
)

with aba_inicio:
    secao_hero()
    secao_destaques()

with aba_cotacoes:
    secao_cotacoes()

with aba_historico:
    secao_historico()

with aba_conversor:
    secao_conversor()

with aba_exportar:
    secao_painel()

st.html(
    f"""
    <div class="cf-foot notranslate" translate="no">
      <span><b>CotaFácil</b> &copy; {datetime.now().year}</span>
      <span>Dados da AwesomeAPI. Valores informativos, sem caráter de recomendação.</span>
    </div>
    """
)

declarar_idioma()