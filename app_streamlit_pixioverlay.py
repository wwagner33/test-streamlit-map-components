# drawOverlayMap.py

import streamlit as st
from modules.data_loader import (
    fetch_regioes,
    fetch_municipios,
    fetch_geojson_por_regiao,
    fetch_geojson_por_municipio,
    fetch_geojson_limites
)
from streamlit.components.v1 import html
import json

st.set_page_config(
    page_title="Localização Fundiária Interativa",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Mapa Fundiário Interativo do Ceará")

# 1) Busca lista de regiões do microserviço
regioes = fetch_regioes()
if not regioes:
    st.error("Não foi possível carregar as regiões do microserviço.")
    st.stop()

# 2) Usuário escolhe região
regiao = st.selectbox("Selecione a região administrativa", regioes)

# 3) Busca municípios dessa região
municipios = fetch_municipios(regiao)
# Adiciona opção para "mostrar toda a região"
municipio = st.selectbox(
    "Selecione o município (opcional)", ["(toda a região)"] + municipios
)

# 4) Quando o usuário clicar em "Gerar Mapa", fazemos a chamada correspondente
geojson = None
boundary_geojson = None
if st.button("Gerar Mapa"):
    if municipio == "(toda a região)":
        # chama /geojson?regiao=regiao
        try:
            geojson = fetch_geojson_por_regiao(regiao)
            # Busca os limites de todos os municípios da região
            boundaries = []
            for m in municipios:
                try:
                    boundary = fetch_geojson_limites(m)
                    if boundary and boundary.get("features"):
                        boundaries.extend(boundary["features"])
                except:
                    continue
            boundary_geojson = {"type": "FeatureCollection", "features": boundaries} if boundaries else None
        except Exception as e:
            st.error(f"Não foi possível carregar GeoJSON da região '{regiao}':\n{e}")
            st.stop()
    else:
        # chama /geojson?municipio=municipio
        try:
            geojson = fetch_geojson_por_municipio(municipio)
            # Busca o limite do município específico
            boundary_geojson = fetch_geojson_limites(municipio)
        except Exception as e:
            st.error(f"Não foi possível carregar GeoJSON do município '{municipio}':\n{e}")
            st.stop()

    # Se retornou GeoJSON vazio ou sem features:
    if not geojson or not geojson.get("features"):
        st.warning("Nenhuma geometria encontrada para o filtro selecionado.")
        st.stop()

    # 5) Converte para string JSON para injetar no HTML do PixiOverlay
    geojson_str = json.dumps(geojson)
    boundary_str = json.dumps(boundary_geojson) if boundary_geojson and boundary_geojson.get("features") else "null"

    # 6) Cores para categorias (deve coincidir com o que está no backend)
    CORES = {
        "Pequena Propriedade < 1 MF": "#fecc5c",
        "Pequena Propriedade": "#fd8d3c",
        "Média Propriedade": "#f03b20",
        "Grande Propriedade": "#bd0026",
        "Sem Classificação": "#808080"
    }

    # 7) Monta o HTML/JavaScript completo com controles interativos
    html_code = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Mapa Fundiário Interativo</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            html, body, #map {{ height: 100%; margin: 0; padding: 0; }}

            /* ESTILOS DA LEGENDA INTERATIVA */
            #legend {{
                position: absolute;
                top: 1rem;
                right: 1rem;
                background: rgba(255, 255, 255, 0.95);
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #ddd;
                box-shadow: 0 3px 10px rgba(0,0,0,0.2);
                z-index: 2000;
                font-family: Arial, sans-serif;
                max-width: 20rem;
                transition: all 0.3s ease;
            }}
            #legend h4 {{
                margin: 0 0 12px 0;
                text-align: center;
                color: #333;
                border-bottom: 1px solid #eee;
                padding-bottom: 8px;
            }}
            .legend-item {{
                display: flex;
                align-items: center;
                margin: 8px 0;
                padding: 5px;
                border-radius: 4px;
                transition: background 0.2s;
            }}
            .legend-item:hover {{
                background: #f5f5f5;
            }}
            .legend-color {{
                width: 22px;
                height: 18px;
                margin-right: 10px;
                border: 1px solid #888;
                border-radius: 3px;
            }}
            .legend-controls {{
                margin-left: auto;
                display: flex;
                align-items: center;
            }}
            .toggle-btn {{
                background: none;
                border: none;
                cursor: pointer;
                font-size: 14px;
                color: #666;
                margin-right: 8px;
            }}
            
            /* Controle de camadas */
            #layer-controls {{
                position: absolute;
                top: 10px;
                left: 10px;
                background: rgba(255, 255, 255, 0.9);
                padding: 10px;
                border-radius: 5px;
                z-index: 1000;
                font-size: 14px;
            }}
            
            /* NOVOS ESTILOS PARA MOBILE */
            #legend-mobile-header {{
                display: none;
                position: fixed;
                top: 10px;
                right: 50px;
                left: 50px;
                background: rgba(255,255,255,0.95);
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px 15px;
                z-index: 2000;
                font-family: Arial, sans-serif;
                font-weight: bold;
                text-align: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                cursor: pointer;
            }}
            
            @media (max-width: 900px) {{
                #legend {{
                    position: fixed;
                    top: 60px;
                    right: 50px;
                    left: 50px;
                    max-width: 100%;
                    max-height: 0;
                    overflow: hidden;
                    padding: 0;
                    opacity: 0;
                    transition: max-height 0.3s ease, opacity 0.3s ease, padding 0.3s ease;
                }}
                
                #legend.open {{
                    max-height: 500px;
                    opacity: 1;
                    padding: 15px;
                    overflow-y: auto;
                }}
                
                #legend-mobile-header {{
                    display: block;
                }}
                
                #legend-close {{
                    display: none;
                }}
                
                #legend-hamburger {{
                    display: none;
                }}
            }}
        </style>
      </head>
      <body>
        <div id="map" style="width: 100%; height: 800px;"></div>

        <!-- Cabeçalho da legenda para mobile -->
        <div id="legend-mobile-header">
          <i class="fas fa-layer-group"></i> Legenda
        </div>
        
        <!-- Legenda Interativa -->
        <div id="legend">
          <h4><i class="fas fa-layer-group"></i> Tipos de Propriedade</h4>
          {''.join([
              f'<div class="legend-item" id="legend-{categoria.replace(" ", "_")}">'
              f'<div class="legend-color" style="background:{cor};"></div>'
              f'<span>{categoria}</span>'
              f'<div class="legend-controls">'
              f'<button class="toggle-btn" data-category="{categoria}" title="Mostrar/Ocultar">'
              f'<i class="fas fa-eye"></i>'
              f'</button>'
              f'</div>'
              f'</div>'
              for categoria, cor in CORES.items()
          ])}
          <!-- Adiciona item na legenda para limites municipais -->
          <div class="legend-item" id="legend-boundaries">
              <div class="legend-color" style="background:none; border:2px solid #003366;"></div>
              <span>Limites Municipais</span>
              <div class="legend-controls">
              <button class="toggle-btn" id="toggle-boundaries" title="Mostrar/Ocultar">
                  <i class="fas fa-eye"></i>
              </button>
              </div>
          </div>
        </div>
        
        <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/pixi.js/5.3.10/pixi.min.js"></script>
        <script src="https://unpkg.com/leaflet-pixi-overlay@1.9.4/L.PixiOverlay.min.js"></script>
        <script>
              const CORES = {json.dumps(CORES)};
              const geojson = {geojson_str};
              const boundaryGeojson = {boundary_str};
              let map, pixiOverlay, boundaryLayer;
              const categoryContainers = {{}};
              const categoryBounds = {{}};

              // Função para calcular o centro do mapa
              function getMapCenter(geojson) {{
                for (const f of geojson.features) {{
                  const g = f.geometry;
                  if (g.type === "Polygon") {{
                    const [lng, lat] = g.coordinates[0][0];
                    return [lat, lng];
                  }} else if (g.type === "MultiPolygon") {{
                    const [lng, lat] = g.coordinates[0][0][0];
                    return [lat, lng];
                  }}
                }}
                return [-5.2, -39.0];
              }}

              // Função para extrair coordenadas e calcular bounds
              function extractCoordinates(feature) {{
                const coords = [];
                if (feature.geometry.type === "Polygon") {{
                  feature.geometry.coordinates[0].forEach(coord => coords.push([coord[1], coord[0]]));
                }} else if (feature.geometry.type === "MultiPolygon") {{
                  feature.geometry.coordinates[0][0].forEach(coord => coords.push([coord[1], coord[0]]));
                }}
                return coords;
              }}

              // Função principal para inicializar o mapa
              function initMap() {{
                const center = getMapCenter(geojson);
                map = L.map('map').setView(center, 10);
                
                L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
                  attribution: "© OpenStreetMap"
                }}).addTo(map);

                // Adiciona limites municipais se existirem
                if (boundaryGeojson && boundaryGeojson.features && boundaryGeojson.features.length > 0) {{
                  boundaryLayer = L.geoJSON(boundaryGeojson, {{
                    style: {{
                      color: "#003366",
                      weight: 2,
                      opacity: 0.8,
                      fill: false,
                      dashArray: "5, 5"
                    }},
                    interactive: false
                  }}).addTo(map);
                }}

                // Criar container principal
                const mainContainer = new PIXI.Container();
                
                // Criar containers individuais para cada categoria
                Object.keys(CORES).forEach(categoria => {{
                  categoryContainers[categoria] = new PIXI.Container();
                  categoryContainers[categoria].alpha = 0.6; // Opacidade padrão
                  categoryContainers[categoria].visible = true;
                  mainContainer.addChild(categoryContainers[categoria]);
                  categoryBounds[categoria] = L.latLngBounds();
                }});
                
                // Container para não classificados
                categoryContainers["Sem Classificação"] = new PIXI.Container();
                categoryContainers["Sem Classificação"].alpha = 0.6;
                categoryContainers["Sem Classificação"].visible = true;
                mainContainer.addChild(categoryContainers["Sem Classificação"]);
                categoryBounds["Sem Classificação"] = L.latLngBounds();

                // Criar overlay
                pixiOverlay = L.pixiOverlay(function(utils) {{
                  // Limpar containers
                  Object.values(categoryContainers).forEach(container => {{
                    container.removeChildren();
                  }});
                  
                  // Resetar bounds
                  Object.keys(categoryBounds).forEach(key => {{
                    categoryBounds[key] = L.latLngBounds();
                  }});
                  
                  // Processar cada feature
                  for (const feature of geojson.features) {{
                    const categoria = feature.properties.categoria || "Sem Classificação";
                    const cor = CORES[categoria] || "#aaa";
                    let polygons = [];
                    
                    if (feature.geometry.type === "Polygon") {{
                      polygons = [feature.geometry.coordinates];
                    }} else if (feature.geometry.type === "MultiPolygon") {{
                      polygons = feature.geometry.coordinates;
                    }}
                    
                    for (const polygon of polygons) {{
                      for (const ring of polygon) {{
                        const graphics = new PIXI.Graphics();
                        graphics.lineStyle(0.1, 0x000000, 1);
                        graphics.beginFill(PIXI.utils.string2hex(cor), categoryContainers[categoria].alpha);
                        
                        ring.forEach(([lng, lat], idx) => {{
                          const p = utils.latLngToLayerPoint([lat, lng]);
                          if (idx === 0) {{
                            graphics.moveTo(p.x, p.y);
                          }} else {{
                            graphics.lineTo(p.x, p.y);
                          }}
                          
                          // Atualizar bounds da categoria
                          categoryBounds[categoria].extend([lat, lng]);
                        }});
                        
                        graphics.closePath();
                        graphics.endFill();
                        categoryContainers[categoria].addChild(graphics);
                      }}
                    }}
                  }}
                  utils.getRenderer().render(mainContainer);
                }}, mainContainer).addTo(map);
              }}

              // Inicializar o mapa
              initMap();
              
              // ===== FUNÇÕES DE CONTROLE =====
              
              // Alternar visibilidade da camada
              function toggleLayer(categoria, visible) {{
                if (categoryContainers[categoria]) {{
                  categoryContainers[categoria].visible = visible;
                  
                  // Atualizar ícone do botão
                  const icon = document.querySelector(`.toggle-btn[data-category="${{categoria}}"] i`);
                  icon.className = visible ? "fas fa-eye" : "fas fa-eye-slash";
                  
                  pixiOverlay.redraw();
                }}
              }}
              
              // Alternar visibilidade dos limites municipais
              function toggleBoundaries(visible) {{
                if (boundaryLayer) {{
                  if (visible) {{
                    map.addLayer(boundaryLayer);
                  }} else {{
                    map.removeLayer(boundaryLayer);
                  }}
                  const icon = document.querySelector('#toggle-boundaries i');
                  icon.className = visible ? "fas fa-eye" : "fas fa-eye-slash";
                }}
              }}
              
            
              // Mostrar todas as camadas
              function showAllLayers() {{
                Object.keys(categoryContainers).forEach(categoria => {{
                  categoryContainers[categoria].visible = true;
                  const icon = document.querySelector(`.toggle-btn[data-category="${{categoria}}"] i`);
                  if (icon) icon.className = "fas fa-eye";
                }});
                toggleBoundaries(true);
                pixiOverlay.redraw();
              }}
              
              // Ocultar todas as camadas
              function hideAllLayers() {{
                Object.keys(categoryContainers).forEach(categoria => {{
                  categoryContainers[categoria].visible = false;
                  const icon = document.querySelector(`.toggle-btn[data-category="${{categoria}}"] i`);
                  if (icon) icon.className = "fas fa-eye-slash";
                }});
                toggleBoundaries(false);
                pixiOverlay.redraw();
              }}
              
              // ===== EVENT LISTENERS =====
              
              // Botões de toggle
              document.querySelectorAll('.toggle-btn').forEach(btn => {{
                btn.addEventListener('click', function() {{
                  const categoria = this.getAttribute('data-category');
                  if (categoria) {{
                    const currentlyVisible = categoryContainers[categoria].visible;
                    toggleLayer(categoria, !currentlyVisible);
                  }} else if (this.id === 'toggle-boundaries') {{
                    const currentlyVisible = map.hasLayer(boundaryLayer);
                    toggleBoundaries(!currentlyVisible);
                  }}
                }});
              }});

              // ===== LEGENDA MOBILE =====
              document.addEventListener('DOMContentLoaded', function() {{
                  var legend = document.getElementById('legend');
                  var mobileHeader = document.getElementById('legend-mobile-header');
                  
                  if (mobileHeader && legend) {{
                      mobileHeader.addEventListener('click', function() {{
                          legend.classList.toggle('open');
                          
                          // Rotaciona o ícone para indicar estado
                          var icon = this.querySelector('i');
                          if (legend.classList.contains('open')) {{
                              icon.classList.remove('fa-layer-group');
                              icon.classList.add('fa-chevron-up');
                          }} else {{
                              icon.classList.remove('fa-chevron-up');
                              icon.classList.add('fa-layer-group');
                          }}
                      }});
                      
                      // Fechar ao clicar fora
                      document.addEventListener('click', function(e) {{
                          if (window.innerWidth <= 900 && 
                              legend.classList.contains('open') && 
                              !legend.contains(e.target) && 
                              e.target !== mobileHeader && 
                              !mobileHeader.contains(e.target)) {{
                              legend.classList.remove('open');
                              var icon = mobileHeader.querySelector('i');
                              icon.classList.remove('fa-chevron-up');
                              icon.classList.add('fa-layer-group');
                          }}
                      }});
                  }}
              }});
              
            </script>
          </body>
        </html>
        """

    html(html_code, height=800, scrolling=True)