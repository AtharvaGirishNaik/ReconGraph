import os
import sqlite3
import logging
from typing import TypedDict, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", google_api_key=os.getenv("GEMINI_API_KEY"))

class ReconState(TypedDict):
    prompt: str
    schema: str
    generated_sql: Optional[str]
    execution_result: Optional[list]
    columns: Optional[list]
    error: Optional[str]
    retry_count: int
    audit_trail: List[str]

def generate_sql(state: ReconState) -> ReconState:
    system_prompt = f"""You are a financial data assistant.
    Write strictly valid SQLite queries based on the following schema:
    {state['schema']}
    
    Instructions:
    - Return ONLY the raw SQL query.
    - Do not include markdown formatting.
    - Do not provide explanations."""
    
    human_input = f"Task: {state['prompt']}"
    
    if state['error']:
        human_input += f"\n\nPrevious query:\n{state['generated_sql']}\nFailed with error:\n{state['error']}\nCorrect the SQL query."
        state['audit_trail'].append(f"Healing attempt {state['retry_count'] + 1} initiated.")
        logger.info(f"Initiating self-healing protocol. Retry count: {state['retry_count'] + 1}")

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=human_input)]
    response = llm.invoke(messages)
    
    
    raw_content = response.content
    if isinstance(raw_content, list):
        if isinstance(raw_content[0], dict) and "text" in raw_content[0]:
            raw_content = raw_content[0]["text"]
        else:
            raw_content = str(raw_content[0])
    elif not isinstance(raw_content, str):
        raw_content = str(raw_content)
        
    clean_sql = raw_content.replace('```sql', '').replace('```', '').strip()
    return {"generated_sql": clean_sql, "error": None}

def execute_sql(state: ReconState) -> ReconState:
    try:
        with sqlite3.connect('finance_records.db') as conn:
            cursor = conn.cursor()
            cursor.execute(state['generated_sql'])
            results = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
        state['audit_trail'].append(f"Execution successful. Rows retrieved: {len(results)}")
        return {"execution_result": results, "columns": columns, "error": None}
        
    except sqlite3.Error as e:
        error_msg = str(e)
        state['audit_trail'].append(f"Execution failed: {error_msg}")
        logger.warning(f"SQL Execution Error: {error_msg}")
        return {"error": error_msg, "retry_count": state['retry_count'] + 1}

def decide_next_step(state: ReconState) -> str:
    if state['error'] is None:
        return "end" 
    if state['retry_count'] >= 3:
        return "end" 
    return "generate" 

def build_recon_graph():
    workflow = StateGraph(ReconState)
    workflow.add_node("generate_sql_node", generate_sql)
    workflow.add_node("execute_sql_node", execute_sql)
    workflow.set_entry_point("generate_sql_node")
    workflow.add_edge("generate_sql_node", "execute_sql_node")
    workflow.add_conditional_edges(
        "execute_sql_node",
        decide_next_step,
        {
            "end": END,
            "generate": "generate_sql_node"
        }
    )
    return workflow.compile()