from flask import Blueprint, send_from_directory, render_template
import os
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import numpy as np

detalle_bp = Blueprint('detalle', __name__)

@detalle_bp.route('/grafica')
def grafica():
    print("Ruta /grafica accedida")
    plt.switch_backend('Agg')
    meses_espanol = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    
    # Leer datos de ventas
    df = pd.read_csv('lista.csv')
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df['Año'] = df['Fecha'].dt.year
    df['Mes'] = df['Fecha'].dt.month
    ventas_por_mes_anio = df.groupby(['Año', 'Mes']).agg({'Cantidad': 'sum'}).reset_index()
    ventas_pivot = ventas_por_mes_anio.pivot(index='Año', columns='Mes', values='Cantidad')
    ventas_pivot = ventas_pivot.fillna(0).astype(int)

    # Crear gráfico de ventas
    plt.figure(figsize=(10, 5))
    for year in ventas_pivot.index:
        plt.plot(ventas_pivot.columns, ventas_pivot.loc[year], marker='o', linestyle='-', label=f'Año {year}')
    
    prediction_files = [f for f in os.listdir('PRONOSTICO_MES') if f.startswith('predicciones_') and f.endswith('.csv')]

    pred_data = {}

    for file in prediction_files:
        file_parts = file.replace('predicciones_', '').replace('.csv', '').split('_')
        month_name = file_parts[0]
        year = int(file_parts[1])
        month = next((key for key, value in meses_espanol.items() if value == month_name), None)
        if month is None:
            continue
        
        pred_df = pd.read_csv(os.path.join('PRONOSTICO_MES', file))
        pred_values = pred_df['Cantidad'].values
        pred_total = sum(pred_values)

        if year not in pred_data:
            pred_data[year] = {'months': [], 'totals': []}

        pred_data[year]['months'].append(month)
        pred_data[year]['totals'].append(pred_total)

    # Ordenar los meses de predicción
    for year in pred_data.keys():
        sorted_indices = np.argsort(pred_data[year]['months'])
        pred_data[year]['months'] = np.array(pred_data[year]['months'])[sorted_indices]
        pred_data[year]['totals'] = np.array(pred_data[year]['totals'])[sorted_indices]

    # Dibujar líneas de predicción separadas por año
    for year, data in pred_data.items():
        # Crear un array con 12 meses
        pred_totals_full = np.full(12, np.nan)
        pred_totals_full[data['months'] - 1] = data['totals']
        
        plt.plot(range(1, 13), pred_totals_full, marker='s', color='black', markersize=8, linestyle='-', label=f'Pronosticos {year}')
        
        # Añadir texto para los puntos de predicción con un ajuste vertical
        for month, total in zip(data['months'], data['totals']):
            plt.text(month, total + 10, str(int(total)), fontsize=12, ha='right')

    # Configurar el eje X para mostrar todos los meses
    plt.xticks(ticks=list(meses_espanol.keys()), labels=list(meses_espanol.values()), rotation=45)

    # Configurar el eje Y para que inicie en 100 y se incremente de 25 en 25
    plt.ylim(bottom=100)  # Establecer límite inferior del eje Y
    max_y = max(max(ventas_pivot.max()), max(max(data['totals']) for data in pred_data.values()))  # Determinar el valor máximo en los datos
    plt.yticks(range(100, int(max_y) + 25, 25))  # Ajustar las marcas del eje Y

    # Mover la leyenda debajo de la gráfica
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.35), ncol=3)

    plt.title('Ventas Históricas y Pronósticos')
    plt.xlabel('Mes')
    plt.ylabel('Cantidad de Productos Vendidos')

    # Ajustar el espacio para la leyenda y reducir el espacio en blanco arriba
    plt.subplots_adjust(left=0.1, right=0.9, top=0.85, bottom=0.3)

    now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    image_path = os.path.join('static', f'grafica_ventas_{now}.png')
    plt.savefig(image_path)
    plt.close()

    return send_from_directory(directory='static', path=f'grafica_ventas_{now}.png', as_attachment=False)
