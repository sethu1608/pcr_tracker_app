# app/db.py
import mysql.connector
from datetime import datetime

MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',             # ✅ Change this
    'password': 'root', # ✅ Change this
    'database': 'pcr_tracker'   # ✅ Make sure this DB exists
}

def get_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)

def insert_pcr(symbol, expiry, strike_price, pcr, timestamp=None):
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO pcr_data (symbol, expiry, strike_price, pcr, timestamp)
        VALUES (%s, %s, %s, %s, %s)
    """
    if timestamp is None:
        timestamp = datetime.now()
    cursor.execute(query, (symbol, expiry, strike_price, pcr, timestamp))
    conn.commit()
    cursor.close()
    conn.close()

def get_pcr_data(symbol, expiry, timeframe="3m"):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if timeframe == "3m":
        group_expr = "timestamp"
    elif timeframe == "15m":
        group_expr = "DATE_FORMAT(DATE_SUB(timestamp, INTERVAL MINUTE(timestamp) % 15 MINUTE), '%Y-%m-%d %H:%i:00')"
    elif timeframe == "75m":
        group_expr = "DATE_FORMAT(DATE_SUB(timestamp, INTERVAL MINUTE(timestamp) % 75 MINUTE), '%Y-%m-%d %H:%i:00')"
    else:
        group_expr = "timestamp"

    query = f"""
        SELECT strike_price, ROUND(AVG(pcr), 2) AS pcr,
               {group_expr} AS timestamp
        FROM pcr_data
        WHERE symbol=%s AND expiry=%s
        GROUP BY strike_price, {group_expr}
        ORDER BY {group_expr}
    """
    cursor.execute(query, (symbol, expiry))
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data
