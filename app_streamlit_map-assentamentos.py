import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MiniMap, Fullscreen
import requests
from typing import Optional

# Configuração da página
st.set_page_config(page_title="Assentamentos do Ceará", layout="wide")
st.title("Mapa de Assentamentos do Ceará")

# Estilo CSS personalizado
st.markdown("""
<style>
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .stSelectbox>div>div>select {
        min-width: 300px;
    }
</style>
""", unsafe_allow_html=True)

# Cores para diferentes tipos de assentamento
CORES_ASSENTAMENTOS = {
    "Estadual": "#ff7f0e",  # Laranja
    "Federal": "#1f77b4",   # Azul
}

# Cores para ícones dos marcadores
CORES_MARKERS = {
    "Estadual": "#ff7f0e",  # Laranja
    "Federal": "#1f77b4",   # Azul
}

# Coordenadas padrão do Ceará
CENTRO_CEARA = [-5.2, -39.0]
ZOOM_PADRAO = 8

# Carga dos dados para o Mapa de Assentamentos

# Controle de simplificação
tolerancia = 0.001

def carregar_geojson(municipio: str = "todos", tipo: str = "todos", tolerancia: float = 0.001) -> Optional[dict]:
    """Carrega dados GeoJSON da API com filtros"""
    try:
        url = f"http://localhost:8000/geojson_assentamentos?municipio={municipio}&tipo={tipo}&tolerance={tolerancia}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return None

def criar_mapa_base() -> folium.Map:
    """Cria um mapa Folium base com configurações padrão"""
    return folium.Map(
        location=CENTRO_CEARA,
        zoom_start=ZOOM_PADRAO,
        tiles="cartodbpositron",
        control_scale=True,
        prefer_canvas=True
    )

def adicionar_camadas(mapa: folium.Map, geojson_data: dict):
    if not geojson_data or not geojson_data.get("features"):
        st.warning("Nenhum dado de assentamento para exibir.")
        return
    
    # Verifique os campos disponíveis na primeira feature
    if geojson_data['features']:
        sample_feature = geojson_data['features'][0]
        available_fields = list(sample_feature['properties'].keys())
    else:
        available_fields = []
    
    # Defina os campos a serem usados com fallback
    tooltip_fields = [
        'cd_sipra', 'tipo_assentamento', 'nome_assentamento', 
        'nome_municipio_original', 'num_familias', 'forma_obtecao', 
        'area', 'perimetro'
    ]
    
    # Filtre apenas campos disponíveis
    fields_to_use = [f for f in tooltip_fields if f in available_fields]
    
    # Crie aliases correspondentes
    aliases_map = {
        'cd_sipra': 'Cd_SIPRA: ',
        'tipo_assentamento': 'Tipo: ',
        'nome_assentamento': 'Assentamento: ',
        'nome_municipio_original': 'Município: ',
        'num_familias': 'Famílias: ',
        'forma_obtecao': 'Forma de Obtenção: ',
        'area': 'Área (ha): ',
        'perimetro': 'Perímetro (km): '
    }
    aliases_to_use = [aliases_map.get(f, f) for f in fields_to_use]  # Usa o campo se não tiver alias

    # Camada GeoJSON com tooltip adaptável
    folium.GeoJson(
        geojson_data,
        name="Assentamentos",
        style_function=lambda feature: {
            'fillColor': CORES_ASSENTAMENTOS.get(
                feature['properties'].get('tipo_assentamento', 'Outros').capitalize(),
                "#ff7f0e"  # Cor padrão
            ),
            'color': '#000000',
            'weight': 0.5,
            'fillOpacity': 0.7
        },
        tooltip=folium.GeoJsonTooltip(
            fields=fields_to_use,
            aliases=aliases_to_use,
            sticky=True,
            style="font-family: Arial; font-size: 12px;"
        )
    ).add_to(mapa)
    
    # Adiciona marcadores com tratamento de campos ausentes
    for feature in geojson_data['features']:
        try:
            props = feature['properties']
            
            # Obter coordenadas com fallback
            try:
                if feature['geometry']['type'] == 'MultiPolygon':
                    # Pega o primeiro ponto do primeiro polígono do MultiPolygon
                    coords = feature['geometry']['coordinates'][0][0][0]  # Primeiro polígono, primeiro anel, primeiro ponto
                    lon, lat = coords[0], coords[1]
                elif feature['geometry']['type'] == 'Polygon':
                    coords = feature['geometry']['coordinates'][0][0]  # Primeiro anel, primeiro ponto
                    lon, lat = coords[0], coords[1]
                else:
                    # Outros tipos? Ponto? Linha? Vamos tentar pegar o primeiro ponto da lista de coordenadas
                    coords = feature['geometry']['coordinates'][0]
                    lon, lat = coords[0], coords[1]
            except (IndexError, TypeError):
                # Se falhar, usar um ponto padrão (centro do Ceará) e logar o erro
                print(f"Erro ao obter coordenadas para o assentamento: {props.get('nome_assentamento')}")
                lat, lon = CENTRO_CEARA
            
            # Tooltip com valores padrão
            tooltip_content = f"""
                <b>CD_SIPRA:</b> {props.get('cd_sipra', 'N/A')}<br>
                <b>Tipo:</b> {props.get('tipo_assentamento', 'N/A')}<br>
                <b>Assentamento:</b> {props.get('nome_assentamento', 'N/A')}<br>
                <b>Município:</b> {props.get('nome_municipio_original', 'N/A')}<br>
                <b>Famílias:</b> {props.get('num_familias', 'N/A')}<br>
                <b>Forma de Obtenção:</b> {props.get('forma_obtecao', 'N/A')}<br>
                <b>Área:</b> {props.get('area', 'N/A')} ha<br>
                <b>Perímetro:</b> {props.get('perimetro', 'N/A')} km<br>
            """
            
            # Determina a cor do marcador baseada no tipo de assentamento
            tipo = props.get('tipo_assentamento', '').capitalize()
            cor_marker = CORES_MARKERS.get(tipo, "#ff7f0e")  # Default laranja
            
            # Cria marcador com ícone personalizado
            folium.Marker(
                location=[lat, lon],
                tooltip=folium.Tooltip(tooltip_content),
                icon=folium.Icon(
                    color='white',  # Cor do ícone (branco)
                    icon_color=cor_marker,  # Cor principal do marcador
                    icon='home',  # Ícone
                    prefix='fa'   # Font Awesome
                )
            ).add_to(mapa)
        except (KeyError, IndexError, TypeError) as e:
            print(f"Erro ao processar feature: {e}")

    # Adiciona minimapa
    MiniMap(toggle_display=True).add_to(mapa)
    Fullscreen().add_to(mapa)

def obter_municipios() -> list:
    """Obtém lista de municípios da API"""
    try:
        url = "http://localhost:8000/assentamentos_municipios"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("municipios", [])
    except requests.exceptions.RequestException:
        return []

# Carrega dados e adiciona ao mapa

municipios = ["Todos"] + obter_municipios()
tipos_assentamento = ["Todos", "Estadual", "Federal"]

# Corpo principal
col1, col2 = st.columns([12, 4])

with col2:
    st.markdown(f"### Filtros")

    # Carrega municípios
    municipio_selecionado = st.selectbox(
        "Selecione o município:",
        municipios,
        index=0
    )

    # Novo filtro por tipo de assentamento
    tipo_selecionado = st.selectbox(
        "Selecione o tipo de assentamento:",
        tipos_assentamento,
        index=0
    )
    
    st.markdown("---")

    st.markdown("### Informações")
    # Carrega os dados com base nos filtros selecionados
    geojson_data = carregar_geojson(
        municipio="todos" if municipio_selecionado == "Todos" else municipio_selecionado,
        tipo="todos" if tipo_selecionado == "Todos" else tipo_selecionado.lower(),
        tolerancia=tolerancia
    )

    # Resumo estatístico
    if geojson_data and geojson_data.get("features"):
        areas = [f['properties'].get('area', 0) for f in geojson_data['features']]
        num_assentamentos = len(areas)
        if municipio_selecionado == 'Todos' and tipo_selecionado == 'Todos': 
            st.metric("Total de assentamentos", num_assentamentos)
            st.metric("Área média (ha)", round(sum(areas)/num_assentamentos, 2) if num_assentamentos > 0 else 0)
            st.metric("Área total (ha)", round(sum(areas), 2))
        else:
            st.metric("Total de assentamentos", num_assentamentos)
            st.metric("Área total (ha)", round(sum(areas), 2))
    else:
        st.metric("Total de assentamentos", 0)
        st.metric("Área total (ha)", 0)

    st.markdown("---")
    for tipo, cor in CORES_ASSENTAMENTOS.items():
        st.markdown(f"<span style='color:{cor}; font-weight:bold'>■</span> {tipo}", unsafe_allow_html=True)

with col1:
    # Cria o mapa base
    mapa = criar_mapa_base()
        
    if geojson_data:
        adicionar_camadas(mapa, geojson_data)
        
        # Exibe o mapa
        st_folium(
            mapa,
            width=1200,
            height=700,
            returned_objects=[]
        )
    else:
        st.warning("Nenhum dado disponível para os filtros selecionados.")