import streamlit as st
import folium
import json
import geopandas as gpd
from streamlit_folium import st_folium
from folium.plugins import Fullscreen
import base64
from io import BytesIO
from PIL import Image
from modules.data_loader import (
    fetch_regioes, fetch_municipios,
    fetch_geojson_por_municipio,
    fetch_geojson_limites
)

# Cores para as categorias de propriedade
CORES = {
    "Pequena Propriedade < 1 MF": "#fecc5c",
    "Pequena Propriedade": "#fd8d3c",
    "Média Propriedade": "#f03b20",
    "Grande Propriedade": "#bd0026",
    "Sem Classificação": "#eeeee4"
}

def simplify_geojson(geojson_data, tolerance=0.001):
    if not geojson_data or not geojson_data.get("features"):
        return geojson_data
    gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])
    gdf["geometry"] = gdf["geometry"].simplify(tolerance)
    return json.loads(gdf.to_json())

def get_map_center(geojson):
    for f in geojson["features"]:
        g = f["geometry"]
        if g["type"] == "Polygon":
            lng, lat = g["coordinates"][0][0]
            return [lat, lng]
        elif g["type"] == "MultiPolygon":
            lng, lat = g["coordinates"][0][0][0]
            return [lat, lng]
    return [-5.2, -39.0]  # Centro do Ceará

def create_map(categoria_selecionada, regiao="(todos)"):
    # Busca todos os municípios do Ceará
    regioes = fetch_regioes()
    if not regioes:
        st.error("Erro ao carregar regiões.")
        return None
    
    all_features = []
    boundaries = []
    
    # Se for selecionada uma região específica, busca apenas seus municípios
    if regiao != "(todos)":
        municipios = fetch_municipios(regiao)
    else:
        # Busca municípios de todas as regiões
        municipios = []
        for r in regioes:
            municipios.extend(fetch_municipios(r))
    
    with st.spinner(f"Carregando propriedades {categoria_selecionada} de {len(municipios)} municípios..."):
        for municipio in municipios:
            try:
                geojson_data = fetch_geojson_por_municipio(municipio)
                if geojson_data and geojson_data.get("features"):
                    # Filtra apenas as features da categoria selecionada
                    feats = [f for f in geojson_data["features"] 
                            if f.get("properties", {}).get("categoria", "Sem Classificação") == categoria_selecionada]
                    all_features.extend(feats)
                    
                    # Adiciona limites do município
                    boundary = fetch_geojson_limites(municipio)
                    if boundary and boundary.get("features"):
                        boundaries.extend(boundary["features"])
            except Exception as e:
                st.warning(f"Erro ao processar {municipio}: {str(e)}")
                continue
    
    if not all_features:
        st.warning(f"Nenhuma propriedade encontrada para a categoria {categoria_selecionada}")
        return None
    
    # Cria o GeoJSON com todas as propriedades da categoria selecionada
    propriedades_geojson = {"type": "FeatureCollection", "features": all_features}
    propriedades_geojson = simplify_geojson(propriedades_geojson)
    
    # Cria o GeoJSON com os limites dos municípios
    boundary_geojson = {"type": "FeatureCollection", "features": boundaries} if boundaries else None
    
    # Cria o mapa
    center = get_map_center(propriedades_geojson)
    m = folium.Map(location=center, zoom_start=7, tiles=None, control_scale=True)
    
    # Adiciona o tile layer
    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
        attr='© OpenStreetMap contributors, © CARTO',
        name='Mapa Base',
        control=False,
        overlay=True
    ).add_to(m)
    
    # Adiciona os limites dos municípios
    if boundary_geojson and boundary_geojson.get("features"):
        folium.GeoJson(
            boundary_geojson,
            name='<span><svg width="12" height="12"><rect width="12" height="12" fill="#003366"/></svg> Limites Municipais</span>',
            style_function=lambda x: {
                'color': '#003366', 'weight': 1, 'opacity': 0.7,
                'fill': False, 'dashArray': '5, 5'
            },
            tooltip=folium.GeoJsonTooltip(fields=['nome_municipio'], aliases=['Município:'])
        ).add_to(m)
    
    # Adiciona as propriedades da categoria selecionada
    cor = CORES.get(categoria_selecionada, "#eeeeee")
    name_html = (
        f'<span><svg width="12" height="12">'
        f'<circle cx="6" cy="6" r="6" fill="{cor}" /></svg> {categoria_selecionada}</span>'
    )
    fg = folium.FeatureGroup(name=name_html, overlay=True, control=True)
    
    folium.GeoJson(
        propriedades_geojson,
        style_function=lambda x, cor=cor: {
            'fillColor': cor, 'color': '#000', 'weight': 0.3, 'fillOpacity': 0.7
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['nome_municipio', 'area', 'categoria'],
            aliases=['Município:', 'Área (ha):', 'Categoria:'],
            localize=True
        )
    ).add_to(fg)
    fg.add_to(m)
    
    # Adiciona controles
    folium.LayerControl(collapsed=False).add_to(m)
    Fullscreen().add_to(m)
    
    return m

def get_map_image(m):
    """Converte o mapa folium em uma imagem PNG"""
    img_data = m._to_png(5)
    img = Image.open(BytesIO(img_data))
    return img

def main():
    st.set_page_config(page_title="Mapa Fundiário por Tipo de Propriedade", layout="wide")
    st.title("Mapa Fundiário por Tipo de Propriedade - Ceará")
    
    # Seleção da categoria
    categorias = list(CORES.keys())
    categoria_selecionada = st.selectbox(
        "Selecione o tipo de propriedade:",
        categorias,
        index=0
    )
    
    # Opcional: filtrar por região administrativa
    regioes = ["(todos)"] + fetch_regioes()
    regiao_selecionada = st.selectbox(
        "Filtrar por região administrativa (opcional):",
        regioes,
        index=0
    )
    
    if st.button("Gerar Mapa"):
        m = create_map(categoria_selecionada, regiao_selecionada)
        if m:
            # Exibe o mapa
            st_folium(m, width=1200, height=800, returned_objects=[])
            
            # Botão para download da imagem
            img = get_map_image(m)
            buf = BytesIO()
            img.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.download_button(
                label="Baixar Mapa como PNG",
                data=byte_im,
                file_name=f"mapa_{categoria_selecionada.lower().replace(' ', '_')}_ceara.png",
                mime="image/png"
            )

if __name__ == "__main__":
    main()