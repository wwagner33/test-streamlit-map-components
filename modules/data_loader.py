# modules/data_loader.py

import requests
import streamlit as st

# URL base do seu microserviço (ajuste se estiver rodando em outro host/porta)
BASE_URL = st.secrets.get("TERRAGEO_URL", "http://127.0.0.1:8000")

@st.cache_data(ttl=60 * 5)
def fetch_regioes() -> list[str]:
    resp = requests.get(f"{BASE_URL}/regioes")
    resp.raise_for_status()
    return resp.json().get("regioes", [])

@st.cache_data(ttl=60 * 5)
def fetch_municipios(regiao: str) -> list[str]:
    resp = requests.get(f"{BASE_URL}/municipios", params={"regiao": regiao})
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json().get("municipios", [])

@st.cache_data(ttl=60 * 5)
def fetch_geojson_por_regiao(regiao: str) -> dict:
    resp = requests.get(f"{BASE_URL}/geojson", params={"regiao": regiao})
    resp.raise_for_status()
    return resp.json()

@st.cache_data(ttl=60 * 5)
def fetch_geojson_por_municipio(municipio: str) -> dict:
    resp = requests.get(f"{BASE_URL}/geojson", params={"municipio": municipio})
    resp.raise_for_status()
    return resp.json()

@st.cache_data(ttl=60 * 5)
def fetch_geojson_limites(municipio: str) -> dict:
    """
    Chama GET /geojson_muni?municipio=YYY e retorna o FeatureCollection do município (limite administrativo).
    """
    resp = requests.get(f"{BASE_URL}/geojson_muni", params={"municipio": municipio})
    resp.raise_for_status()
    return resp.json()