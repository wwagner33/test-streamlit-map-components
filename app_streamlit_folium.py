import streamlit as st
from streamlit_folium import st_folium
import folium
from branca.element import Element
from modules.data_loader import (
    fetch_regioes,
    fetch_municipios,
    fetch_geojson_por_regiao,
    fetch_geojson_por_municipio,
    fetch_geojson_limites
)

# Configuração da página
st.set_page_config(
    page_title="Localização Fundiária Interativa",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📍 Mapa Fundiário Interativo do Ceará")

# --- Sidebar: seleções de região e município ---
regioes = fetch_regioes()
if not regioes:
    st.error("Não foi possível carregar as regiões do microserviço.")
    st.stop()

regiao = st.sidebar.selectbox("Selecione a Região Administrativa:", regioes)
municipios = fetch_municipios(regiao)
municipio = st.sidebar.selectbox(
    "Selecione o Município (opcional):", ["(toda a região)"] + municipios
)

# --- Carga de dados com cache (5 minutos) ---
@st.cache_data(ttl=300)
def load_geojson(regiao, municipio):
    try:
        if municipio == "(toda a região)":
            features = fetch_geojson_por_regiao(regiao).get("features", [])
            # limites de todos os municípios da região
            bounds_feats = []
            for m in municipios:
                b = fetch_geojson_limites(m)
                if b and b.get("features"):
                    bounds_feats.extend(b["features"])
            boundary_geojson = {"type": "FeatureCollection", "features": bounds_feats} if bounds_feats else None
        else:
            features = fetch_geojson_por_municipio(municipio).get("features", [])
            boundary_geojson = fetch_geojson_limites(municipio)
        return {"type": "FeatureCollection", "features": features}, boundary_geojson
    except Exception as e:
        st.error(f"Erro ao obter dados: {e}")
        st.stop()

geojson, boundary_geojson = load_geojson(regiao, municipio)
if not geojson.get("features"):
    st.warning("Nenhuma geometria encontrada para o filtro selecionado.")
    st.stop()

# --- Mapa base com Canvas para melhor performance ---
mapa = folium.Map(
    location=[-5.282, -39.305],
    zoom_start=8,
    tiles="OpenStreetMap",
    prefer_canvas=True
)

# --- Cores por categoria ---
CORES = {
    "Pequena Propriedade < 1 MF": "#fecc5c",
    "Pequena Propriedade": "#fd8d3c",
    "Média Propriedade": "#f03b20",
    "Grande Propriedade": "#bd0026",
    "Sem Classificação": "#808080"
}

# --- Adicionar camada por categoria ---
for categoria, cor in CORES.items():
    # filtrar features
    feats = [f for f in geojson["features"] if f["properties"].get("categoria") == categoria]
    # sem classificação
    if categoria == "Sem Classificação":
        feats = [f for f in geojson["features"] if f["properties"].get("categoria") not in CORES]
    if not feats:
        continue
    subset = {"type": "FeatureCollection", "features": feats}
    folium.GeoJson(
        subset,
        name=categoria,
        style_function=lambda feat, color=cor: {
            "fillColor": color,
            "color": color,
            "weight": 1,
            "fillOpacity": 0.6,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["area", "categoria"],
            aliases=["Área (ha)", "Categoria"]
        )
    ).add_to(mapa)

# --- Overlay de limites municipais ---
if boundary_geojson and boundary_geojson.get("features"):
    folium.GeoJson(
        boundary_geojson,
        name="Limites Municipais",
        style_function=lambda feat: {"color": "black", "weight": 2, "fillOpacity": 0},
        tooltip=folium.GeoJsonTooltip(
            fields=["nome_municipio"],
            aliases=["Município"]
        )
    ).add_to(mapa)

# --- Legenda customizada ---
legend_html = '''
<div style="position: fixed; bottom: 50px; right: 10px; background-color: white; 
     border:2px solid grey; z-index:9999; padding:10px; font-size:14px; max-height:300px; overflow-y:auto;">
  <b>Legenda</b><br>
'''
for categoria, cor in CORES.items():
    legend_html += f'<i style="background:{cor};width:18px;height:18px;display:inline-block;'
    legend_html += 'margin-right:5px;border:1px solid #555;vertical-align:middle;"></i>' + categoria + '<br>'
legend_html += '</div>'
mapa.get_root().html.add_child(Element(legend_html))

# --- Controle de camadas ---
folium.LayerControl(collapsed=False).add_to(mapa)

# --- Exibição no Streamlit ---
st_folium(mapa, width=900, height=650)
