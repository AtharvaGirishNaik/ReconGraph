import logging
import pandas as pd
from agent_graph import build_recon_graph

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_SCHEMA = """
Table: internal_ledger
- id (INTEGER)
- order_id (TEXT)
- amount (REAL)
- created_at (TIMESTAMP)

Table: gateway_settlement
- id (INTEGER)
- order_id (TEXT)
- settled_amount (REAL)
- settled_at (TIMESTAMP)
- status (TEXT)
"""

def run_reconciliation_task(prompt: str, task_name: str):
    logger.info(f"Initializing task: {task_name}")
    graph = build_recon_graph()
    
    initial_state = {
        "prompt": prompt,
        "schema": DB_SCHEMA,
        "generated_sql": None,
        "execution_result": None,
        "columns": None,
        "error": None,
        "retry_count": 0,
        "audit_trail": ["Task initialized."]
    }
    
    final_state = graph.invoke(initial_state)
    
    print(f"\n--- Audit Trail: {task_name} ---")
    for log in final_state['audit_trail']:
        print(f" > {log}")
    print("-" * 40 + "\n")
    
    if final_state['error'] is None and final_state['execution_result'] is not None:
        df = pd.DataFrame(final_state['execution_result'], columns=final_state['columns'])
        return df, final_state['generated_sql']
    
    logger.error(f"Task aborted after {final_state['retry_count']} retries. Final Error: {final_state['error']}")
    return None, None

def main():
    logger.info("Booting ReconGraph Finance Controller")
    
    match_prompt = """
    Write a query that joins internal_ledger and gateway_settlement on order_id.
    Return order_id, internal_ledger.amount as internal_amount, gateway_settlement.settled_amount.
    ONLY include rows where the amounts match exactly.
    """
    
    df_matches, match_sql = run_reconciliation_task(match_prompt, "Process Exact Matches")
    if df_matches is not None:
        logger.info(f"Processed {len(df_matches)} exact match records.")
        print("Match Preview:")
        print(df_matches.head().to_string(index=False))
        print("\n")

    exception_prompt = """
    Write a query to find all reconciliation exceptions. An exception is defined as:
    1. An order_id in internal_ledger that does NOT exist in gateway_settlement.
    2. An order_id where internal_ledger.amount != gateway_settlement.settled_amount.
    Return order_id, internal_ledger.amount as internal_amt, gateway_settlement.settled_amount as gateway_amt.
    Use a LEFT JOIN from internal_ledger to gateway_settlement.
    """
    
    df_exceptions, exception_sql = run_reconciliation_task(exception_prompt, "Isolate Exceptions")
    if df_exceptions is not None:
        logger.info(f"Isolated {len(df_exceptions)} exceptions requiring human review.")
        print("Exception Preview:")
        print(df_exceptions.head().to_string(index=False))
        print("\n")
        
        total_records = 60
        match_rate = ((total_records - len(df_exceptions)) / total_records) * 100
        logger.info(f"Reconciliation Complete. Final Match Rate: {match_rate:.2f}%")

if __name__ == "__main__":
    main()
