import folium
import pandas as pd
from folium.plugins import HeatMap
from branca.element import Template, MacroElement

print("Cargando base de datos geolocalizada...")
df = pd.read_csv("Ranking_Final_Oaxaca_Real.csv")

# 1. Configuración del mapa base
lat_centro = df['LAT_DECIMAL'].mean()
lon_centro = df['LON_DECIMAL'].mean()
mapa = folium.Map(location=[lat_centro, lon_centro], zoom_start=8, tiles='cartodbdark_matter')

# 2. Generar Mapa de Calor (Heatmap)
print("Generando capa de calor...")
datos_calor = df[['LAT_DECIMAL', 'LON_DECIMAL', 'SCORE_PRIORIDAD']].values.tolist()
HeatMap(datos_calor, radius=15, blur=20, min_opacity=0.5).add_to(mapa)

# 3. REINCORPORAR IDENTIFICADORES (Marcadores del Top 10)
print("Colocando identificadores para las 10 zonas más críticas...")
# Tomamos las primeras 10 filas del ranking
for idx, row in df.head(10).iterrows():
    folium.Marker(
        location=[row['LAT_DECIMAL'], row['LON_DECIMAL']],
        popup=folium.Popup(f"""
            <div style='font-family: Arial; font-size: 12px;'>
                <b>Localidad:</b> {row['NOM_LOC']}<br>
                <b>Población:</b> {int(row['POBTOT'])}<br>
                <b>Prioridad:</b> {round(row['SCORE_PRIORIDAD'], 3)}<br>
                <b>Distancia a Red:</b> {row['DISTANCIA_KM_REAL']} km
            </div>
        """, max_width=250),
        tooltip=row['NOM_LOC'],
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(mapa)

# 4. Inyectar la Leyenda (Simbología)
template = """
{% macro html(this, kwargs) %}
<div id='maplegend' class='maplegend' 
    style='position: absolute; z-index:9999; border:2px solid grey; background-color:rgba(255, 255, 255, 0.8);
     border-radius:6px; padding: 10px; font-size:14px; right: 20px; bottom: 20px; font-family: Arial;'>
     
<div class='legend-title' style='font-weight: bold; font-size: 15px; margin-bottom: 8px;'>Simbología: Prioridad</div>
<div class='legend-scale'>
  <ul class='legend-labels' style='margin: 0; padding: 0; list-style: none;'>
    <li style='margin-bottom: 3px;'><span style='display: inline-block; width: 30px; height: 15px; background: #FF0000; border: 1px solid #999; margin-right: 5px;'></span>Alta</li>
    <li style='margin-bottom: 3px;'><span style='display: inline-block; width: 30px; height: 15px; background: #00FF00; border: 1px solid #999; margin-right: 5px;'></span>Media</li>
    <li style='margin-bottom: 3px;'><span style='display: inline-block; width: 30px; height: 15px; background: #0000FF; border: 1px solid #999; margin-right: 5px;'></span>Baja</li>
  </ul>
</div>
<div style='font-size: 10px; color: #555; margin-top: 5px;'>Icono rojo: Top 10 Localidades Críticas</div>
</div>
{% endmacro %}
"""

macro = MacroElement()
macro._template = Template(template)
mapa.get_root().add_child(macro)

# 5. Guardar el archivo final
nombre_archivo = "Mapa_Prioridad_Completo.html"
mapa.save(nombre_archivo)
print(f"\n¡Éxito! Mapa generado con calor, leyenda e identificadores: {nombre_archivo}")
