import os
import numpy as np
import pandas as pd
import pickle
from tensorflow.keras.models import load_model
from datetime import datetime, timedelta

# Mapeo manual de los nombres de los meses en español
meses_espanol = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

def realizar_predicciones(cantidad_meses, fecha_actual):
    # Convertir la fecha actual de cadena a datetime
    current_date = datetime.strptime(fecha_actual, "%Y-%m-%d")
    
    # Determinar el primer mes completo siguiente
    if current_date.month == 12:
        next_month_date = datetime(current_date.year + 1, 1, 1)
    else:
        next_month_date = datetime(current_date.year, current_date.month + 1, 1)

    # Cargar el DataFrame desde el archivo CSV
    df = pd.read_csv('lista.csv')

    # Convertir la columna 'Fecha' a tipo datetime
    df['Fecha'] = pd.to_datetime(df['Fecha'])

    # Extraer el año y el mes de la fecha
    df['Año'] = df['Fecha'].dt.year
    df['Mes'] = df['Fecha'].dt.month

    # Agrupar por año y mes y sumar la cantidad de productos vendidos
    ventas_por_mes_anio = df.groupby(['Año', 'Mes']).agg({'Cantidad': 'sum'}).reset_index()

    # Pivotar el DataFrame para mostrar los meses como columnas
    ventas_pivot = ventas_por_mes_anio.pivot(index='Año', columns='Mes', values='Cantidad')

    # Renombrar las columnas de los meses para mayor claridad
    ventas_pivot.columns = [f'Mes {col}' for col in ventas_pivot.columns]

    # Rellenar valores faltantes con 0 (si algún mes no tuvo ventas)
    ventas_pivot = ventas_pivot.fillna(0).astype(int)

    # Calcular la media de productos vendidos por mes
    media_por_mes = ventas_pivot.mean().astype(int)

    # Cargar el modelo 
    model = load_model('model_lstm_diversified_v3.h5')

    # Cargar los encoders y scaler guardados
    with open('encodersFUTURO.pkl', 'rb') as f:
        label_encoders = pickle.load(f)

    with open('scalerFUTURO.pkl', 'rb') as f:
        scaler = pickle.load(f)

    X = np.load('XFUTURO.npy')
    y = np.load('yFUTURO.npy')
    split_ratio = 0.8
    split = int(len(X) * split_ratio)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    # Crear la carpeta para guardar las predicciones si no existe
    carpeta_predicciones = 'PRONOSTICO_MES'
    if not os.path.exists(carpeta_predicciones):
        os.makedirs(carpeta_predicciones)

    # Función para realizar múltiples predicciones por mes con variabilidad y forzar diversidad
    def predict_multiple_products_per_month(model, initial_sequence, num_months, media_por_mes):
        all_predictions = []
        product_counts = {}  # Para almacenar el conteo de productos por mes
        previous_product_type = None  # Para rastrear el tipo de producto predicho anteriormente
        previous_color = None  # Para rastrear el color de producto predicho anteriormente
        previous_material = None  # Para rastrear el material de producto predicho anteriormente

        statistics = {}  # Para almacenar las estadísticas por mes

        for month in range(num_months):
            monthly_predictions = []
            current_seq = initial_sequence.copy()  # Asegurar que la secuencia no se modifique en el bucle

            # Determinar el mes y año actual
            current_month = (next_month_date.month + month - 1) % 12 + 1
            current_year = next_month_date.year + ((next_month_date.month + month - 1) // 12)
            month_name = f'{meses_espanol[current_month]}_{current_year}'
            csv_filename = os.path.join(carpeta_predicciones, f'predicciones_{month_name}.csv')

            # Verificar si ya existe el archivo CSV para este mes
            if os.path.exists(csv_filename):
                print(f"El archivo {csv_filename} ya existe, omitiendo la predicción para este mes.")
                continue

            num_products_per_month = media_por_mes.get(f'Mes {current_month}', 0)  # Usar la media de productos vendidos por mes

            for _ in range(num_products_per_month):
                # Realizar la predicción
                pred = model.predict(current_seq[np.newaxis, :, :])[0, -1]  # Tomar solo la última predicción

                prob_dist_tipo = np.array([0.2 if i != previous_product_type else 0.01 for i in range(len(label_encoders['Tipo'].classes_))])
                prob_dist_tipo = prob_dist_tipo / prob_dist_tipo.sum()  # Normalizar para que sume 1
                pred[0] = np.random.choice(np.arange(len(label_encoders['Tipo'].classes_)), p=prob_dist_tipo)
                previous_product_type = pred[0]  # Actualizar el tipo de producto anterior

                prob_dist_color = np.array([0.2 if i != previous_color else 0.01 for i in range(len(label_encoders['Color'].classes_))])
                prob_dist_color = prob_dist_color / prob_dist_color.sum()
                pred[1] = np.random.choice(np.arange(len(label_encoders['Color'].classes_)), p=prob_dist_color)
                previous_color = pred[1]  # Actualizar el color de producto anterior

                prob_dist_material = np.array([0.2 if i != previous_material else 0.01 for i in range(len(label_encoders['Material'].classes_))])
                prob_dist_material = prob_dist_material / prob_dist_material.sum()
                pred[2] = np.random.choice(np.arange(len(label_encoders['Material'].classes_)), p=prob_dist_material)
                previous_material = pred[2]  # Actualizar el material de producto anterior

                pred += np.random.normal(scale=0.1, size=pred.shape)  # Introducir ligera variación
                monthly_predictions.append(pred)

                # Actualizar la secuencia con la predicción
                current_seq = np.roll(current_seq, -1, axis=0)
                current_seq[-1] = pred  # Actualizar la última fila con la predicción

            all_predictions.append(monthly_predictions)
            product_counts[current_month] = len(monthly_predictions)  # Guardar el conteo de productos predichos por mes

            # Calcular estadísticas de interés
            statistics[month_name] = {
                'total_predictions': len(monthly_predictions),
                # Puedes agregar más estadísticas aquí si es necesario
            }

            # Formatear las predicciones
            formatted_predictions = format_predictions([monthly_predictions], next_month_date)

            # Guardar las predicciones en un archivo CSV
            df_predictions = pd.DataFrame(formatted_predictions)
            df_predictions.to_csv(csv_filename, index=False)
            print(f"Predicciones guardadas en el archivo {csv_filename}")

        return all_predictions, product_counts, statistics


    def custom_round(value):
        if value < 1.25:
            return 1
        elif value >= 1.25 and value < 1.36:
            return 2
        else:
            return 3

    # Función para formatear las predicciones en el formato original
    def format_predictions(predictions, initial_date):
        formatted_predictions = []
        for i, month_preds in enumerate(predictions):
            date = initial_date + timedelta(days=30 * i)  # Ajustar la fecha para cada mes
            for pred in month_preds:
                formatted_predictions.append({
                    'Fecha': date.strftime('%Y-%m'),
                    'Tipo': label_encoders['Tipo'].inverse_transform([int(round(pred[0]))])[0],
                    'Color': label_encoders['Color'].inverse_transform([int(round(pred[1]))])[0],
                    'Material': label_encoders['Material'].inverse_transform([int(round(pred[2]))])[0],
                    #'Cantidad': scaler.inverse_transform([[pred[4]]])[0, 0]
                    'Cantidad': custom_round(scaler.inverse_transform([[pred[4]]])[0, 0])
                })
        return formatted_predictions

    # Seleccionar una secuencia inicial para la predicción
    initial_sequence = X_val[np.random.randint(0, len(X_val))]  

    # Realizar las predicciones comenzando desde el mes siguiente al actual
    predict_multiple_products_per_month(model, initial_sequence, cantidad_meses, media_por_mes)

