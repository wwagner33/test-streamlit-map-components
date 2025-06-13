# Módulo com defeito :-(

# import streamlit as st
# from streamlit_leaflet import st_leaflet
# from modules.data_loader import (
#     fetch_regioes,
#     fetch_municipios,
#     fetch_geojson_por_regiao,
#     fetch_geojson_por_municipio,
#     fetch_geojson_limites
# )

# # Configuração da página
# st.set_page_config(
#     page_title="Localização Fundiária Interativa",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )
# st.title("📍 Mapa Fundiário Interativo do Ceará")

# # --- Sidebar: seleção de região e município ---
# regioes = fetch_regioes()
# if not regioes:
#     st.error("Não foi possível carregar as regiões do microserviço.")
#     st.stop()

# regiao = st.sidebar.selectbox("Selecione a Região Administrativa:", regioes)
# municipios = fetch_municipios(regiao)
# municipio = st.sidebar.selectbox(
#     "Selecione o Município (opcional):", ["(toda a região)"] + municipios
# )

# # --- Carregamento e cache dos GeoJSON (5 minutos) ---
# @st.cache_data(ttl=300)
# def load_geojson(regiao, municipio):
#     if municipio == "(toda a região)":
#         features = fetch_geojson_por_regiao(regiao).get("features", [])
#         bounds_feats = []
#         for m in municipios:
#             b = fetch_geojson_limites(m)
#             if b and b.get("features"):
#                 bounds_feats.extend(b["features"])
#         boundary = {"type": "FeatureCollection", "features": bounds_feats} if bounds_feats else None
#     else:
#         features = fetch_geojson_por_municipio(municipio).get("features", [])
#         boundary = fetch_geojson_limites(municipio)
#     return {"type": "FeatureCollection", "features": features}, boundary

# geojson, boundary_geojson = load_geojson(regiao, municipio)
# if not geojson.get("features"):
#     st.warning("Nenhuma geometria encontrada para o filtro selecionado.")
#     st.stop()

# # --- Definição de cores por categoria ---
# CORES = {
#     "Pequena Propriedade < 1 MF": "#fecc5c",
#     "Pequena Propriedade": "#fd8d3c",
#     "Média Propriedade": "#f03b20",
#     "Grande Propriedade": "#bd0026",
#     "Sem Classificação": "#808080"
# }

# # --- Configuração do mapa via streamlit-leaflet ---
# map_options = {
#     "center": {"lat": -5.282, "lng": -39.305},
#     "zoom": 8,
#     "tiles": "OpenStreetMap",
#     "preferCanvas": True,
#     "zoomControl": True,
#     "scrollWheelZoom": True,
#     "dragging": True
# }

# layers = []
# # camadas por categoria
# for categoria, cor in CORES.items():
#     feats = [f for f in geojson["features"] if f["properties"].get("categoria") == categoria]
#     if categoria == "Sem Classificação":
#         feats = [f for f in geojson["features"] if f["properties"].get("categoria") not in CORES]
#     if not feats:
#         continue
#     subset = {"type": "FeatureCollection", "features": feats}
#     layers.append({
#         "type": "geoJson",
#         "data": subset,
#         "style": {"fillColor": cor, "color": cor, "weight": 1, "fillOpacity": 0.6},
#         "tooltipOptions": {
#             "fields": ["nome_proprietario", "area", "categoria"],
#             "aliases": ["Proprietário", "Área (ha)", "Categoria"],
#             "sticky": True
#         }
#     })

# # limite municipal
# if boundary_geojson and boundary_geojson.get("features"):
#     layers.append({
#         "type": "geoJson",
#         "data": boundary_geojson,
#         "style": {"color": "black", "weight": 2, "fillOpacity": 0},
#         "tooltipOptions": {
#             "fields": ["nome_municipio"],
#             "aliases": ["Município"],
#             "sticky": True
#         }
#     })

# # --- Legenda personalizada ---
# def create_legend(cores):
#     """Cria o HTML para a legenda do mapa"""
#     legend_items = []
#     for cat, color in cores.items():
#         item = f'''
#         <div style="display: flex; align-items: center; margin-bottom: 5px;">
#             <div style="background: {color}; width: 18px; height: 18px; 
#                       border: 1px solid #555; margin-right: 5px;"></div>
#             <span>{cat}</span>
#         </div>
#         '''
#         legend_items.append(item)
    
#     legend_html = f'''
#     <div style="
#         position: fixed;
#         bottom: 50px;
#         right: 10px;
#         background-color: white;
#         border: 2px solid grey;
#         z-index: 9999;
#         padding: 10px;
#         font-size: 14px;
#         max-height: 300px;
#         overflow-y: auto;
#     ">
#         <div style="font-weight: bold; margin-bottom: 8px;">Legenda</div>
#         {"".join(legend_items)}
#     </div>
#     '''
#     return legend_html

# # Exibe a legenda
# st.markdown(create_legend(CORES), unsafe_allow_html=True)

# # --- Renderiza o mapa ---
# st_leaflet(
#     options=map_options,
#     layers=layers,
#     height=650,
#     key="mapa_principal",
#     zoom_animation=True
# )