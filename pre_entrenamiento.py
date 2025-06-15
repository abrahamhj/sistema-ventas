# pre_entrenamiento.py

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
import pickle
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dropout, TimeDistributed, Dense
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.optimizers import Adam
from db import get_db_connection
import matplotlib.pyplot as plt
import os

import matplotlib
matplotlib.use('Agg')

def descargar_datos_ventas():
    """Descargar los datos de la tabla ventas de la base de datos y guardarlos como CSV."""
    query = "SELECT ID, Tipo, Color, Material, Agregado, Cantidad, PrecioU, PrecioT, Fecha FROM ventas"
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    ventas = cursor.fetchall()
    cursor.close()
    conn.close()

    if not os.path.exists('descarga_csv'):
        os.makedirs('descarga_csv')

    # Convertir los datos a un DataFrame
    ventas_df = pd.DataFrame(ventas)
    ventas_df.to_csv('descarga_csv/datos_descargados.csv', index=False)
    print("Datos de ventas descargados y guardados en descarga_csv/datos_descargados.csv")

def combinar_csvs():
    """Unir el archivo descargado de ventas con el archivo lista.csv."""
    ventas_descargadas = pd.read_csv('descarga_csv/datos_descargados.csv')

    lista_path = 'lista.csv'
    if not os.path.exists(lista_path):
        print(f"Archivo {lista_path} no encontrado, creando uno vacío.")
        ventas_lista = pd.DataFrame(columns=ventas_descargadas.columns)
    else:
        ventas_lista = pd.read_csv(lista_path)

    ventas_combinadas = pd.concat([ventas_lista, ventas_descargadas])
    ventas_combinadas.to_csv(lista_path, index=False)
    print(f"Archivos combinados guardados en {lista_path}")

def preprocesar_datos():
    """Preprocesar los datos para entrenamiento."""
    descargar_datos_ventas()
    combinar_csvs()

    df = pd.read_csv('lista.csv')
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df['TotalVentas'] = df['Cantidad'] * df['PrecioU']

    producto_totales = df.groupby('Tipo')['TotalVentas'].sum().sort_values(ascending=False)
    producto_totales_cumsum = producto_totales.cumsum()
    total_ventas = producto_totales_cumsum.iloc[-1]
    producto_totales_percentage = producto_totales_cumsum / total_ventas
    productos_80 = producto_totales_percentage[producto_totales_percentage <= 0.8].index

    df_pareto = df[df['Tipo'].isin(productos_80)]
    productos_menos_comunes = df[~df['Tipo'].isin(productos_80)]['Tipo'].unique()
    df_minority = df[df['Tipo'].isin(productos_menos_comunes)]

    df_diverse = pd.concat([df_pareto, df_minority])
    df_diverse['YearMonth'] = df_diverse['Fecha'].dt.to_period('M')

    label_encoders = {}
    for column in ['Tipo', 'Color', 'Material', 'Agregado']:
        le = LabelEncoder()
        df_diverse[column] = le.fit_transform(df_diverse[column])
        label_encoders[column] = le

    scaler = MinMaxScaler()
    df_diverse['Cantidad'] = scaler.fit_transform(df_diverse[['Cantidad']])

    with open('encodersFUTURO.pkl', 'wb') as f:
        pickle.dump(label_encoders, f)

    with open('scalerFUTURO.pkl', 'wb') as f:
        pickle.dump(scaler, f)

    grouped = df_diverse.groupby('YearMonth').apply(lambda x: x[['Tipo', 'Color', 'Material', 'Agregado', 'Cantidad']].values)

    max_len = max(grouped.apply(len))
    grouped_padded = grouped.apply(lambda x: np.pad(x, ((0, max_len - len(x)), (0, 0)), 'constant'))

    def create_sequences(data, seq_length):
        xs, ys = [], []
        for i in range(len(data) - seq_length):
            x = np.vstack(data[i:(i+seq_length)])
            y = np.vstack(data[(i+1):(i+seq_length+1)])
            xs.append(x)
            ys.append(y)
        return np.array(xs), np.array(ys)

    seq_length = 12
    X, y = create_sequences(grouped_padded, seq_length)

    np.save('XFUTURO.npy', X)
    np.save('yFUTURO.npy', y)

    print("Preprocesamiento completado y archivos guardados.")

def entrenar_modelo():
    """Entrenar el modelo LSTM con los datos preprocesados."""
    X = np.load('XFUTURO.npy')
    y = np.load('yFUTURO.npy')

    split_ratio = 0.8
    split = int(len(X) * split_ratio)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    seq_length = 6  # Tamaño de secuencia ajustado
    X_train = X_train[:, :seq_length, :]
    X_val = X_val[:, :seq_length, :]
    y_train = y_train[:, :seq_length, :]
    y_val = y_val[:, :seq_length, :]

    model = Sequential()
    model.add(LSTM(300, return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2])))
    model.add(Dropout(0.4))
    model.add(LSTM(50, return_sequences=True))
    model.add(Dropout(0.5))
    model.add(TimeDistributed(Dense(5, activation='softmax')))

    model.compile(optimizer=Adam(learning_rate=1e-4), loss='categorical_crossentropy', metrics=['accuracy'])
    early_stop = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True)

    history = model.fit(X_train, y_train, epochs=120, batch_size=16, validation_data=(X_val, y_val), callbacks=[early_stop])
    model.save('model_lstm_diversified_v3.h5')

    """
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.plot(history.history['loss'], label='Entrenamiento')
    plt.plot(history.history['val_loss'], label='Validación')
    plt.title('Pérdida durante el Entrenamiento y Validación')
    plt.xlabel('Épocas')
    plt.ylabel('Pérdida')
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(history.history['accuracy'], label='Entrenamiento')
    plt.plot(history.history['val_accuracy'], label='Validación')
    plt.title('Precisión durante el Entrenamiento y Validación')
    plt.xlabel('Épocas')
    plt.ylabel('Precisión')
    plt.legend()

    plt.show()
    """
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.plot(history.history['loss'], label='Entrenamiento')
    plt.plot(history.history['val_loss'], label='Validación')
    plt.title('Pérdida durante el Entrenamiento y Validación')
    plt.xlabel('Épocas')
    plt.ylabel('Pérdida')
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(history.history['accuracy'], label='Entrenamiento')
    plt.plot(history.history['val_accuracy'], label='Validación')
    plt.title('Precisión durante el Entrenamiento y Validación')
    plt.xlabel('Épocas')
    plt.ylabel('Precisión')
    plt.legend()

    # Guardar en archivo en lugar de mostrar
    plt.savefig('training_plot.png')
    plt.close()

    print("Entrenamiento completado y modelo guardado.")