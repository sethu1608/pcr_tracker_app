# app/db.py
from datetime import datetime
import pytz
import psycopg2
from psycopg2.extras import RealDictCursor

POSTGRES_CONFIG = {
    'host': '13.203.155.8',
    'port': 5432,
    'user': 'pcr_user',
    'password': 'pcr_pass',
    'dbname': 'pcr_db'
}

def get_connection():
    return psycopg2.connect(**POSTGRES_CONFIG)

def insert_pcr(symbol, expiry, strike_price, pcr, timestamp=None):
    conn = get_connection()
    cursor = conn.cursor()
    if timestamp is None:
        # ✅ Convert to IST
        ist = pytz.timezone("Asia/Kolkata")
        timestamp = datetime.now(ist)
    query = """
        INSERT INTO pcr_data (symbol, expiry, strike_price, pcr, timestamp)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (symbol, expiry, strike_price, pcr, timestamp))
    conn.commit()
    cursor.close()
    conn.close()

from datetime import datetime
import pytz

def get_pcr_data(symbol, expiry, timeframe="3m"):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if timeframe == "3m":
        time_bucket = "timestamp AT TIME ZONE 'Asia/Kolkata'"
    elif timeframe == "15m":
        time_bucket = """
            (date_trunc('minute', timestamp) - 
            INTERVAL '1 minute' * (EXTRACT(minute FROM timestamp)::int %% 15)) AT TIME ZONE 'Asia/Kolkata'
        """
    elif timeframe == "75m":
        time_bucket = """
            TO_TIMESTAMP(FLOOR(EXTRACT(EPOCH FROM timestamp) / (75 * 60)) * (75 * 60)) AT TIME ZONE 'Asia/Kolkata'
        """
    else:
        time_bucket = "timestamp AT TIME ZONE 'Asia/Kolkata'"

    query = f"""
        SELECT 
            strike_price, 
            ROUND(AVG(pcr)::numeric, 2) AS pcr,
            {time_bucket} AS timestamp
        FROM pcr_data
        WHERE symbol = %s AND expiry = %s
        GROUP BY strike_price, {time_bucket}
        ORDER BY {time_bucket}
    """

    cursor.execute(query, (symbol, expiry))
    data = cursor.fetchall()
    cursor.close()
    conn.close()

    # 🛠 Format timestamps as IST strings
    for row in data:
        if isinstance(row["timestamp"], datetime):
            ist = pytz.timezone("Asia/Kolkata")
            row["timestamp"] = row["timestamp"].astimezone(ist).strftime("%Y-%m-%d %H:%M")

    return data
