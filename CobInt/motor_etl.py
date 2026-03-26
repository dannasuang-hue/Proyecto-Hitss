import pandas as pd
import numpy as np
import os
from sklearn.neighbors import BallTree

def dms_to_dd(dms_str):
    """Convierte coordenadas de GMS a Decimales."""
    try:
        dms_str = str(dms_str).replace('N', '').replace('W', '').replace('°', ' ').replace('\'', ' ').replace('"', ' ').strip()
        parts = dms_str.split()
        if len(parts) >= 3:
            return float(parts[0]) + float(parts[1])/60 + float(parts[2])/3600
        return np.nan
    except:
        return np.nan

def procesar_estado(id_estado_str, nombre_estado, nombre_pestana_coneval):
    """Pipeline ETL completo."""
    archivo_salida = f"Ranking_Final_{nombre_estado}_Real.csv"
    
    if os.path.exists(archivo_salida):
        return archivo_salida
        
    print(f"Iniciando extracción de datos para {nombre_estado}...")
    
    # 1 y 2. EXTRAER INEGI Y CONEVAL
    df_inegi = pd.read_csv('iter_00_cpv2020_csv/iter_00_cpv2020/conjunto_de_datos.zip', compression='zip', dtype={'ENTIDAD': str, 'MUN': str, 'LOC': str}, low_memory=False)
    
    df_estado = df_inegi[(df_inegi['ENTIDAD'] == id_estado_str) & (df_inegi['NOM_LOC'] != 'Total de la entidad')].copy()
    df_estado['CLAVE_UNICA'] = df_estado['ENTIDAD'].str.zfill(2) + df_estado['MUN'].str.zfill(3) + df_estado['LOC'].str.zfill(4)
    
    ruta_coneval = "IRS_loc_interior_entidades_2020/IRS_loc_interior_entidades_2020.xlsx"
    df_coneval = pd.read_excel(ruta_coneval, sheet_name=nombre_pestana_coneval, skiprows=4, dtype={'Clave localidad': str})
    
    # 3. CRUCE
    df_coneval['Clave localidad'] = df_coneval['Clave localidad'].astype(str).str.zfill(9)
    df_cruce = pd.merge(df_estado, df_coneval, left_on='CLAVE_UNICA', right_on='Clave localidad', how='inner')
    
    df_cruce = df_cruce.dropna(subset=['LATITUD', 'LONGITUD'])
    df_cruce['LAT_DECIMAL'] = df_cruce['LATITUD'].apply(dms_to_dd)
    df_cruce['LON_DECIMAL'] = df_cruce['LONGITUD'].apply(dms_to_dd) * -1 
    df_cruce = df_cruce.dropna(subset=['LAT_DECIMAL', 'LON_DECIMAL'])
    
    # 4. DISTANCIAS Y ANTENAS (Aquí estaba el error, ya está completo)
    ruta_antenas = "antenas_mexico.csv/antenas_mexico.csv" 
    nombres_columnas = ['radio', 'mcc', 'mnc', 'lac', 'cid', 'unit', 'lon', 'lat', 'range', 'samples', 'changeable', 'created', 'updated', 'averageSignal']
    df_antenas = pd.read_csv(ruta_antenas, header=None, names=nombres_columnas)
    
    print(f"Optimizando búsqueda espacial para {len(df_cruce)} localidades...")
    antenas_rad = np.deg2rad(df_antenas[['lat', 'lon']].values)
    pueblos_rad = np.deg2rad(df_cruce[['LAT_DECIMAL', 'LON_DECIMAL']].values)
    
    tree = BallTree(antenas_rad, metric='haversine')
    distancias_rad, indices = tree.query(pueblos_rad, k=1)
    
    df_cruce['DISTANCIA_KM_REAL'] = np.round(distancias_rad.flatten() * 6371.0, 2)
    # Guardamos las coordenadas de la antena
    df_cruce['LAT_ANTENA'] = df_antenas.iloc[indices.flatten()]['lat'].values
    df_cruce['LON_ANTENA'] = df_antenas.iloc[indices.flatten()]['lon'].values
    
    # 5. SCORING INTELIGENTE
    df_cruce['POBTOT'] = pd.to_numeric(df_cruce['POBTOT'], errors='coerce').fillna(0)
    df_cruce['LOG_POB'] = np.log1p(df_cruce['POBTOT'])
    max_log_pob = df_cruce['LOG_POB'].max()
    df_cruce['NORM_POB'] = df_cruce['LOG_POB'] / max_log_pob if max_log_pob > 0 else 0
    
    max_dist = df_cruce['DISTANCIA_KM_REAL'].max()
    df_cruce['NORM_DIST'] = df_cruce['DISTANCIA_KM_REAL'] / max_dist if max_dist > 0 else 0
    
    df_cruce['PENALIZACION'] = np.where(df_cruce['DISTANCIA_KM_REAL'] < 3.0, 0.1, 1.0)
    
    columnas_rezago = [col for col in df_cruce.columns if 'rezago' in col.lower()]
    if len(columnas_rezago) == 0:
        raise ValueError("No encontré la columna de rezago.")
    col_rezago = columnas_rezago[0]
    
    df_cruce[col_rezago] = pd.to_numeric(df_cruce[col_rezago], errors='coerce').fillna(0)
    min_rezago, max_rezago = df_cruce[col_rezago].min(), df_cruce[col_rezago].max()
    df_cruce['NORM_REZAGO'] = (df_cruce[col_rezago] - min_rezago) / (max_rezago - min_rezago) if max_rezago > min_rezago else 0

    score_bruto = (df_cruce['NORM_DIST'] * 0.5) + (df_cruce['NORM_REZAGO'] * 0.3) + (df_cruce['NORM_POB'] * 0.2)
    df_cruce['SCORE_PRIORIDAD'] = score_bruto * df_cruce['PENALIZACION']
    
    # 6. EXPORTAR
    df_final = df_cruce.sort_values(by='SCORE_PRIORIDAD', ascending=False)
    df_final = df_final.rename(columns={col_rezago: 'GRADO_REZAGO'})
    
    df_final.to_csv(archivo_salida, index=False)
    print(f"¡Proceso finalizado! Archivo guardado: {archivo_salida}")
    
    return archivo_salida
