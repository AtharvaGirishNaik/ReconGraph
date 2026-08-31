import streamlit as st
import pandas as pd
import sqlite3
import time
from agent_graph import build_recon_graph

st.set_page_config(page_title="ReconGraph | AI Finance Controller", layout="wide", page_icon="⚡")

# --- UI Styling ---
st.markdown("""
    <style>
    .metric-card { background-color: #0E1117; padding: 20px; border-radius: 8px; border: 1px solid #2D3139; }
    .audit-log { font-family: monospace; color: #00FF00; background-color: #000; padding: 15px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ ReconGraph: Autonomous Finance Controller")
st.markdown("Automated Ledger vs. Gateway Reconciliation via Self-Healing Text-to-SQL")

# --- Initialize Agent ---
@st.cache_resource
def get_graph():
    return build_recon_graph()

graph = get_graph()

def fetch_schema():
    with sqlite3.connect('finance_records.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
        return "\n".join([row[0] for row in cursor.fetchall()])

schema = fetch_schema()

# --- Dashboard Layout ---
col1, col2, col3 = st.columns(3)
col1.metric("Total Records Processed", "60", "Daily Batch")
col2.metric("Exact Matches", "45", "75% Match Rate", delta_color="normal")
col3.metric("Exceptions Isolated", "15", "Requires Review", delta_color="inverse")

st.divider()

# --- Execution Controls ---
if st.button("🚀 Run Autonomous Reconciliation Batch", type="primary", use_container_width=True):
    
    match_prompt = "Find exact matches where internal_amount equals settled_amount. Return order_id, internal_amount, and settled_amount."
    exception_prompt = "Find exceptions where internal_amount does not match settled_amount, or where the gateway record is completely missing. Return order_id, internal_amount, and gateway_amount."
    
    tab1, tab2, tab3 = st.tabs(["Agent Audit Trail", "Exact Matches", "Exception Queue"])
    
    with tab1:
        st.subheader("LangGraph Execution Trace")
        log_container = st.empty()
        
        # --- Task 1: Matches ---
        initial_state = {
            "prompt": match_prompt,
            "schema": schema,
            "generated_sql": None,
            "execution_result": None,
            "columns": None,
            "error": None,
            "retry_count": 0,
            "audit_trail": ["> Initializing Task: Process Exact Matches..."]
        }
        
        with st.spinner("Agent generating Match SQL..."):
            final_match_state = graph.invoke(initial_state)
            log_text = "\n".join(final_match_state['audit_trail'])
            log_container.markdown(f'<div class="audit-log">{log_text}</div>', unsafe_allow_html=True)
            
            df_matches = pd.DataFrame(final_match_state['execution_result'], columns=final_match_state['columns'])
            
    with tab2:
        st.subheader("Validated Records (No Action Required)")
        st.dataframe(df_matches, use_container_width=True, hide_index=True)
            
    with tab1:
        st.write("---")
        # --- Task 2: Exceptions ---
        initial_exc_state = {
            "prompt": exception_prompt,
            "schema": schema,
            "generated_sql": None,
            "execution_result": None,
            "columns": None,
            "error": None,
            "retry_count": 0,
            "audit_trail": final_match_state['audit_trail'] + ["", "> Initializing Task: Isolate Exceptions..."]
        }
        
        with st.spinner("Agent generating Exception SQL (Monitoring for Hallucinations)..."):
            final_exc_state = graph.invoke(initial_exc_state)
            log_text = "\n".join(final_exc_state['audit_trail'])
            log_container.markdown(f'<div class="audit-log">{log_text}</div>', unsafe_allow_html=True)
            
            df_exceptions = pd.DataFrame(final_exc_state['execution_result'], columns=final_exc_state['columns'])
            
    with tab3:
        st.subheader("Flagged Exceptions (Action Required)")
        st.error(f"⚠️ {len(df_exceptions)} discrepancies detected between Internal Ledger and Payment Gateway.")
        st.dataframe(df_exceptions, use_container_width=True, hide_index=True)
        
        st.button("Trigger Auto-Refund Workflow (Mock)", disabled=True)