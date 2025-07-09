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

def get_pcr_data(symbol, expiry, timeframe="3m", strikes=None):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # ⏲ Time grouping expression
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

    # 🧾 Strike filter if any
    strike_filter = ""
    main_params = [symbol, expiry]
    subquery_params = [symbol, expiry]

    if strikes:
        strike_filter = "AND strike_price = ANY(%s)"
        main_params.append(strikes)
        subquery_params.append(strikes)

    # 📦 Subquery to get latest 120 grouped timestamps
    latest_timestamps_subquery = f"""
        SELECT DISTINCT {time_bucket} AS ts
        FROM pcr_data
        WHERE symbol = %s AND expiry = %s
        {strike_filter}
        ORDER BY ts DESC
        LIMIT 135
    """

    # 🧠 Main query with time filter
    query = f"""
        WITH latest_ts AS (
            {latest_timestamps_subquery}
        )
        SELECT 
            strike_price, 
            ROUND(AVG(pcr)::numeric, 2) AS pcr,
            {time_bucket} AS timestamp
        FROM pcr_data
        WHERE symbol = %s AND expiry = %s
        {strike_filter}
        AND ({time_bucket}) IN (SELECT ts FROM latest_ts)
        GROUP BY strike_price, {time_bucket}
        ORDER BY {time_bucket}
    """

    cursor.execute(query, tuple(subquery_params + main_params))
    data = cursor.fetchall()
    cursor.close()
    conn.close()

    # 🕒 Convert timestamp to IST string
    ist = pytz.timezone("Asia/Kolkata")
    for row in data:
        if isinstance(row["timestamp"], datetime):
            row["timestamp"] = row["timestamp"].astimezone(ist).strftime("%Y-%m-%d %H:%M")

    return data
