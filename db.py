# db.py
import mysql.connector

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