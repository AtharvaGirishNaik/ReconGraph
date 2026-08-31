import sqlite3
import random
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_database():
    try:
        with sqlite3.connect('finance_records.db') as conn:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS internal_ledger (
                    id INTEGER PRIMARY KEY,
                    order_id TEXT,
                    amount REAL,
                    created_at TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gateway_settlement (
                    id INTEGER PRIMARY KEY,
                    order_id TEXT,
                    settled_amount REAL,
                    settled_at TIMESTAMP,
                    status TEXT
                )
            ''')

            cursor.execute('DELETE FROM internal_ledger')
            cursor.execute('DELETE FROM gateway_settlement')

            base_time = datetime.now()

            for i in range(1, 61):
                order_id = f"order_{1000 + i}"
                amount = round(random.uniform(500, 5000), 2)
                
                cursor.execute(
                    'INSERT INTO internal_ledger (order_id, amount, created_at) VALUES (?, ?, ?)', 
                    (order_id, amount, base_time)
                )

                scenario = random.random()
                
                if scenario < 0.70:
                    drifted_time = base_time + timedelta(seconds=random.randint(1, 10))
                    cursor.execute(
                        'INSERT INTO gateway_settlement (order_id, settled_amount, settled_at, status) VALUES (?, ?, ?, ?)', 
                        (order_id, amount, drifted_time, 'SUCCESS')
                    )
                
                elif scenario < 0.85:
                    drifted_time = base_time + timedelta(seconds=random.randint(1, 10))
                    cursor.execute(
                        'INSERT INTO gateway_settlement (order_id, settled_amount, settled_at, status) VALUES (?, ?, ?, ?)', 
                        (order_id, amount - 50.0, drifted_time, 'SUCCESS')
                    )
                
                base_time += timedelta(minutes=15)

            conn.commit()
            logger.info("Synthetic database 'finance_records.db' successfully initialized with 60 records.")

    except sqlite3.Error as e:
        logger.error(f"Database initialization failed: {e}")

if __name__ == "__main__":
    setup_database()
