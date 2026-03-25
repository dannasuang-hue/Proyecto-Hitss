import pandas as pd
import numpy as np

print("Cargando localidades de Oaxaca y antenas de México...")
df_oaxaca = pd.read_csv("Base_CobInt_Oaxaca_Geolocalizada.csv")

df_antenas = pd.read_csv("antenas_mexico.csv/antenas_mexico.csv", header=None)
antenas_lon = df_antenas[6].values
antenas_lat = df_antenas[7].values

print(f"Total de antenas a evaluar: {len(antenas_lat)}")

# Fórmula matemática (Haversine) para medir distancias reales en la Tierra
def distancia_minima(lat_origen, lon_origen, lats_dest, lons_dest):
    # Convertir grados a radianes
    lat1, lon1 = np.radians(lat_origen), np.radians(lon_origen)
    lat2, lon2 = np.radians(lats_dest), np.radians(lons_dest)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Matemáticas de la curvatura terrestre
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    km = 6371 * c # Radio de la Tierra en km
    return np.min(km) # Nos devuelve la distancia a la antena más cercana

print("Calculando distancias reales, esto puede tomar un poco de tiempo...")

# Medir la distancia para cada pueblo de Oaxaca
distancias = []
for idx, row in df_oaxaca.iterrows():
    min_dist = distancia_minima(row['LAT_DECIMAL'], row['LON_DECIMAL'], antenas_lat, antenas_lon)
    distancias.append(min_dist)

df_oaxaca['DISTANCIA_KM_REAL'] = distancias

print("¡Distancias calculadas! Generando ranking final...")

# 1. Normalizar variables (escala 0 a 1)
df_oaxaca['POB_NORM'] = (df_oaxaca['POBTOT'] - df_oaxaca['POBTOT'].min()) / (df_oaxaca['POBTOT'].max() - df_oaxaca['POBTOT'].min())
df_oaxaca['REZAGO_NORM'] = (df_oaxaca['SCORE_REZAGO'] - df_oaxaca['SCORE_REZAGO'].min()) / (df_oaxaca['SCORE_REZAGO'].max() - df_oaxaca['SCORE_REZAGO'].min())

# Invertir distancia (0 km = 1 de score, estar más cerca es mejor)
max_dist = df_oaxaca['DISTANCIA_KM_REAL'].max()
min_dist = df_oaxaca['DISTANCIA_KM_REAL'].min()
df_oaxaca['DIST_NORM'] = 1 - ((df_oaxaca['DISTANCIA_KM_REAL'] - min_dist) / (max_dist - min_dist))

# 2. Aplicar los pesos del algoritmo
peso_pob = 0.4
peso_rezago = 0.4
peso_dist = 0.2

df_oaxaca['SCORE_PRIORIDAD'] = (df_oaxaca['POB_NORM'] * peso_pob) + (df_oaxaca['REZAGO_NORM'] * peso_rezago) + (df_oaxaca['DIST_NORM'] * peso_dist)

# 3. Ordenar a los ganadores definitivos
ranking = df_oaxaca.sort_values(by='SCORE_PRIORIDAD', ascending=False)
ranking['DISTANCIA_KM_REAL'] = ranking['DISTANCIA_KM_REAL'].round(2)

print("\n--- TOP 10 LOCALIDADES (DATOS 100% REALES Y PRECISOS) ---")
print(ranking[['NOM_LOC', 'POBTOT', 'GRADO_REZAGO', 'DISTANCIA_KM_REAL', 'SCORE_PRIORIDAD']].head(10))

# Guardar tu obra maestra
ranking.to_csv("Ranking_Final_Oaxaca_Real.csv", index=False, encoding='utf-8-sig')