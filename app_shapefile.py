# app_shapefile.py

import streamlit as st
import geopandas as gpd
import pandas as pd
from pathlib import Path
from streamlit_folium import st_folium

# Configuração da página
st.set_page_config(page_title="Exportar por Tipo de Propriedade", layout="wide")
st.title("Exportar Propriedades por Tipo - Ceará")


# Cria pasta de output
OUTPUT_DIR = Path("output_shapes")
OUTPUT_DIR.mkdir(exist_ok=True)

# Seleção do tipo de propriedade com opção "Todas"
tipo_selecionado = st.selectbox("Selecione o tipo de propriedade", list(CATEGORIAS.keys()))

def buscar_propriedades_em_todos_municipios(filtro_categoria=None):
    """Busca propriedades em todos os municípios, com filtro opcional por categoria"""
    municipios = fetch_municipios_all()
    if not municipios:
        st.error("Erro ao carregar municípios.")
        return gpd.GeoDataFrame()
    
    progresso = st.progress(0)
    gdf_final = gpd.GeoDataFrame()
    total_municipios = len(municipios)
    municipios_com_dados = 0
    
    for i, municipio in enumerate(municipios):
        progresso.progress((i + 1) / total_municipios)
        
        try:
            geojson = fetch_geojson_por_municipio(municipio)
            if not geojson or not geojson.get("features"):
                continue
            
            # Filtra features conforme seleção
            if filtro_categoria:
                features_filtradas = [
                    f for f in geojson["features"]
                    if f.get("properties", {}).get("categoria") == filtro_categoria
                ]
            else:  # Caso "Todas"
                features_filtradas = geojson["features"]
            
            if features_filtradas:
                gdf_municipio = gpd.GeoDataFrame.from_features(features_filtradas)
                gdf_final = pd.concat([gdf_final, gdf_municipio], ignore_index=True)
                municipios_com_dados += 1
                
        except Exception as e:
            st.warning(f"Erro no município {municipio}: {str(e)}")
            continue
    
    if not gdf_final.empty:
        gdf_final.crs = "EPSG:4326"
    
    return gdf_final, municipios_com_dados, total_municipios

def gerar_shapefile_local(gdf, tipo):
    """Gera Shapefile localmente com campos essenciais"""
    colunas_necessarias = {
        'nome_municipio': 'municipio',
        'categoria': 'tipo',
        'nome_municipio_original': 'mun_orig',
        'modulo_fiscal': 'mod_fisc',
        'geometry': 'geometry'
    }
    
    gdf_filtrado = gdf[[col for col in colunas_necessarias.keys() if col in gdf.columns]]
    gdf_filtrado = gdf_filtrado.rename(columns={
        col: new_name for col, new_name in colunas_necessarias.items() 
        if col in gdf_filtrado.columns
    })
    
    nome_arquivo = f"propriedades_{tipo.lower().replace(' ', '_').replace('<', 'lt') if tipo != 'Todas' else 'todas_categorias'}"
    caminho_shp = OUTPUT_DIR / nome_arquivo
    
    gdf_filtrado.to_file(caminho_shp, driver='ESRI Shapefile', encoding='utf-8')
    st.success(f"Shapefile gerado em: {caminho_shp}.shp")

def calcular_resumo_areas(gdf):
    """Calcula resumo de áreas com percentuais para todas as categorias"""
    if gdf.empty or 'area' not in gdf.columns:
        return pd.DataFrame(), 0
    
    gdf['area'] = pd.to_numeric(gdf['area'], errors='coerce')
    
    # Agrupa por categoria (se existir) ou cria um grupo único
    if 'categoria' in gdf.columns:
        resumo = gdf.groupby('categoria')['area'].agg(['sum', 'count']).reset_index()
        resumo.columns = ['Tipo de Propriedade', 'Área Total (ha)', 'Quantidade']
    else:
        total_area = gdf['area'].sum()
        total_count = len(gdf)
        resumo = pd.DataFrame({
            'Tipo de Propriedade': ['Todas as Propriedades'],
            'Área Total (ha)': [total_area],
            'Quantidade': [total_count]
        })
    
    total_area = resumo['Área Total (ha)'].sum()
    resumo['% da Área Total'] = (resumo['Área Total (ha)'] / total_area * 100).round(2)
    resumo = resumo.sort_values('Área Total (ha)', ascending=False)
    
    # Formatação
    resumo['Área Total (ha)'] = resumo['Área Total (ha)'].apply(
        lambda x: f"{x:,.2f}".replace(".", "X").replace(",", ".").replace("X", ",")
    )
    
    return resumo, total_area

if st.button("Buscar Propriedades"):
    filtro = CATEGORIAS[tipo_selecionado]["filtro"] if tipo_selecionado != "Todas" else None
    
    with st.spinner("Buscando propriedades em todos os municípios..."):
        propriedades, municipios_com_dados, total_municipios = buscar_propriedades_em_todos_municipios(filtro)
    
    if propriedades.empty:
        st.warning(f"Nenhuma propriedade encontrada em {total_municipios} municípios.")
    else:
        if tipo_selecionado == "Todas":
            st.success(f"✅ Encontradas {len(propriedades)} propriedades (todas categorias) em {municipios_com_dados}/{total_municipios} municípios")
        else:
            st.success(f"✅ Encontradas {len(propriedades)} propriedades do tipo '{tipo_selecionado}' em {municipios_com_dados}/{total_municipios} municípios")
        
        # Seção de Resumo
        st.subheader("📊 Resumo de Áreas por Categoria")
        resumo_areas, area_total = calcular_resumo_areas(propriedades)
        
        if not resumo_areas.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("Categorias", len(resumo_areas) if 'categoria' in propriedades.columns else 1)
            col2.metric("Propriedades", resumo_areas['Quantidade'].sum())
            col3.metric("Área Total", f"{area_total:,.2f} ha")
            
            st.dataframe(
                resumo_areas,
                column_config={
                    "Tipo de Propriedade": st.column_config.TextColumn("Categoria"),
                    "Área Total (ha)": st.column_config.NumberColumn("Área (ha)", format="%.2f"),
                    "% da Área Total": st.column_config.ProgressColumn("% Total", format="%.2f%%", min_value=0, max_value=100),
                    "Quantidade": st.column_config.NumberColumn("Quantidade", format="%d")
                },
                hide_index=True,
                use_container_width=True
            )
            
            with st.expander("Visualização Gráfica"):
                if len(resumo_areas) > 1:
                    st.bar_chart(resumo_areas.set_index('Tipo de Propriedade')['% da Área Total'])
                else:
                    st.write("Selecione 'Todas' para comparar categorias no gráfico")
        
       
        # Seção de Dados Completos
        with st.expander("Ver dados completos"):
            st.dataframe(propriedades.drop(columns='geometry'))
        
        # Geração do Shapefile
        if st.button("Gerar Shapefile Local"):
            gerar_shapefile_local(propriedades, tipo_selecionado)