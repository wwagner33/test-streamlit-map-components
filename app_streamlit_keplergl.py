import streamlit as st
from streamlit_keplergl import keplergl_static
from keplergl import KeplerGl
import json
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
st.title("Mapa Fundiário Interativo do Ceará")

# --- Sidebar: seleção de região e município ---
regioes = fetch_regioes()
if not regioes:
    st.error("Não foi possível carregar as regiões do microserviço.")
    st.stop()

regiao = st.sidebar.selectbox("Selecione a Região Administrativa:", regioes)
municipios = fetch_municipios(regiao)
municipio = st.sidebar.selectbox(
    "Selecione o Município (opcional):", ["(toda a região)"] + municipios
)

# --- Carregamento dos GeoJSON ---
def load_geojson(regiao, municipio):
    if municipio == "(toda a região)":
        features = fetch_geojson_por_regiao(regiao).get("features", [])
        bounds_feats = []
        for m in municipios:
            b = fetch_geojson_limites(m)
            if b and b.get("features"):
                bounds_feats.extend(b["features"])
        boundary = {"type": "FeatureCollection", "features": bounds_feats} if bounds_feats else None
    else:
        features = fetch_geojson_por_municipio(municipio).get("features", [])
        boundary = fetch_geojson_limites(municipio)
    return {"type": "FeatureCollection", "features": features}, boundary

geojson, boundary_geojson = load_geojson(regiao, municipio)
if not geojson.get("features"):
    st.warning("Nenhuma geometria encontrada para o filtro selecionado.")
    st.stop()

# --- Definição de cores por categoria ---
CORES = {
    "Pequena Propriedade < 1 MF": [254, 204, 92],
    "Pequena Propriedade": [253, 141, 60],
    "Média Propriedade": [240, 59, 32],
    "Grande Propriedade": [189, 0, 38],
    "Sem Classificação": [128, 128, 128]
}

# --- Configuração do Kepler.gl ---
def create_kepler_config():
    """Cria a configuração visual para o Kepler.gl"""
    config = {
        "version": "v1",
        "config": {
            "mapState": {
                "latitude": -5.282,
                "longitude": -39.305,
                "zoom": 8,
                "bearing": 0,
                "pitch": 0,
                "dragRotate": False
            },
            "mapStyle": {
                "styleType": "dark",
                "topLayerGroups": {},
                "visibleLayerGroups": {
                    "label": True,
                    "road": True,
                    "border": False,
                    "building": True,
                    "water": True,
                    "land": True,
                    "3d building": False
                }
            }
        }
    }
    
    # Adiciona camadas para cada categoria
    layers = []
    for idx, (categoria, cor) in enumerate(CORES.items()):
        layer = {
            "id": f"propriedades-{idx}",
            "type": "geojson",
            "config": {
                "dataId": categoria,
                "label": categoria,
                "color": cor,
                "columns": {
                    "geojson": "_geojson"
                },
                "isVisible": True,
                "visConfig": {
                    "opacity": 0.8,
                    "strokeOpacity": 0.8,
                    "thickness": 0.5,
                    "strokeColor": cor,
                    "colorRange": {
                        "name": "Custom",
                        "type": "custom",
                        "category": "Custom",
                        "colors": [cor]
                    },
                    "strokeColorRange": {
                        "name": "Custom",
                        "type": "custom",
                        "category": "Custom",
                        "colors": [cor]
                    },
                    "radius": 10,
                    "sizeRange": [0, 10],
                    "radiusRange": [0, 50],
                    "heightRange": [0, 500],
                    "elevationScale": 5,
                    "enableElevationZoomFactor": True,
                    "stroked": True,
                    "filled": True,
                    "enable3d": False,
                    "wireframe": False
                },
                "hidden": False,
                "textLabel": [
                    {
                        "field": None,
                        "color": [255, 255, 255],
                        "size": 18,
                        "offset": [0, 0],
                        "anchor": "start",
                        "alignment": "center"
                    }
                ]
            }
        }
        layers.append(layer)
    
    # Adiciona camada para limites municipais
    if boundary_geojson and boundary_geojson.get("features"):
        layers.append({
            "id": "limites-municipais",
            "type": "geojson",
            "config": {
                "dataId": "Limites Municipais",
                "label": "Limites Municipais",
                "color": [0, 0, 0],
                "columns": {
                    "geojson": "_geojson"
                },
                "isVisible": True,
                "visConfig": {
                    "opacity": 1,
                    "strokeOpacity": 1,
                    "thickness": 2,
                    "strokeColor": [0, 0, 0],
                    "colorRange": {
                        "name": "Custom",
                        "type": "custom",
                        "category": "Custom",
                        "colors": [[0, 0, 0]]
                    },
                    "strokeColorRange": {
                        "name": "Custom",
                        "type": "custom",
                        "category": "Custom",
                        "colors": [[0, 0, 0]]
                    },
                    "radius": 10,
                    "sizeRange": [0, 10],
                    "radiusRange": [0, 50],
                    "heightRange": [0, 500],
                    "elevationScale": 5,
                    "enableElevationZoomFactor": True,
                    "stroked": True,
                    "filled": False,
                    "enable3d": False,
                    "wireframe": False
                },
                "hidden": False
            }
        })
    
    config["config"]["layers"] = layers
    return config

# --- Preparação dos dados para o Kepler.gl ---
def prepare_kepler_data(geojson, boundary_geojson):
    """Prepara os dados no formato que o Kepler.gl espera"""
    data = {}
    
    # Separa features por categoria
    for categoria in CORES.keys():
        if categoria == "Sem Classificação":
            feats = [f for f in geojson["features"] if f["properties"].get("categoria") not in CORES]
        else:
            feats = [f for f in geojson["features"] if f["properties"].get("categoria") == categoria]
        
        if feats:
            data[categoria] = {"type": "FeatureCollection", "features": feats}
    
    # Adiciona limites municipais
    if boundary_geojson and boundary_geojson.get("features"):
        data["Limites Municipais"] = boundary_geojson
    
    return data

# --- Cria e exibe o mapa Kepler.gl ---
map_data = prepare_kepler_data(geojson, boundary_geojson)
config = create_kepler_config()

# Cria o mapa Kepler.gl
kepler_map = KeplerGl(height=650, config=config)

# Adiciona os dados ao mapa
for name, geojson_data in map_data.items():
    kepler_map.add_data(data=geojson_data, name=name)

# Exibe o mapa no Streamlit
keplergl_static(kepler_map)