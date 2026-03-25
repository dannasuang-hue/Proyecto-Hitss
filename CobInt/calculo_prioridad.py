import pandas as pd
import numpy as np # Importamos numpy para simular la distancia

# 1. Cargar nuestra súper tabla de ayer
df = pd.read_csv("Base_CobInt_Oaxaca_Limpia.csv")

print(f"Procesando {len(df)} localidades de Oaxaca...")

# 2. Normalizar los datos (Escala 0 a 1)
# Esto hace que la comparación sea justa
df['POB_NORM'] = (df['POBTOT'] - df['POBTOT'].min()) / (df['POBTOT'].max() - df['POBTOT'].min())
df['REZAGO_NORM'] = (df['SCORE_REZAGO'] - df['SCORE_REZAGO'].min()) / (df['SCORE_REZAGO'].max() - df['SCORE_REZAGO'].min())

# 3. Calcular el Score Final de Prioridad
# Aquí tú decides: ¿Qué es más importante? 
# Por ahora pondremos 50% población y 50% rezago
peso_pob = 0.5
peso_rezago = 0.5

df['SCORE_PRIORIDAD'] = (df['POB_NORM'] * peso_pob) + (df['REZAGO_NORM'] * peso_rezago)

# 4. Ordenar para ver quiénes urgen más
ranking = df.sort_values(by='SCORE_PRIORIDAD', ascending=False)

print("\n--- TOP 10 LOCALIDADES CON MAYOR PRIORIDAD DE COBERTURA ---")
print(ranking[['NOM_LOC', 'POBTOT', 'GRADO_REZAGO', 'SCORE_PRIORIDAD']].head(10))

# Guardar el resultado final
ranking.to_csv("Ranking_Prioridad_Oaxaca.csv", index=False, encoding='utf-8-sig')


# 1. Cargar nuestra súper tabla maestra que hicimos ayer
df = pd.read_csv("Base_CobInt_Oaxaca_Limpia.csv")

print(f"Procesando {len(df)} localidades con simulación de distancia...")

# 2. Normalizar Población y Rezago (Escala 0 a 1 para que sea justo)
df['POB_NORM'] = (df['POBTOT'] - df['POBTOT'].min()) / (df['POBTOT'].max() - df['POBTOT'].min())
df['REZAGO_NORM'] = (df['SCORE_REZAGO'] - df['SCORE_REZAGO'].min()) / (df['SCORE_REZAGO'].max() - df['SCORE_REZAGO'].min())

# 3. MOCKING (Simulación): Inventar una distancia a la red en km (entre 1km y 50km)
np.random.seed(42) # Esto asegura que siempre nos dé los mismos números aleatorios para la prueba
df['DISTANCIA_KM'] = np.random.uniform(1, 50, len(df))

# 4. Normalizar la distancia (¡Ojo! Invertimos la escala porque estar Cerca = Mejor Score)
df['DIST_NORM'] = 1 - ((df['DISTANCIA_KM'] - df['DISTANCIA_KM'].min()) / (df['DISTANCIA_KM'].max() - df['DISTANCIA_KM'].min()))

# 5. Calcular el Score Final con 3 variables
# Pesos: Población 40%, Rezago Social 40%, Cercanía a la red 20%
peso_pob = 0.4
peso_rezago = 0.4
peso_dist = 0.2

df['SCORE_PRIORIDAD'] = (df['POB_NORM'] * peso_pob) + (df['REZAGO_NORM'] * peso_rezago) + (df['DIST_NORM'] * peso_dist)

# 6. Ordenar a los ganadores definitivos
ranking = df.sort_values(by='SCORE_PRIORIDAD', ascending=False)

print("\n--- TOP 5 LOCALIDADES (CON DISTANCIA SIMULADA) ---")
# Redondeamos la distancia a 1 decimal para que se vea limpio
ranking['DISTANCIA_KM'] = ranking['DISTANCIA_KM'].round(1) 
print(ranking[['NOM_LOC', 'POBTOT', 'GRADO_REZAGO', 'DISTANCIA_KM', 'SCORE_PRIORIDAD']].head(5))

# Guardamos el archivo final
ranking.to_csv("Ranking_Final_Oaxaca_Simulado.csv", index=False, encoding='utf-8-sig')
print("\n¡Archivo 'Ranking_Final_Oaxaca_Simulado.csv' guardado con éxito!")