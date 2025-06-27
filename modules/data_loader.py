# modules/data_loader.py

import requests
import streamlit as st
from typing import Dict, List, Optional

BASE_URL = st.secrets.get("TERRAGEO_URL", "http://127.0.0.1:8000")

@st.cache_data(ttl=3600)
def fetch_regioes() -> List[str]:
    """Busca todas as regiões administrativas."""
    resp = requests.get(f"{BASE_URL}/regioes", timeout=120)
    resp.raise_for_status()
    return resp.json().get("regioes", [])

@st.cache_data(ttl=3600)
def fetch_municipios(regiao: str) -> List[str]:
    """Busca municípios de uma região específica."""
    resp = requests.get(f"{BASE_URL}/municipios", params={"regiao": regiao}, timeout=120)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json().get("municipios", [])

@st.cache_data(ttl=3600)
def fetch_municipios_all() -> List[str]:
    """Busca TODOS os municípios do Ceará."""
    resp = requests.get(f"{BASE_URL}/municipios_todos", timeout=120)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json().get("municipios", [])

@st.cache_data(ttl=3600)
def fetch_geojson_municipio(municipio: str) -> Dict:
    """Busca GeoJSON específico de um município."""
    resp = requests.get(f"{BASE_URL}/geojson_muni", params={"municipio": municipio}, timeout=120)
    if resp.status_code == 404:
        return {"type": "FeatureCollection", "features": []}
    resp.raise_for_status()
    return resp.json()

@st.cache_data(ttl=3600, hash_funcs={dict: lambda _: None})
def fetch_geojson_assentamentos(
    municipio: Optional[str] = None,
    tolerance: Optional[float] = None,
    decimals: Optional[int] = None
) -> Dict:
    """
    Busca dados de assentamentos em formato GeoJSON.
    
    Args:
        municipio: Filtro por município (opcional)
        tolerance: Tolerância de simplificação da geometria (opcional)
        decimals: Número de casas decimais nas coordenadas (opcional)
    """
    params = {}
    if municipio:
        params["municipio"] = municipio
    if tolerance is not None:
        params["tolerance"] = tolerance
    if decimals is not None:
        params["decimals"] = decimals
    
    try:
        resp = requests.get(f"{BASE_URL}/geojson_assentamentos", params=params, timeout=120)
        
        if resp.status_code == 404:
            return {"type": "FeatureCollection", "features": []}
        
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erro na requisição: {str(e)}")
        return {"type": "FeatureCollection", "features": []}

@st.cache_data(ttl=3600)
def fetch_assentamentos_municipios() -> List[str]:
    """Busca todos os municípios que possuem assentamentos."""
    resp = requests.get(f"{BASE_URL}/assentamentos_municipio", timeout=120)
    if resp.status_code == 404:
        return []
    
    resp.raise_for_status()
    return resp.json().get("municipios", [])