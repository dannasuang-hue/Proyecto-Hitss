import streamlit as st
import pandas as pd
import numpy as np
import motor_etl
import networkx as nx
import pydeck as pdk
import requests

# --- FUNCIÓN MATEMÁTICA PARA MEDIR CABLE ---
def calcular_distancia_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

# --- NUEVA FUNCIÓN: API DE ELEVACIÓN NASA (GRATUITA) ---
def obtener_elevaciones_batch(df):
    """Consulta la API de OpenTopoData para obtener la altitud en metros."""
    lats = df['LAT_DECIMAL'].tolist()
    lons = df['LON_DECIMAL'].tolist()
    
    # Formateamos las coordenadas para la API: lat1,lon1|lat2,lon2...
    locations = "|".join([f"{lat},{lon}" for lat, lon in zip(lats, lons)])
    url = f"https://api.opentopodata.org/v1/srtm90m?locations={locations}"
    
    try:
        respuesta = requests.get(url, timeout=10)
        datos = respuesta.json()
        # Extraemos la elevación y la devolvemos como lista
        return [resultado['elevation'] for resultado in datos['results']]
    except Exception as e:
        # PLAN B: Si la API gratuita falla o se satura, asumimos terreno plano (0 metros)
        return [0] * len(lats)

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="COBINT - Inteligencia de Red", layout="wide")

st.markdown("""
    <style>
        /* Fondo gris moderno en toda la página */
        .stApp {
            background-color: #f0f4f8 !important;
            font-family: 'Segoe UI', sans-serif !important;
        }

        /* Ocultar la barra superior, dejar botón menú */
        header { background: transparent !important; }
        #MainMenu { visibility: hidden !important; }
        footer { visibility: hidden !important; }
        div[data-testid="stStatusWidget"] { visibility: hidden !important; }

        /* CABECERA LIMPIA */
        .corporate-title {
            color: #1e3a8a;
            font-size: 3rem;
            font-weight: 800;
            margin-bottom: 0px;
            letter-spacing: 1px;
        }
        .corporate-subtitle {
            color: #64748b;
            font-size: 1.1rem;
            font-weight: 400;
            margin-top: 5px;
            margin-bottom: 30px;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 20px;
        }

        /* CAJA DE DESCRIPCIÓN EJECUTIVA */
        .description-box {
            background-color: white;
            padding: 20px 25px;
            border-left: 5px solid #1e3a8a;
            border-radius: 6px;
            box-shadow: 0px 2px 10px rgba(0,0,0,0.03);
            margin-bottom: 25px;
            color: #334155;
            font-size: 1.05rem;
            line-height: 1.6;
        }

        /* Estilo de los Botones */
        button[kind="primary"] {
            background-color: #1e3a8a !important;
            color: white !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 12px 24px !important;
            font-weight: 600 !important;
            letter-spacing: 1px !important;
            width: 100% !important;
            transition: 0.3s !important;
        }
        button[kind="primary"]:hover {
            background-color: #0f172a !important;
            box-shadow: 0px 4px 15px rgba(30, 58, 138, 0.3) !important;
        }

        /* Tarjetas de Métricas y Contenedores */
        div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
            background-color: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.03);
            margin-bottom: 30px;
            border: 1px solid rgba(0,0,0,0.02);
        }
        div[data-testid="metric-container"] {
            background-color: white !important;
            border: 1px solid #e2e8f0 !important;
            padding: 15px !important;
            border-radius: 8px !important;
            box-shadow: 0px 2px 8px rgba(0,0,0,0.02) !important;
        }
        div[data-testid="stMetricValue"] {
            color: #1e3a8a !important;
            font-weight: 700 !important;
        }

        /* Títulos de sección limpios */
        .section-title {
            color: #020617 !important;
            border-bottom: 2px solid #cbd5e1 !important;
            padding-bottom: 10px !important;
            margin-bottom: 20px !important;
            font-weight: 700 !important;
            font-size: 1.4rem !important;
        }

        /* --- NUEVA SIMBOLOGÍA TIPO GOOGLE MAPS --- */
        .legend-container {
            display: flex;
            gap: 12px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        .legend-pill {
            background-color: white;
            border: 1px solid #cbd5e1;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9rem;
            color: #334155;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
        }
        .legend-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
        }
    </style>
""", unsafe_allow_html=True)

# 3. NUEVA CABECERA MINIMALISTA
st.markdown("""
    <h1 class="corporate-title">CobInt</h1>
    <div class="corporate-subtitle">Inteligencia de red para Transformación Digital • Desarrollo Global Hitss</div>
""", unsafe_allow_html=True)

# 4. CONFIGURACIÓN LATERAL Y DICCIONARIO
estados_mexico = {
    '01': ('Aguascalientes', 'Aguascalientes'), '02': ('Baja California', 'Baja California'), '03': ('Baja California Sur', 'Baja California Sur'), '04': ('Campeche', 'Campeche'), '05': ('Coahuila', 'Coahuila de Zaragoza'), '06': ('Colima', 'Colima'), '07': ('Chiapas', 'Chiapas'), '08': ('Chihuahua', 'Chihuahua'), '09': ('Ciudad de México', 'Ciudad de México'), '10': ('Durango', 'Durango'), '11': ('Guanajuato', 'Guanajuato'), '12': ('Guerrero', 'Guerrero'), '13': ('Hidalgo', 'Hidalgo'), '14': ('Jalisco', 'Jalisco'), '15': ('Estado de México', 'Estado de México'), '16': ('Michoacán', 'Michoacán de Ocampo'), '17': ('Morelos', 'Morelos'), '18': ('Nayarit', 'Nayarit'), '19': ('Nuevo León', 'Nuevo León'), '20': ('Oaxaca', 'Oaxaca'), '21': ('Puebla', 'Puebla'), '22': ('Querétaro', 'Querétaro'), '23': ('Quintana Roo', 'Quintana Roo'), '24': ('San Luis Potosí', 'San Luis Potosí'), '25': ('Sinaloa', 'Sinaloa'), '26': ('Sonora', 'Sonora'), '27': ('Tabasco', 'Tabasco'), '28': ('Tamaulipas', 'Tamaulipas'), '29': ('Tlaxcala', 'Tlaxcala'), '30': ('Veracruz', 'Veracruz de Ignacio de la Llave'), '31': ('Yucatán', 'Yucatán'), '32': ('Zacatecas', 'Zacatecas')
}

st.sidebar.subheader("Panel de Control") 
id_seleccionado = st.sidebar.selectbox(
    "1. Selecciona el estado a analizar:",
    options=list(estados_mexico.keys()),
    format_func=lambda x: estados_mexico[x][0]
)

nombre_estado = estados_mexico[id_seleccionado][0]
pestana_coneval = estados_mexico[id_seleccionado][1]

st.markdown(f'<h3 class="section-title">Análisis en tiempo real: <b>{nombre_estado}</b></h3>', unsafe_allow_html=True)

# --- DESCRIPCIÓN EJECUTIVA ANTES DEL BOTÓN ---
st.markdown("""
    <div class="description-box">
        <b>Plataforma analítica para la optimización de infraestructura de telecomunicaciones.</b><br>
        CobInt procesa datos sociodemográficos y geolocalización de antenas existentes para priorizar zonas de rezago. Al ejecutar el análisis, el motor calcula automáticamente el enrutamiento óptimo de red de fibra óptica utilizando teoría de grafos y estima el CAPEX necesario para el despliegue.
    </div>
""", unsafe_allow_html=True)

# 5. LÓGICA DE BOTÓN Y CÁLCULO
if st.button("CALCULAR RUTAS Y PRIORIDAD", type="primary"):
    with st.container():
        with st.spinner(f"Optimizando infraestructura en {nombre_estado}..."):
            try:
                archivo_resultado = motor_etl.procesar_estado(id_seleccionado, nombre_estado, pestana_coneval)
                df_estado = pd.read_csv(archivo_resultado)
                df_nodos = df_estado.head(20).reset_index(drop=True)

                st.success(f"Análisis optimizado para {nombre_estado} finalizado.")

                # =========================================================
                # --- NUEVO CÁLCULO 3D CON ELEVACIÓN Y PENALIZACIÓN ---
                # =========================================================
                df_nodos['ELEVACION_M'] = obtener_elevaciones_batch(df_nodos)
                
                G = nx.Graph()
                costo_base_km_mxn = 150000 

                for i, row in df_nodos.iterrows():
                    G.add_node(i, pos=(row['LON_DECIMAL'], row['LAT_DECIMAL']), nom_loc=row['NOM_LOC'], pob=row['POBTOT'], elev=row['ELEVACION_M'])
                
                for i in G.nodes():
                    for j in G.nodes():
                        if i < j:
                            lon1, lat1 = G.nodes[i]['pos']
                            lon2, lat2 = G.nodes[j]['pos']
                            elev1 = G.nodes[i]['elev']
                            elev2 = G.nodes[j]['elev']
                            
                            # Distancia 2D
                            dist_2d_km = calcular_distancia_km(lat1, lon1, lat2, lon2)
                            
                            # Diferencia de altura en KM para Pitágoras
                            d_elev_km = abs(elev1 - elev2) / 1000.0
                            dist_3d_km = np.sqrt(dist_2d_km**2 + d_elev_km**2)
                            
                            # Cálculo de pendiente y penalización de costo
                            pendiente = (d_elev_km / dist_2d_km) * 100 if dist_2d_km > 0 else 0
                            multiplicador_dificultad = 1 + (pendiente * 0.025)
                            
                            costo_ruta = dist_3d_km * costo_base_km_mxn * multiplicador_dificultad
                            
                            # Añadimos la ruta considerando el costo monetario real
                            G.add_edge(i, j, weight=costo_ruta, dist_3d=dist_3d_km, costo=costo_ruta)
                
                # El árbol buscará la ruta más barata (evitando montañas muy empinadas)
                T = nx.minimum_spanning_tree(G)
                
                # Sumamos costos de Fibra Nueva (3D + Penalización)
                costo_fibra_cian = sum(T.edges[u, v]['costo'] for u, v in T.edges())
                
                # Sumamos costos de Troncales (Asumimos costo base por ahora)
                km_troncal_amarillo = df_nodos['DISTANCIA_KM_REAL'].sum()
                costo_troncal = km_troncal_amarillo * costo_base_km_mxn
                
                presupuesto_estimado = costo_fibra_cian + costo_troncal

                # --- RENDERIZADO DEL DASHBOARD ---
                st.markdown('<h3 class="section-title">Resumen de Ingeniería y CAPEX</h3>', unsafe_allow_html=True)
                m1, m2, m3 = st.columns(3)
                m1.metric("Localidades Prioritarias", f"{len(df_nodos)}")
                m2.metric("Población a Conectar", f"{int(df_nodos['POBTOT'].sum()):,}")
                m3.metric("CAPEX Estimado", f"${presupuesto_estimado:,.0f} MXN")
                
                st.markdown('<h3 class="section-title">Detalle de Localidades Prioritarias</h3>', unsafe_allow_html=True)
                df_mostrar = df_nodos[['NOM_LOC', 'POBTOT', 'GRADO_REZAGO', 'DISTANCIA_KM_REAL', 'SCORE_PRIORIDAD', 'ELEVACION_M']].copy()
                df_mostrar['ELEVACION_M'] = df_mostrar['ELEVACION_M'].round(1) # Redondeamos la elevación
                df_mostrar = df_mostrar.rename(columns={'NOM_LOC': 'Comunidad', 'POBTOT': 'Habitantes', 'GRADO_REZAGO': 'Rezago', 'DISTANCIA_KM_REAL': 'Distancia a Red (km)', 'SCORE_PRIORIDAD': 'Puntaje Urgencia', 'ELEVACION_M': 'Altitud (msnm)'})
                
                st.dataframe(df_mostrar, use_container_width=True)
                
                csv_export = df_estado.head(100).to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Descargar Reporte Completo (CSV)",
                    data=csv_export,
                    file_name=f'Reporte_COBINT_{nombre_estado}_3D.csv',
                    mime='text/csv'
                )

                st.markdown('<h3 class="section-title">Mapa Interactivo de Rutas y Backhaul</h3>', unsafe_allow_html=True)
                
                # --- LEYENDA TIPO GOOGLE MAPS (Pills) ---
                st.markdown("""
                <div class="legend-container">
                    <div class="legend-pill"><span class="legend-dot" style="background-color: rgb(180, 50, 50);"></span> Zonas Críticas</div>
                    <div class="legend-pill"><span class="legend-dot" style="background-color: rgb(90, 120, 140);"></span> Fibra Nueva</div>
                    <div class="legend-pill"><span class="legend-dot" style="background-color: rgb(100, 140, 80);"></span> Antena Existente</div>
                    <div class="legend-pill"><span class="legend-dot" style="background-color: rgb(200, 160, 50);"></span> Enlace Troncal</div>
                </div>
                """, unsafe_allow_html=True)

                # Colores RGB (Mate/Desaturados)
                color_cian_fibra = [90, 120, 140, 200]       
                color_amarillo_troncal = [200, 160, 50, 200] 
                color_rojo_nodo = [180, 50, 50, 230]         
                color_verde_antena = [100, 140, 80, 230]     
                color_borde_blanco = [255, 255, 255, 255] 

                # Preparamos rutas del grafo
                rutas = [{"origen": [G.nodes[u]['pos'][0], G.nodes[u]['pos'][1]], "destino": [G.nodes[v]['pos'][0], G.nodes[v]['pos'][1]]} for u, v in T.edges()]
                rutas_troncales = [{"origen": [row['LON_DECIMAL'], row['LAT_DECIMAL']], "destino": [row['LON_ANTENA'], row['LAT_ANTENA']]} for i, row in df_nodos.iterrows()]

                capa_fibra = pdk.Layer("LineLayer", pd.DataFrame(rutas), get_source_position="origen", get_target_position="destino", get_color=color_cian_fibra, get_width=3, pickable=False)
                capa_troncal = pdk.Layer("LineLayer", pd.DataFrame(rutas_troncales), get_source_position="origen", get_target_position="destino", get_color=color_amarillo_troncal, get_width=4, pickable=False)
                capa_nodos = pdk.Layer("ScatterplotLayer", df_nodos, get_position="[LON_DECIMAL, LAT_DECIMAL]", get_radius=1200, get_fill_color=color_rojo_nodo, get_line_color=color_borde_blanco, stroked=True, get_line_width=150, pickable=True)
                capa_antenas = pdk.Layer("ScatterplotLayer", df_nodos, get_position="[LON_ANTENA, LAT_ANTENA]", get_radius=2000, get_fill_color=color_verde_antena, get_line_color=color_borde_blanco, stroked=True, get_line_width=250, pickable=True)

                vista_inicial = pdk.ViewState(latitude=df_nodos['LAT_DECIMAL'].mean(), longitude=df_nodos['LON_DECIMAL'].mean(), zoom=7.5, pitch=55)

                st.pydeck_chart(pdk.Deck(
                    map_style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json", 
                    initial_view_state=vista_inicial, 
                    layers=[capa_fibra, capa_nodos, capa_troncal, capa_antenas], 
                    tooltip={"html": "<b>Comunidad:</b> {NOM_LOC} <br/> <b>Habitantes a conectar:</b> {POBTOT} <br/> <b>Altitud:</b> {ELEVACION_M} msnm"}
                ))

            except Exception as e:
                st.error(f"Error crítico en el proceso: {e}")
                st.info("Revisa la terminal para detalles técnicos.")