# Importaciones estándar
import os
import glob
import pickle
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO

# Bibliotecas de terceros
import mysql.connector
import numpy as np
import pandas as pd
from flask import (Flask, flash, json, jsonify, redirect, render_template, request,
                   send_file, session, url_for)
from jinja2 import TemplateNotFound
from keras.models import load_model
from keras.metrics import mean_squared_error
from tensorflow.keras.losses import MeanSquaredError
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas

# Importaciones específicas del proyecto
from detalle import detalle_bp
from pronostico import realizar_predicciones

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from db import get_db_connection
from pre_entrenamiento import preprocesar_datos, entrenar_modelo
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from pre_entrenamiento import preprocesar_datos, entrenar_modelo

app = Flask(__name__, template_folder='views')
app.secret_key = 'supersecretkey'

db_config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'bd_ventas',
    'charset': 'utf8'
}

def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn

# Función para obtener datos de la base de datos
def get_data_from_db(query, params=None):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

# Función para ejecutar comandos de modificación en la base de datos
def execute_db_command(query, params=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params or ())
    conn.commit()
    cursor.close()
    conn.close()

def execute_db_command2(query, params=None, return_lastrowid=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
        if return_lastrowid:
            return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


# Funcion para el listado de productos en venta
@app.route('/registro')
def registro_venta():
    query1 = "SELECT * FROM tipos ORDER BY nombre"
    tipos = get_data_from_db(query1)
    #print(tipos)

    query2 = "SELECT * FROM colores ORDER BY nombre"
    colores = get_data_from_db(query2)

    query3 = "SELECT * FROM materiales ORDER BY nombre"
    materiales = get_data_from_db(query3)

    query4 = "SELECT * FROM agregados ORDER BY nombre"
    agregados_data = get_data_from_db(query4)

    agregados_por_tipo = {}
    for agregado in agregados_data:
        tipo_id = agregado['tipo']
        agregado_id = agregado['id']
        nombre = agregado['nombre']
        if tipo_id not in agregados_por_tipo:
            agregados_por_tipo[tipo_id] = []
        agregados_por_tipo[tipo_id].append({'id': agregado_id, 'nombre': nombre})

    query5 = "SELECT * FROM ventas"
    ventas = get_data_from_db(query5)

    return render_template('registro.html', tipos=tipos, colores=colores, materiales=materiales, agregados_por_tipo=agregados_por_tipo, ventas=ventas)

@app.route('/get_price', methods=['POST'])
def get_price():
    data = request.json
    tipo_id = data.get('tipo_id')
    color_id = data.get('color_id')
    material_id = data.get('material_id')
    agregado_id = data.get('agregado_id')

    # Modify the query to handle NULL for agregado_id
    if agregado_id is None:
        query = "SELECT id, activo, precioU, stock FROM producto_combinaciones WHERE tipo_id = %s AND color_id = %s AND material_id = %s AND agregado_id IS NULL"
        params = (tipo_id, color_id, material_id)
    else:
        query = "SELECT id, activo, precioU, stock FROM producto_combinaciones WHERE tipo_id = %s AND color_id = %s AND material_id = %s AND agregado_id = %s"
        params = (tipo_id, color_id, material_id, agregado_id)
    
    result = get_data_from_db(query, params)

    if result:
        return jsonify(result[0])
    else:
        return jsonify(None), 404

@app.route('/editar_inventario', methods=['POST'])
def editar_inventario():
    producto_id = request.form['producto_id']
    stock = request.form['stock_1']
    precioU = request.form['precio_1']

    # Actualizar la base de datos
    query = """
        UPDATE producto_combinaciones
        SET stock = %s, precioU = %s
        WHERE id = %s
    """
    params = (stock, precioU, producto_id)
    execute_db_command(query, params)

    return jsonify({'success': True})





# Función para conectar a la base de datos
def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn

# Función para obtener el siguiente nombre de archivo disponible
def get_next_filename():
    i = 1
    while os.path.exists(f'csv_files/v{i}.csv'):
        i += 1
    return f'csv_files/v{i}.csv'

# Rutas de la aplicación

@app.route('/')
def index():
    # Serializar el diccionario agregados_por_tipo a JSON
    # agregados_json = json.dumps(agregados_por_tipo)
    # Pasar la cadena JSON a la plantilla
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'id' in session:
        return redirect(url_for('dashboard'))
    
    error_message = None
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM usuario WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            query1 = "SELECT * FROM persona WHERE id = %s"
            persona = get_data_from_db(query1, (user['id_persona'],))
            if persona:
                persona = persona[0]  # Accede al primer elemento de la lista

                session['id'] = user['id']
                session['username'] = user['username']
                session['rol'] = user['rol']
                session['id_persona'] = user['id_persona']
                session['nombre'] = persona['nombre']
                session['apellido'] = persona['apellido']
                flash('Inicio de sesión exitoso.', 'success')
                if user['rol'] == 'administrador':
                    return redirect(url_for('dashboard'))
                elif user['rol'] == 'encargado' or user['rol'] == 'empleado':
                    return redirect(url_for('registro'))
            else:
                error_message = 'Datos personales no encontrados.'
        else:
            error_message = 'Nombre de usuario o contraseña incorrectos.'

    return render_template('login.html', error_message=error_message)


@app.route('/logout')
def logout():
    session.pop('id', None)
    session.pop('username', None)
    session.pop('rol', None)
    session.pop('id_persona', None)
    flash('Cierre de sesión exitoso.', 'success')
    return render_template('login.html')

# @app.route('/<page_name>')
# def render_page(page_name):
#     try:
#         return render_template(f'{page_name}')
#     except TemplateNotFound:
#         return redirect(url_for('page_not_found'))


@app.route('/guardar_producto', methods=['POST'])
def guardar_producto():
    data = request.json
    nombre_producto = data.get('producto_3')
    stock = data.get('stock_3')
    precioU = data.get('precioU_3')
    
    if nombre_producto and stock is not None and precioU is not None:
        try:
            # Insertar el nuevo producto en la tabla 'tipos'
            query_tipo = "INSERT INTO tipos (nombre) VALUES (%s)"
            params_tipo = (nombre_producto,)
            tipo_id = execute_db_command2(query_tipo, params_tipo, return_lastrowid=True)
            
            # Convertir stock y precioU a los tipos de datos correctos
            stock = int(stock)
            precioU = float(precioU)
            
            # Llamar al procedimiento almacenado con el tipo_id
            query_proc = "CALL generate_combinations_primero(%s, NULL, %s, %s)"
            params_proc = (tipo_id, stock, precioU)
            execute_db_command2(query_proc, params_proc)
            
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    else:
        return jsonify({'success': False, 'error': 'Faltan datos del producto.'})

@app.route('/guardar_agregado_primero', methods=['POST'])
def guardar_agregado_primero():
    data = request.json
    tipo = data.get('tipo_3')
    descripcion = data.get('nombre_3')
    stock = data.get('stock_3')
    precioU = data.get('precioU_3')

    if tipo and descripcion and stock is not None and precioU is not None:
        try:
            # Insertar el nuevo agregado
            query_agregado = "INSERT INTO agregados (tipo, nombre) VALUES (%s, %s)"
            params_agregado = (tipo, descripcion)
            agregado_id = execute_db_command2(query_agregado, params_agregado, return_lastrowid=True)

            # Convertir stock y precioU a los tipos de datos correctos
            stock = int(stock)
            precioU = float(precioU)

            # Llamar al procedimiento almacenado con el agregado_id
            query_proc = "CALL generate_combinations_primero(NULL, %s, %s, %s)"
            params_proc = (agregado_id, stock, precioU)
            execute_db_command2(query_proc, params_proc)

            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    else:
        return jsonify({'success': False, 'error': 'Faltan datos del agregado.'})


@app.route('/guardar_agregado', methods=['POST'])
def guardar_agregado():
    data = request.json
    tipo = data.get('tipo_4')
    descripcion = data.get('nombre_4')

    if tipo and descripcion:
        try:
            # Insertar el agregado en la base de datos
            query = "INSERT INTO agregados (tipo, nombre) VALUES (%s, %s)"
            params = (tipo, descripcion)
            execute_db_command(query, params)

            # Llamar al procedimiento almacenado con el agregado_id
            query_proc = "CALL generate_combinations()"
            execute_db_command(query_proc)

            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'No se proporcionaron los datos de tipo o descripción.'})

@app.route('/guardar_color', methods=['POST'])
def guardar_color():
    data = request.json
    color = data.get('color_3')
    
    if color:
        query = "INSERT INTO colores (nombre) VALUES (%s)"
        params = (color,)

        # Intentar ejecutar la inserción en la base de datos
        try:
            execute_db_command(query, params)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    # Si no se proporcionó nombre, retornar error
    return jsonify({'success': False, 'error': 'No se proporcionó el nombre del producto.'})

@app.route('/guardar_material', methods=['POST'])
def guardar_material():
    data = request.json
    material = data.get('material_3')
    
    if material:
        query = "INSERT INTO materiales (nombre) VALUES (%s)"
        params = (material,)

        # Intentar ejecutar la inserción en la base de datos
        try:
            execute_db_command(query, params)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    # Si no se proporcionó nombre, retornar error
    return jsonify({'success': False, 'error': 'No se proporcionó el nombre del producto.'})


@app.route('/registro', methods=['POST'])
def registro():
    ventas = []
    i = 2
    tipo = request.form.get(f'tipo_{i}')
    color = request.form.get(f'color_{i}')
    material = request.form.get(f'material_{i}')
    agregado_id = request.form.get(f'agregado_{i}')
    cantidad = request.form.get(f'cantidad_{i}')
    precioU = request.form.get(f'precio_{i}')
    fecha = request.form.get(f'fecha_{i}')

    tipo = tipo.split("'")[5]
    color = color.split("'")[5]
    material = material.split("'")[5]

    if not (tipo and color and material and cantidad and precioU and fecha):
        return jsonify({'status': 'error', 'message': 'Todos los campos son obligatorios.'}), 400

    # Obtener el nombre del agregado a partir de su id
    agregado_nombre = get_agregado_nombre(agregado_id)
          
    cantidad = int(cantidad)
    precioU = float(precioU)
    precioT = cantidad * precioU

    ventas.append((tipo, color, material, agregado_nombre, cantidad, precioU, precioT, fecha))

    try:
        # Guardar en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO ventas (tipo, color, material, agregado, cantidad, precioU, precioT, fecha)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, ventas)
        conn.commit()
    except mysql.connector.Error as err:
        if err.errno == 1644:  # Error personalizado para stock insuficiente
            return jsonify({'status': 'error', 'message': 'Stock insuficiente para la venta.'}), 400
        else:
            return jsonify({'status': 'error', 'message': 'Ocurrió un error al registrar las ventas. Por favor, intente nuevamente.'}), 500
    finally:
        cursor.close()
        conn.close()

    # Generar IDs para el archivo CSV
    ids = list(range(1, len(ventas) + 1))
    ventas_con_id = [(ids[i], *ventas[i]) for i in range(len(ventas))]

    # Guardar en un archivo CSV
    ventas_df = pd.DataFrame(ventas_con_id, columns=['ID', 'Tipo', 'Color', 'Material', 'Agregado', 'Cantidad', 'Precio Unitario', 'Precio Total', 'Fecha'])
    filename = get_next_filename()
    ventas_df.to_csv(filename, index=False)

    return jsonify({'status': 'success', 'message': 'Se han registrado la venta.'})

def get_agregado_nombre(agregado_id):
    query = "SELECT nombre FROM agregados WHERE id = %s"
    result = get_data_from_db(query, (agregado_id,))
    return result[0]['nombre'] if result else None


@app.route('/datos')
def datos():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM ventas')
    ventas = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('registro.html', ventas=ventas)


@app.route('/editar_venta/<int:venta_id>', methods=['GET', 'POST'])
def editar_venta(venta_id):
    if request.method == 'POST':
        tipo_json = request.form.get('tipo_1')
        color_json = request.form.get('color_1')
        material_json = request.form.get('material_1')
        agregado_id = request.form['agregado_1']
        cantidad = int(request.form['cantidad_1'])
        precioU = float(request.form['precioU_1'])
        precioT = cantidad * precioU
        fecha = request.form['fecha_1']

        tipo = json.loads(tipo_json)
        color = json.loads(color_json)
        material = json.loads(material_json)

        tipo_nombre = tipo['nombre']
        color_nombre = color['nombre']
        material_nombre = material['nombre']

        query = """
            UPDATE ventas 
            SET tipo = %s, color = %s, material = %s, agregado = %s, cantidad = %s, precioU = %s, precioT = %s, fecha = %s
            WHERE id = %s
        """
        params = (tipo_nombre, color_nombre, material_nombre, agregado_id, cantidad, precioU, precioT, fecha, venta_id)
        execute_db_command(query, params)

        flash('Venta actualizada correctamente.', 'success')
        return redirect(url_for('registro'))
    return redirect(url_for('registro'))


@app.route('/eliminar_venta/<int:venta_id>', methods=['POST'])
def eliminar_venta(venta_id):
    query = 'DELETE FROM ventas WHERE id = %s'
    execute_db_command(query, (venta_id,))
    flash('Venta eliminada correctamente.', 'success')
    return redirect(url_for('registro'))


@app.route('/profile')
def profile():
    if 'id' not in session:
        return redirect(url_for('login'))  # Redirigir al login si no hay una sesión activa

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM usuario WHERE id = %s', (session['id'],))
    user = cursor.fetchone()

    if user:
        cursor.execute('SELECT * FROM persona WHERE id = %s', (session['id_persona'],))
        persona = cursor.fetchone()
        
        cursor.close()
        conn.close()

        if persona:
            return render_template('profile.html', user=user, persona=persona)
    else:
        cursor.close()
        conn.close()
        flash('Usuario no encontrado.', 'danger')
        return render_template('login.html')

    return render_template('login.html')


@app.route('/update_datos', methods=['POST'])
def update_datos():
    if 'id' not in session:
        flash('Debe iniciar sesión primero.', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['id']
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    ci = request.form['ci']
    genero = request.form['genero']
    email = request.form['email']
    telefono = request.form['telefono']
    direccion = request.form['direccion']
    fecha_nac = request.form['fecha_nac']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Actualizar la tabla persona
    cursor.execute("""
        UPDATE persona
        SET nombre = %s, apellido = %s, ci = %s, genero = %s, email = %s, telefono = %s, direccion = %s, fecha_nac = %s
        WHERE id = %s
    """, (nombre, apellido, ci, genero, email, telefono, direccion, fecha_nac, session['id_persona']))

    conn.commit()
    cursor.close()
    conn.close()

    # Actualizar los datos de la sesión
    session['nombre'] = nombre
    session['apellido'] = apellido

    flash('Perfil actualizado con éxito.', 'success')
    return redirect(url_for('profile'))

@app.route('/update_user', methods=['POST'])
def update_user():
    if 'id' not in session:
        flash('Debe iniciar sesión primero.', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['id']
    username = request.form['username']
    password = request.form['password']
    rol = request.form['rol']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Actualizar la tabla usuario
    cursor.execute("""
        UPDATE usuario
        SET username = %s, password = %s, rol = %s
        WHERE id = %s
    """, (username, password, rol, user_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Perfil actualizado con éxito.', 'success')
    return redirect(url_for('profile'))


@app.route('/register')
def register():
    query1 = "SELECT * FROM usuario u, persona p WHERE u.id_persona = p.id AND u.rol != 'administrador'"
    usuarios = get_data_from_db(query1)

    return render_template('register.html', usuarios=usuarios)

@app.route('/create_user', methods=['POST'])
def create_user():
    if 'id' not in session:
        flash('Debe iniciar sesión primero.', 'danger')
        return redirect(url_for('login'))
    
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    ci = request.form['ci']
    genero = request.form['genero']
    email = request.form['email']
    telefono = request.form['telefono']
    direccion = request.form['direccion']
    fecha_nac = request.form['fecha_nac']
    rol = request.form['rol']

    # Generar username y password
    nombre_split = nombre.strip().split()
    apellido_split = apellido.strip().split()
    
    if len(nombre_split) > 0 and len(apellido_split) > 0:
        username = nombre_split[0][0].lower() + apellido_split[0].lower()
        if len(apellido_split) > 1:
            username += apellido_split[1][0].lower()
        password = username  # Esto es solo un ejemplo; usualmente, las contraseñas deben ser más seguras
    else:
        flash('Nombre o apellido no proporcionados correctamente.', 'danger')
        return redirect(url_for('register'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Insertar en la tabla persona
    cursor.execute("""
        INSERT INTO persona (nombre, apellido, ci, genero, email, telefono, direccion, fecha_nac)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (nombre, apellido, ci, genero, email, telefono, direccion, fecha_nac))
    
    # Obtener el id de la persona recién creada
    persona_id = cursor.lastrowid

    # Insertar en la tabla usuario
    cursor.execute("""
        INSERT INTO usuario (username, password, rol, id_persona)
        VALUES (%s, %s, %s, %s)
    """, (username, password, rol, persona_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Usuario creado con éxito.', 'success')
    return redirect(url_for('register'))


@app.route('/editar_datos_personales/<int:user_id>', methods=['POST'])
def editar_datos_personales(user_id):
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    ci = request.form['ci']
    genero = request.form['genero']
    email = request.form['email']
    telefono = request.form['telefono']
    direccion = request.form['direccion']
    fecha_nac = request.form['fecha_nac']

    query = '''
        UPDATE persona
        SET nombre = %s, apellido = %s, ci = %s, genero = %s, email = %s, telefono = %s, direccion = %s, fecha_nac = %s
        WHERE id = %s
    '''
    params = (nombre, apellido, ci, genero, email, telefono, direccion, fecha_nac, user_id)
    execute_db_command(query, params)
    flash('Datos personales actualizados correctamente.', 'success')
    return redirect(url_for('register'))

@app.route('/editar_ajustes_usuario/<int:user_id>', methods=['POST'])
def editar_ajustes_usuario(user_id):
    username = request.form['username']
    password = request.form['password']
    rol = request.form['rol']

    query = '''
        UPDATE usuario
        SET username = %s, password = %s, rol = %s
        WHERE id_persona = %s
    '''
    params = (username, password, rol, user_id)
    execute_db_command(query, params)
    flash('Ajustes de usuario actualizados correctamente.', 'success')
    return redirect(url_for('register'))

@app.route('/eliminar_user/<int:user_id>', methods=['POST'])
def eliminar_user(user_id):
    query_get_persona_id = 'SELECT id_persona FROM usuario WHERE id = %s'
    result = get_data_from_db(query_get_persona_id, (user_id,))
    if result:
        persona_id = result[0]['id_persona']
        
        # Elimina el usuario
        query_delete_user = 'DELETE FROM usuario WHERE id = %s'
        execute_db_command(query_delete_user, (user_id,))
        
        # Elimina la persona asociada
        query_delete_persona = 'DELETE FROM persona WHERE id = %s'
        execute_db_command(query_delete_persona, (persona_id,))
        
        flash('Usuario y persona asociados eliminados correctamente.', 'success')
    else:
        print("no")
        flash('No se encontró el usuario.', 'danger')
    
    return redirect(url_for('registro'))


@app.route('/inventario')
def inventario():
    query1 = "SELECT * FROM tipos ORDER BY nombre"
    tipos = get_data_from_db(query1)

    query2 = "SELECT * FROM colores ORDER BY nombre"
    colores = get_data_from_db(query2)

    query3 = "SELECT * FROM materiales ORDER BY nombre"
    materiales = get_data_from_db(query3)

    query4 = "SELECT * FROM agregados ORDER BY nombre"
    agregados_data = get_data_from_db(query4)

    agregados_por_tipo = {}
    for agregado in agregados_data:
        tipo_id = agregado['tipo']
        agregado_id = agregado['id']
        nombre = agregado['nombre']
        if tipo_id not in agregados_por_tipo:
            agregados_por_tipo[tipo_id] = []
        agregados_por_tipo[tipo_id].append({'id': agregado_id, 'nombre': nombre})

    query5 = "SELECT * FROM ventas"
    ventas = get_data_from_db(query5)

    query6 = "SELECT pc.activo, pc.id, pc.tipo_id, t.nombre as 'n_tipo', pc.color_id, c.nombre as 'n_color', pc.material_id, m.nombre as 'n_material', pc.agregado_id, a.nombre as 'n_agregado', pc.stock, pc.precioU FROM producto_combinaciones pc, tipos t, colores c, materiales m, agregados a WHERE pc.tipo_id = t.id AND pc.color_id = c.id AND pc.material_id = m.id AND pc.agregado_id = a.id"
    inventarios = get_data_from_db(query6)
    return render_template('table.html', inventarios=inventarios, tipos=tipos, colores=colores, materiales=materiales, agregados_por_tipo=agregados_por_tipo, ventas=ventas)


@app.route('/toggle_inventario/<int:producto_id>', methods=['POST'])
def toggle_inventario(producto_id):
    data = request.json
    nuevo_estado = data['activo']
    query = "UPDATE producto_combinaciones SET activo = %s WHERE id = %s"
    params = (nuevo_estado, producto_id)
    execute_db_command(query, params)
    return jsonify({'success': True})


@app.route('/update_product', methods=['POST'])
def update_product():
    try:
        stock = request.form.get('stock_0', type=int)
        precio_unitario = request.form.get('precio_0', type=float)
        product_id = request.form.get('id_0', type=int)

        query = "UPDATE producto_combinaciones SET stock = %s, precioU = %s WHERE id = %s"
        params = (stock, precio_unitario, product_id)
        execute_db_command(query, params)

        return jsonify({'message': 'Producto actualizado correctamente.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/check_product_status', methods=['POST'])
def check_product_status():
    data = request.get_json()
    tipo_id = data['tipo_id']
    color_id = data['color_id']
    material_id = data['material_id']
    agregado_id = data.get('agregado_id')  # Use .get to safely access agregado_id

    # Modify the query depending on whether agregado_id is provided or null
    if agregado_id is None:
        query = """
            SELECT activo FROM producto_combinaciones
            WHERE tipo_id = %s AND color_id = %s AND material_id = %s AND agregado_id IS NULL
        """
        params = (tipo_id, color_id, material_id)
    else:
        query = """
            SELECT activo FROM producto_combinaciones
            WHERE tipo_id = %s AND color_id = %s AND material_id = %s AND agregado_id = %s
        """
        params = (tipo_id, color_id, material_id, agregado_id)

    result = get_data_from_db(query, params)

    # Return JSON response based on whether the product is active
    if result and result[0]['activo']:
        return jsonify(is_active=True)
    else:
        return jsonify(is_active=False)

@app.route('/dashboard')
def dashboard():
    # Consulta para obtener el número de usuarios registrados
    query_usuarios = "SELECT COUNT(*) AS total_usuarios FROM usuario"
    total_usuarios = get_data_from_db(query_usuarios)[0]['total_usuarios']

    # Consulta para obtener el número de ventas hechas
    query_ventas = "SELECT COUNT(*) AS total_ventas FROM ventas"
    total_ventas = get_data_from_db(query_ventas)[0]['total_ventas']

    # Consulta para obtener el número de productos en el inventario
    query_productos = "SELECT COUNT(*) AS total_productos FROM producto_combinaciones WHERE stock > 0"
    total_productos = get_data_from_db(query_productos)[0]['total_productos']

    # Consulta para obtener las ventas hechas en los últimos 5 días
    query_ventas_ultimos_5_dias = """
        SELECT fecha, COUNT(*) AS ventas_por_dia 
        FROM ventas 
        WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 5 DAY)
        GROUP BY fecha
    """
    ventas_ultimos_5_dias = get_data_from_db(query_ventas_ultimos_5_dias)

    # Consulta para obtener la cantidad de encargados y empleados
    query_usuarios_roles = "SELECT rol, COUNT(*) AS total FROM usuario WHERE rol != 'administrador' GROUP BY rol"
    usuarios_roles = get_data_from_db(query_usuarios_roles)
    
    roles_data = {role['rol']: role['total'] for role in usuarios_roles}

    return render_template('inicio.html', 
                           total_usuarios=total_usuarios, 
                           total_ventas=total_ventas, 
                           total_productos=total_productos,
                           ventas_ultimos_5_dias=ventas_ultimos_5_dias,
                           roles_data=roles_data)





@app.route('/prediccion', methods=['GET'])
def prediccion():
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')

    # Extraer ventas del día actual desde la base de datos
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM ventas WHERE fecha = %s', (fecha_hoy,))
    ventas_hoy = cursor.fetchall()
    cursor.close()
    conn.close()

    if not ventas_hoy:
        flash('No se registraron ventas del día de hoy.', 'warning')
        return redirect(url_for('registro_venta'))

    # Convertir las ventas del día actual en un DataFrame con las columnas adecuadas
    ventas_hoy_df = pd.DataFrame(ventas_hoy)
    ventas_hoy_df.columns = ['ID', 'Tipo', 'Color', 'Material', 'Agregado', 'Cantidad', 'Precio Unitario', 'Precio Total', 'Fecha']

    # Guardar ventas del día actual en un archivo CSV
    filename = get_next_filename()
    ventas_hoy_df.to_csv(filename, index=False)

    # Leer el archivo 'lista.csv'
    ventas_lista = pd.read_csv('lista.csv')

    # Combinar las ventas del día actual con el archivo 'lista.csv'
    ventas_combined = pd.concat([ventas_hoy_df, ventas_lista], ignore_index=True)

    # Realizar la predicción para el día siguiente
    predicciones = predecir_dia_siguiente(ventas_combined)

    # Renderizar el template con las predicciones
    return render_template('predicciones.html', predicciones=predicciones.to_dict(orient='records'))

def predecir_dia_siguiente(ventas_dia):
    # Cargar el modelo entrenado, especificando la métrica mse
    model = load_model('modelo.h5', custom_objects={'mse': mean_squared_error})

    # Cargar los codificadores y el scaler
    with open('encoders.pkl', 'rb') as f:
        encoders = pickle.load(f)
    with open('scaler.pkl', 'rb') as f:
        scaler = pickle.load(f)

    ventas_dia = ventas_dia.copy()  # Hacemos una copia para evitar modificaciones sobre la vista
    ventas_dia['Fecha'] = pd.to_datetime(ventas_dia['Fecha'])
    fecha_siguiente = ventas_dia['Fecha'].max() + pd.Timedelta(days=1)
    ventas_dia['Fecha'] = fecha_siguiente
    for feature in encoders.keys():
        ventas_dia[feature] = encoders[feature].transform(ventas_dia[feature])
    ventas_dia['Cantidad'] = scaler.transform(ventas_dia[['Cantidad']])
    X = ventas_dia.drop(columns=['Cantidad', 'Precio Unitario', 'Precio Total', 'Fecha'])
    X = np.expand_dims(X.values, axis=1)
    predicciones = model.predict(X)
    ventas_dia['Cantidad'] = scaler.inverse_transform(predicciones).round().astype(int)  # Redondear y convertir a entero
    for feature in encoders.keys():
        ventas_dia[feature] = encoders[feature].inverse_transform(ventas_dia[feature])
    
    # Generar un número aleatorio de predicciones entre 3 y 10
    num_predictions = np.random.randint(3, 7)
    
    predicciones_df = ventas_dia[['Tipo', 'Color', 'Material', 'Agregado', 'Cantidad']].head(num_predictions)
    predicciones_df.reset_index(inplace=True, drop=True)
    predicciones_df.index += 1
    predicciones_df.reset_index(inplace=True)
    predicciones_df.rename(columns={'index': 'ID'}, inplace=True)
    
    return predicciones_df

@app.route('/guardar_predicciones', methods=['POST'])
def guardar_predicciones():
    predicciones = request.json['predicciones']
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    hora_hoy = datetime.now().strftime('%H-%M-%S')  
    fecha_manana = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    filename = f'predicciones_{fecha_hoy}_{hora_hoy}.pdf'
    filepath = os.path.join('pdf_files', filename)

    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont('Helvetica-Bold', 10)

    c.drawString(30, 750, f"Predicciones para el día siguiente: {fecha_manana}")
    c.drawString(30, 735, f"Generado el: {fecha_hoy} a las {hora_hoy}")

    # Encabezados de la tabla
    c.drawString(30, 700, "ID")
    c.drawString(70, 700, "Tipo")
    c.drawString(280, 700, "Color")
    c.drawString(320, 700, "Material")
    c.drawString(390, 700, "Agregado")
    c.drawString(490, 700, "Cant.")

    # Contenido de la tabla
    y = 680
    for prediccion in predicciones:
        c.drawString(30, y, str(prediccion['ID']))
        c.drawString(70, y, prediccion['Tipo'])
        c.drawString(280, y, prediccion['Color'])
        c.drawString(320, y, prediccion['Material'])
        c.drawString(390, y, prediccion['Agregado'])
        c.drawString(490, y, str(prediccion['Cantidad']))
        y -= 20
        if y < 40:  # Para evitar que el texto se salga de la página
            c.showPage()
            c.setFont('Courier', 11)
            y = 750
            c.drawString(30, 700, "ID")
            c.drawString(70, 700, "Tipo")
            c.drawString(280, 700, "Color")
            c.drawString(320, 700, "Material")
            c.drawString(390, 700, "Agregado")
            c.drawString(490, 700, "Cant.")

    c.save()

    return send_file(filepath, as_attachment=True)

@app.route('/guardar_predicciones_futuro', methods=['POST'])
def guardar_predicciones_futuro():
    predicciones = request.json['predicciones']
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    hora_hoy = datetime.now().strftime('%H-%M-%S')
    fecha_futura = predicciones[0]['Fecha']

    filename = f'predicciones_futuro_{fecha_hoy}_{hora_hoy}.pdf'
    filepath = os.path.join('pdf_files', filename)

    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont('Helvetica-Bold', 10)

    c.drawString(30, 750, f"Predicciones para la fecha futura: {fecha_futura}")
    c.drawString(30, 735, f"Generado el: {fecha_hoy} a las {hora_hoy}")

    # Encabezados de la tabla
    c.drawString(30, 700, "ID")
    c.drawString(70, 700, "Tipo")
    c.drawString(280, 700, "Color")
    c.drawString(320, 700, "Material")
    c.drawString(390, 700, "Agregado")
    c.drawString(490, 700, "Cant.")

    # Contenido de la tabla
    y = 680
    for prediccion in predicciones:
        c.drawString(30, y, str(prediccion['ID']))
        c.drawString(70, y, prediccion['Tipo'])
        c.drawString(280, y, prediccion['Color'])
        c.drawString(320, y, prediccion['Material'])
        c.drawString(390, y, prediccion['Agregado'])
        c.drawString(490, y, str(prediccion['Cantidad']))
        y -= 20
        if y < 40:  # Para evitar que el texto se salga de la página
            c.showPage()
            c.setFont('Helvetica-Bold', 10)
            y = 750
            c.drawString(30, y, "ID")
            c.drawString(70, y, "Tipo")
            c.drawString(280, y, "Color")
            c.drawString(320, y, "Material")
            c.drawString(390, y, "Agregado")
            c.drawString(490, y, "Cant.")

    c.save()

    return send_file(filepath, as_attachment=True)

@app.route('/prediccion_futuro', methods=['GET'])
def prediccion_futuro():
    fecha_futura = request.args.get('fecha')
    if not fecha_futura:
        flash('Fecha futura no proporcionada.', 'danger')
        return redirect(url_for('registro_venta'))

    # Obtener las predicciones para la fecha futura
    predicciones = predecir_fecha_futura(fecha_futura)

    # Renderizar el template con las predicciones
    return render_template('datosFuturo.html', predicciones=predicciones.to_dict(orient='records'))

def predecir_fecha_futura(fecha_futura):
    # Cargar el modelo entrenado y los objetos de preprocesamiento
    model = load_model('lstm_model.h5', custom_objects={'mse': MeanSquaredError()})
    
    with open('label_encoders.pkl', 'rb') as f:
        label_encoders = pickle.load(f)
    with open('scaler1.pkl', 'rb') as f:
        scaler = pickle.load(f)

    # Cargar los datos históricos
    file_path = 'lista.csv'
    df = pd.read_csv(file_path)

    # Preprocesar los datos históricos
    categorical_columns = ['Tipo', 'Color', 'Material', 'Agregado']
    for col in categorical_columns:
        df[col] = label_encoders[col].transform(df[col])

    df['Cantidad'] = scaler.transform(df[['Cantidad']])
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df = df.sort_values(by='Fecha')

    future_date = datetime.strptime(fecha_futura, "%Y-%m-%d")

    # Crear predicciones aleatorias
    predicted_products = []

    # Generar un número aleatorio de predicciones entre 2 y 9
    num_predictions = np.random.randint(2, 8)

    # Agarrar la fecha del sistema (30 de agosto del 2024)
    # Buscar la misma fecha en el historico y con la IA predecir

    for _ in range(num_predictions):  # Generar predicciones aleatorias
        predicted_values = [
            np.random.choice(df['Tipo'].unique()),
            np.random.choice(df['Color'].unique()),
            np.random.choice(df['Material'].unique()),
            np.random.choice(df['Agregado'].unique()),
            np.random.random()  # Valor aleatorio para la cantidad
        ]
        predicted_products.append(predicted_values)

    # Transformar las predicciones inversamente a sus etiquetas originales
    predicted_df = pd.DataFrame(predicted_products, columns=['Tipo', 'Color', 'Material', 'Agregado', 'Cantidad'])
    for col in categorical_columns:
        predicted_df[col] = label_encoders[col].inverse_transform(predicted_df[col].astype(int))

    # Asignar las cantidades promedio de los datos históricos del mismo tipo de producto
    def get_avg_quantity(row):
        filtered_df = df[df['Tipo'] == row['Tipo']]
        if not filtered_df.empty:
            avg_quantity = filtered_df['Cantidad'].mean()
            return abs(avg_quantity)  # Asegurar que la cantidad sea positiva
        else:
            return abs(row['Cantidad'])

    predicted_df['Cantidad'] = predicted_df.apply(get_avg_quantity, axis=1)
    predicted_df['Cantidad'] = scaler.inverse_transform(predicted_df[['Cantidad']])
    predicted_df['Cantidad'] = predicted_df['Cantidad'].abs().round().astype(int)

    predicted_df['Fecha'] = future_date

    # Añadir columna de ID
    predicted_df['ID'] = range(1, len(predicted_df) + 1)

    # Mostrar los resultados de la predicción
    return predicted_df[['ID', 'Tipo', 'Color', 'Material', 'Agregado', 'Cantidad', 'Fecha']]

"""
@app.route('/mes')
def mes():
    return render_template('mes.html')

@app.route('/ejecutar_prediccion', methods=['POST'])
def ejecutar_prediccion():
    data = request.json
    num_months = data.get('num_months')
    current_date_str = data.get('current_date')

    # Validar datos
    if not num_months or not current_date_str:
        return jsonify({"error": "Datos inválidos"}), 400

    try:
        num_months = int(num_months)
        current_date = datetime.strptime(current_date_str, "%Y-%m")
    except ValueError:
        return jsonify({"error": "Formato de fecha inválido"}), 400

    # Llamar a la función de pronóstico
    result = pronostico.realizar_predicciones(num_months, current_date)

    if result:
        return jsonify({"message": "Predicciones realizadas con éxito"}), 200
    else:
        return jsonify({"error": "Error al realizar las predicciones"}), 500
"""
# Función para borrar archivos en el directorio de pronósticos
"""
def borrar_archivos_pronostico():
    folder_path = 'PRONOSTICO_MES'  # Ruta a la carpeta de predicciones
    files = glob.glob(os.path.join(folder_path, '*.csv'))  # Busca archivos .csv

    for file in files:
        try:
            os.remove(file)  # Elimina cada archivo encontrado
            print(f"Archivo {file} eliminado correctamente.")
        except Exception as e:
            print(f"No se pudo eliminar el archivo {file}. Error: {e}")
"""

# Ruta /pronostico modificada
@app.route('/pronostico', methods=['GET'])
def pronostico():
    # Llamar a la función para borrar los archivos antes de generar nuevos pronósticos
    # borrar_archivos_pronostico()

    # Continuar con la lógica existente
    return render_template('mes.html')

@app.route('/ejecutar_prediccion', methods=['POST'])
def ejecutar_prediccion():
    fecha = request.form.get('fecha')
    cantidad_meses = int(request.form.get('cantidad_meses'))
    
    realizar_predicciones(cantidad_meses, fecha)

    return redirect(url_for('mes', mensaje="Pronósticos realizados exitosamente."))

@app.route('/mes', methods=['GET', 'POST'])
def mes():
    mensaje = request.args.get('mensaje')
    return render_template('mes.html', mensaje=mensaje)

app.register_blueprint(detalle_bp, url_prefix='/detalle')
@app.route('/detalle')
def detalle():
    # Ruta a la carpeta donde están los archivos de pronóstico
    folder_path = 'PRONOSTICO_MES'
    
    # Verificar que la carpeta existe
    if not os.path.exists(folder_path):
        return "La carpeta de datos no existe", 404

    # Obtener lista de archivos CSV
    files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    
    if not files:
        return "No se encontraron archivos CSV en la carpeta", 404

    # Cargar los datos de los archivos CSV
    data = {}
    for file in files:
        # Extraer el mes y año del nombre del archivo
        try:
            parts = file.split('_')
            if len(parts) >= 2:
                month = parts[1]  # Esto será 'Enero', 'Febrero', etc.
                year = parts[2].split('.')[0]  # Asumimos que el año es la tercera parte y está seguido por la extensión .csv
                df = pd.read_csv(os.path.join(folder_path, file))
                key = f"{month} {year}"  # Combinar mes y año
                data[key] = df.to_dict(orient='records')
            else:
                print(f"Nombre de archivo inesperado: {file}")
        except Exception as e:
            print(f"Error al procesar el archivo {file}: {e}")

    # Verificar que se han cargado datos
    if not data:
        return "No se cargaron datos", 500

    # Obtener el mes y año actual
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    # Mapear nombres de meses a números
    meses_a_numero = {
        'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4, 'Mayo': 5, 'Junio': 6,
        'Julio': 7, 'Agosto': 8, 'Septiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12
    }
    
    # Invertir el mapa para obtener el nombre del mes desde el número
    numero_a_meses = {v: k for k, v in meses_a_numero.items()}
    
    # Crear lista de meses a mostrar desde el siguiente mes
    meses_a_mostrar = []
    
    # Incluir meses del año actual desde el siguiente mes
    for mes_numero in range(current_month + 1, 13):
        mes_nombre = numero_a_meses[mes_numero]
        if f"{mes_nombre} {current_year}" in data:
            meses_a_mostrar.append(f"{mes_nombre} {current_year}")
    
    # Incluir meses del próximo año si existen en los datos
    for mes_numero in range(1, 13):
        mes_nombre = numero_a_meses[mes_numero]
        if f"{mes_nombre} {current_year + 1}" in data:
            meses_a_mostrar.append(f"{mes_nombre} {current_year + 1}")
    
    # Filtrar y ordenar los datos para mostrar solo los meses deseados
    datos_por_mes = {mes: data[mes] for mes in meses_a_mostrar if mes in data}
    
    # Ordenar los meses
    meses_ordenados = sorted(datos_por_mes.keys(), key=lambda mes: (int(mes.split()[1]), meses_a_numero[mes.split()[0]]))
    datos_por_mes = {mes: datos_por_mes[mes] for mes in meses_ordenados}
    
    # Depuración: imprimir los datos que se enviarán a la plantilla
    print("Datos enviados a la plantilla:", datos_por_mes)

    # Generar timestamp para la URL de la gráfica
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    # Renderizar la plantilla con los datos y el timestamp
    return render_template('detalle.html', datos_por_mes=datos_por_mes, timestamp=timestamp)

@app.route('/ver', methods=['GET'])
def ver():
    # Ruta a la carpeta donde están los archivos de pronóstico
    folder_path = 'PRONOSTICO_MES'
    
    # Verificar que la carpeta existe
    if not os.path.exists(folder_path):
        return "La carpeta de datos no existe", 404

    # Obtener lista de archivos CSV
    files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    
    if not files:
        return "No se encontraron archivos CSV en la carpeta", 404

    # Cargar los datos de los archivos CSV
    data = {}
    for file in files:
        try:
            parts = file.split('_')
            if len(parts) >= 2:
                month = parts[1]  # Esto será 'Enero', 'Febrero', etc.
                year = parts[2].split('.')[0]  # Asumimos que el año es la tercera parte y está seguido por la extensión .csv
                df = pd.read_csv(os.path.join(folder_path, file))
                key = f"{month} {year}"  # Combinar mes y año
                data[key] = df.to_dict(orient='records')
            else:
                print(f"Nombre de archivo inesperado: {file}")
        except Exception as e:
            print(f"Error al procesar el archivo {file}: {e}")

    if not data:
        return "No se cargaron datos", 500

    # Obtener el mes seleccionado desde el formulario
    selected_mes = request.args.get('mes')

    # Si hay un mes seleccionado, filtrar solo los datos de ese mes
    if selected_mes and selected_mes in data:
        data_filtrada = {selected_mes: data[selected_mes]}
    else:
        # Si no hay selección, mostrar todos los meses
        data_filtrada = data

    # Agrupar productos por tipo y sumar las cantidades
    for key, productos in data_filtrada.items():
        productos_agrupados = defaultdict(int)
        for producto in productos:
            tipo_producto = producto['Tipo']
            productos_agrupados[tipo_producto] += producto['Cantidad']
        
        # Crear una nueva lista con los productos agrupados y sumados
        data_filtrada[key] = [{'Tipo': tipo, 'Cantidad': cantidad} for tipo, cantidad in productos_agrupados.items()]

    # Enviar los datos y el mes seleccionado a la plantilla
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return render_template('ver.html', datos_por_mes=data_filtrada, todos_meses=list(data.keys()), selected_mes=selected_mes, timestamp=timestamp)

# Ruta para el formulario donde se selecciona el mes
@app.route('/form')
def form():
    folder_path = 'PRONOSTICO_MES'
    
    # Verificar que la carpeta existe
    if not os.path.exists(folder_path):
        return "La carpeta de datos no existe", 404

    # Obtener los archivos CSV y extraer los meses y años de los nombres de archivo
    files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    todos_meses = []
    
    # Diccionario para convertir nombres de meses a números
    meses_a_numero = {
        'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4, 'Mayo': 5, 'Junio': 6,
        'Julio': 7, 'Agosto': 8, 'Septiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12
    }

    for file in files:
        parts = file.split('_')
        if len(parts) >= 3:
            mes = parts[1]  # Extraemos el mes (e.g., Diciembre, Enero)
            year = parts[2].split('.')[0]  # Extraemos el año (e.g., 2024, 2025)
            # Convertir el mes a su número correspondiente
            mes_num = meses_a_numero.get(mes, 0)
            if mes_num > 0:
                # Convertir a un objeto datetime para ordenar
                mes_anio = datetime(int(year), mes_num, 1)
                # Guardar el objeto datetime y el nombre original del mes
                todos_meses.append((mes_anio, f"{mes} {year}"))

    # Ordenar la lista por los objetos datetime
    todos_meses.sort(key=lambda x: x[0])

    # Debug: imprimir todos los objetos ordenados para verificar
    print("Meses ordenados:", todos_meses)

    # Extraer solo los nombres de los meses ya ordenados
    todos_meses_ordenados = [mes[1] for mes in todos_meses]

    # Pasar los meses ordenados a la plantilla
    return render_template('form.html', todos_meses=todos_meses_ordenados)

# Función para generar el PDF a partir del archivo CSV
@app.route('/generar_pdf', methods=['POST'])
def generar_pdf():
    mes = request.form['mes']
    
    # Ruta a la carpeta donde están los archivos de pronóstico
    folder_path = 'PRONOSTICO_MES'
    
    # Verificar que la carpeta existe
    if not os.path.exists(folder_path):
        return "La carpeta de datos no existe", 404

    # Buscar el archivo correspondiente al mes seleccionado
    files = [f for f in os.listdir(folder_path) if f"predicciones_{mes.replace(' ', '_')}" in f and f.endswith('.csv')]
    
    if not files:
        return f"No se encontró el archivo CSV para el mes {mes}", 404

    # Cargar los datos del archivo CSV
    file_path = os.path.join(folder_path, files[0])
    df = pd.read_csv(file_path)

    # Crear el buffer de memoria para el PDF
    buffer = BytesIO()

    # Configuración del documento PDF
    pdf = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Obtener estilos de párrafo
    styles = getSampleStyleSheet()

    # Título del PDF
    report_title = f"REPORTE MES: {mes}"
    report_date = f"Fecha del reporte: {datetime.now().strftime('%d/%m/%Y')}"

    # Añadir título y fecha del reporte como párrafos
    elements.append(Paragraph(report_title, styles["Title"]))
    elements.append(Spacer(1, 12))  # Añadir un espaciado de 12 puntos entre el título y la fecha

    elements.append(Paragraph(report_date, styles["Normal"]))
    elements.append(Spacer(1, 12))  # Añadir un espaciado de 12 puntos entre la fecha y el resumen de datos

    # Datos adicionales
    total_productos = df['Cantidad'].sum()
    producto_mas_vendido = df.groupby('Tipo')['Cantidad'].sum().idxmax()
    cantidad_mas_vendida = df.groupby('Tipo')['Cantidad'].sum().max()

    # Añadir resumen de datos
    resumen_data = [
        ['Total de productos vendidos:', total_productos],
        ['Producto más vendido:', producto_mas_vendido],
        ['Cantidad más vendida de un producto:', cantidad_mas_vendida]
    ]

    resumen_table = Table(resumen_data, colWidths=[200, 300])
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(resumen_table)
    elements.append(Spacer(1, 24))  # Añadir un espaciado de 24 puntos entre el resumen y la tabla de productos

    # Añadir tabla de productos
    data = [['Tipo', 'Color', 'Material', 'Cantidad']] + df[['Tipo', 'Color', 'Material', 'Cantidad']].values.tolist()
    table = Table(data, colWidths=[240, 70, 75, 50])

    # Estilo de la tabla
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)

    # Construir el PDF
    pdf.build(elements)

    # Enviar el PDF generado
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f'reporte_{mes}.pdf')

@app.route('/ver_detalles', methods=['GET'])
def ver_detalles():
    selected_mes = request.args.get('mes')  # Obtener el mes seleccionado del formulario
    
    # Ruta a la carpeta donde están los archivos de pronóstico
    folder_path = 'PRONOSTICO_MES'

    # Verificar que la carpeta existe
    if not os.path.exists(folder_path):
        return "La carpeta de datos no existe", 404

    # Obtener lista de archivos CSV en la carpeta
    files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    
    # Lista para almacenar los datos de pronóstico
    pronostico_mes = []

    # Si hay un mes seleccionado, buscar solo archivos que coincidan con ese mes
    if selected_mes:
        for file in files:
            if selected_mes in file:  # Filtrar por el mes seleccionado
                file_path = os.path.join(folder_path, file)
                df = pd.read_csv(file_path)
                pronostico_mes = df.to_dict(orient='records')
                break  # Si encontramos el archivo, no es necesario continuar
    else:
        # Si no hay mes seleccionado, mostrar un mensaje vacío o cargar un archivo por defecto
        pronostico_mes = []

    # Obtener todos los meses posibles para el dropdown
    todos_meses = [file.split('_')[1].replace('.csv', '') for file in files]

    # Pasar los datos y el mes seleccionado al template
    return render_template('ver_detalles.html', pronostico_mes=pronostico_mes, todos_meses=todos_meses, selected_mes=selected_mes)

@app.route('/reentrenar_modelo', methods=['POST'])
def reentrenar_modelo():
    try:
        preprocesar_datos()
        entrenar_modelo()
        # Renderizar la plantilla con el mensaje de éxito
        return render_template('mes.html', mensaje_reentrenar="Reentrenamiento completado correctamente.")
    except Exception as e:
        # Imprimir el error en el servidor
        print(f"Error durante el reentrenamiento: {str(e)}")
        # Retornar un mensaje de error
        return render_template('mes.html', mensaje_reentrenar=f"Ocurrió un error: {str(e)}")

def realizar_reentrenamiento_programado():
    try:
        print(f"Reentrenamiento automático ejecutado en: {datetime.now()}")
        preprocesar_datos()
        entrenar_modelo()
        print("Reentrenamiento completado automáticamente.")
    except Exception as e:
        print(f"Error durante el reentrenamiento automático: {e}")

# Inicializar el scheduler y agregar la tarea
def iniciar_scheduler():
    scheduler = BackgroundScheduler()
    # Programar la tarea para que se ejecute cada primer día de cada mes a las 00:00
    scheduler.add_job(realizar_reentrenamiento_programado, 'cron', day=1, hour=0, minute=0)
    scheduler.start()

if __name__ == '__main__':
    if not os.path.exists('csv_files'):
        os.makedirs('csv_files')
    if not os.path.exists('pdf_files'):
        os.makedirs('pdf_files')
    if not os.path.exists('union_csv'):
        os.makedirs('union_csv')    
    app.run(debug=True)
