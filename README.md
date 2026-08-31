# ReconGraph: Autonomous Self-Healing Finance Controller

**Razorpay AI Buildathon | Track 04: AI Finance Controller**

ReconGraph is an autonomous, graph-based AI agent engineered to automate multi-source financial reconciliation. It uses a **self-healing Text-to-SQL pipeline** to dynamically reconcile internal ledgers against payment gateway settlements, isolate financial exceptions, and maintain a transparent execution trail for auditability.

Unlike a conventional LLM-based SQL generator, ReconGraph does not terminate when the generated query fails. It captures the database error, feeds the failure context back into the agent, and allows the system to iteratively correct its query within a strictly bounded execution loop.

---

## 🚨 Problem Statement

Financial reconciliation is inherently difficult because transaction data rarely produces clean 1:1 matches.

When internal order ledgers are reconciled against payment gateway settlements, discrepancies can arise from:

* Timestamp drift
* Partial refunds
* Gateway fee deductions
* Missing settlement records
* Amount discrepancies
* Inconsistent transaction data

Traditional deterministic reconciliation scripts are often brittle when these edge cases occur.

### The LLM Problem

A straightforward approach is to use an LLM to generate SQL from a natural-language reconciliation requirement.

However, this introduces another class of failures:

* Hallucinated column names
* Incorrect table references
* Invalid SQL syntax
* Incorrect `JOIN` conditions
* Misinterpretation of schema relationships

A single malformed query can cause an entire reconciliation batch to fail.

**ReconGraph solves this by treating SQL generation as an iterative execution-and-recovery process rather than a one-shot LLM call.**

---

# 💡 Solution

ReconGraph implements a **cyclic state-machine architecture using LangGraph**.

The agent follows a controlled loop:

```text
        ┌─────────────────────┐
        │   Database Schema   │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │   Generate SQL      │
        │     with LLM        │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │    Execute SQL      │
        └──────────┬──────────┘
                   │
             ┌─────┴─────┐
             │           │
          SUCCESS       ERROR
             │           │
             ▼           ▼
       Process Result   Capture
                       Traceback
                           │
                           ▼
                  ┌─────────────────┐
                  │  Self-Healing   │
                  │   Agent Loop    │
                  └────────┬────────┘
                           │
                           ▼
                    Retry SQL Query
```

The system combines LLM reasoning with deterministic database execution and explicit failure handling.

---

# 🧠 Core Capabilities

## 1. Stateful Schema-Aware Execution

ReconGraph dynamically provides the agent with the relevant database schema before generating SQL.

This grounds query generation against the actual database structure and reduces the likelihood of hallucinated:

* Tables
* Columns
* Relationships
* Schema properties

The workflow is maintained through a shared LangGraph state rather than a stateless sequence of LLM calls.

---

## 2. Autonomous SQL Healing

When the generated SQL fails during SQLite execution, ReconGraph does not immediately terminate the reconciliation process.

The execution node captures the database error and routes the failure information back into the agent.

The LLM receives the relevant context, including:

* Previously generated SQL
* Database schema
* SQLite execution error
* Current retry state

It can then generate a corrected query and attempt execution again.

```text
Generated SQL
      │
      ▼
SQLite Execution
      │
      ├─────────────── Success ──────────────► Continue
      │
      ▼
sqlite3.Error
      │
      ▼
Capture traceback
      │
      ▼
Feed error back to agent
      │
      ▼
Generate corrected SQL
      │
      ▼
Retry execution
```

This transforms database errors from terminal failures into actionable feedback.

---

## 3. Strict Exception Isolation

ReconGraph does not attempt to force every transaction into a successful match.

Instead, the system explicitly identifies reconciliation exceptions such as:

### Amount Discrepancies

A transaction exists in both sources, but the amounts differ.

```text
Internal Ledger       Gateway Settlement
      ₹1,000                ₹980
         │                    │
         └────── MISMATCH ────┘
```

### Missing Gateway Records

An internal transaction exists, but no corresponding gateway settlement can be identified.

```text
Internal Ledger
TXN_1024
    │
    ▼
Gateway Settlement
NOT FOUND
    │
    ▼
MISSING_RECORD
```

This prevents the reconciliation system from silently converting uncertain transactions into false positives.

---

## 4. Transparent Auditability

Every important stage of the reconciliation process is recorded in an execution trace.

The trace captures:

* Generated SQL
* Query execution results
* SQL errors
* Retry attempts
* Self-correction cycles
* Final reconciliation outcome

This makes the agent's behaviour observable and allows operators to understand **what the system attempted, what failed, and how it recovered**.

---

# 🏗️ Architecture

ReconGraph is built around four primary components:

```text
┌─────────────────────────────────────────────────────┐
│                    ReconGraph                       │
│                                                     │
│  ┌──────────────┐     ┌─────────────────────────┐  │
│  │ Schema       │────►│ LLM SQL Generation      │  │
│  │ Inspection   │     │ Gemini 1.5 Flash        │  │
│  └──────────────┘     └────────────┬────────────┘  │
│                                    │               │
│                                    ▼               │
│                         ┌─────────────────────┐    │
│                         │ SQLite Execution    │    │
│                         └──────────┬──────────┘    │
│                                    │               │
│                          ┌─────────┴─────────┐     │
│                          │                   │     │
│                       Success              Error  │
│                          │                   │     │
│                          ▼                   ▼     │
│                    Reconciliation       Self-Heal │
│                       Results              Loop    │
│                          │                   │     │
│                          └─────────┬─────────┘     │
│                                    ▼               │
│                           Exception Analysis       │
│                                    │               │
│                                    ▼               │
│                            Execution Trace         │
└─────────────────────────────────────────────────────┘
```

---

# 🛠️ Technical Stack

| Component            | Technology                       |
| -------------------- | -------------------------------- |
| Programming Language | Python                           |
| Database Engine      | SQLite3                          |
| Agent Framework      | LangGraph                        |
| LLM Framework        | LangChain Core                   |
| Large Language Model | Google Gemini 1.5 Flash          |
| Dataset              | Synthetic financial transactions |
| Records              | 60 dynamically generated records |
| Query Strategy       | Schema-aware Text-to-SQL         |
| Recovery Mechanism   | Error-driven SQL self-healing    |
| Execution Control    | Bounded LangGraph state machine  |

---

# 📊 Synthetic Dataset

ReconGraph uses **60 dynamically generated synthetic transaction records** designed to reproduce common financial reconciliation anomalies.

The dataset intentionally introduces conditions such as:

* Timestamp drift
* Missing gateway records
* Transaction mismatches
* Amount discrepancies

This provides a controlled environment for testing the agent's ability to identify exceptions instead of assuming that every transaction can be successfully reconciled.

The dataset is generated into:

```text
finance_records.db
```

---

# 🔄 Self-Healing Control Loop

One of the primary engineering challenges during development was preventing repeated SQL-generation failures from creating an infinite execution loop.

## The Problem

Early implementations used a conventional `while` loop:

```text
Generate SQL
     │
     ▼
Execute
     │
     ▼
Error
     │
     ▼
Generate SQL Again
     │
     ▼
Same Error
     │
     ▼
Repeat indefinitely
```

If the LLM repeatedly generated the same invalid `LEFT JOIN` syntax, the agent could continue retrying indefinitely.

This created two major risks:

1. Unbounded execution
2. Unnecessary API consumption

---

## The Solution

The architecture was migrated from an unrestricted loop to a **strict LangGraph state machine**.

A `retry_count` parameter was introduced into the `ReconState` structure.

The graph uses conditional routing to determine whether the agent should:

* Retry the failed query
* Continue processing
* Terminate execution

```text
                 ┌───────────────┐
                 │ Generate SQL  │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Execute Query │
                 └───────┬───────┘
                         │
                 ┌───────┴────────┐
                 │                │
              SUCCESS            ERROR
                 │                │
                 ▼                ▼
              Continue      retry_count++
                                  │
                         ┌────────┴────────┐
                         │                 │
                       < 3               >= 3
                         │                 │
                         ▼                 ▼
                    Self-Heal            END
```

The system allows a maximum of **three attempts**.

If valid SQL cannot be generated within that limit, the graph terminates gracefully instead of entering an infinite loop.

---

# 🧪 Error-Driven Self-Correction

A critical improvement was passing the precise `sqlite3.Error` traceback back to the LLM during the healing cycle.

Instead of simply telling the model:

```text
"Your SQL failed."
```

ReconGraph provides the actual execution failure.

For example:

```text
sqlite3.OperationalError:
no such column: gateway.payment_identifier
```

This gives the LLM concrete information about what went wrong and allows it to regenerate the query using the database schema and execution feedback.

The result was a substantial improvement in the agent's ability to correct failed SQL queries during subsequent attempts.

---

# 📁 Project Structure

```text
recongraph-buildathon/
│
├── main.py
├── mock_data.py
├── requirements.txt
├── .env
├── finance_records.db
└── README.md
```

### File Responsibilities

| File                 | Purpose                                        |
| -------------------- | ---------------------------------------------- |
| `main.py`            | Main LangGraph reconciliation controller       |
| `mock_data.py`       | Generates synthetic financial transaction data |
| `requirements.txt`   | Python project dependencies                    |
| `.env`               | Gemini API configuration                       |
| `finance_records.db` | Generated SQLite database                      |
| `README.md`          | Project documentation                          |

> `finance_records.db` is generated by `mock_data.py` and does not need to be manually created.

---

# ⚡ Installation & Execution

## 1. Clone the Repository

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/recongraph-buildathon.git
cd recongraph-buildathon
```

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Configure Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
```

Replace `your_api_key_here` with your Google Gemini API key.

> **Important:** Never commit API credentials to GitHub.

A recommended `.gitignore` should include:

```gitignore
.env
*.db
__pycache__/
*.pyc
```

---

## 4. Generate Synthetic Data

Run:

```bash
python mock_data.py
```

This provisions:

```text
finance_records.db
```

The generated database contains 60 synthetic transaction records with intentionally injected reconciliation anomalies.

---

## 5. Run ReconGraph

Start the reconciliation controller:

```bash
python main.py
```

The system will:

1. Inspect the available database schema
2. Generate reconciliation SQL
3. Execute the generated query
4. Detect SQL execution failures
5. Capture SQLite error information
6. Feed the failure context back to the LLM
7. Attempt self-healing
8. Identify reconciliation exceptions
9. Produce an execution audit trail
10. Terminate after the configured retry limit if recovery fails

---

# 🔍 Example Self-Healing Flow

A simplified execution sequence looks like:

```text
────────────────────────────────────────────
ATTEMPT 1
────────────────────────────────────────────

Generate SQL
      │
      ▼
Execute Query
      │
      ▼
FAILED

sqlite3.Error:
Invalid column reference


────────────────────────────────────────────
SELF-HEALING
────────────────────────────────────────────

Failed SQL
     +
Database Schema
     +
SQLite Error
     │
     ▼
LLM generates corrected SQL


────────────────────────────────────────────
ATTEMPT 2
────────────────────────────────────────────

Execute Corrected Query
      │
      ▼
SUCCESS
      │
      ▼
Continue Reconciliation
```

If the query continues to fail after three attempts:

```text
ATTEMPT 3
    │
    ▼
FAILED
    │
    ▼
Retry Limit Reached
    │
    ▼
END
```

This guarantees that the autonomous healing mechanism remains bounded.

---

# 🎯 Key Design Principles

### 1. Treat LLM SQL as Untrusted

LLM-generated SQL should never be assumed to be correct.

ReconGraph validates generated queries through actual database execution.

### 2. Use Errors as Feedback

Database errors contain useful information.

ReconGraph feeds execution failures back into the generation process rather than treating them as terminal events.

### 3. Never Manufacture Matches

The system explicitly identifies discrepancies and missing records instead of forcing transactions into successful matches.

### 4. Bound Autonomous Behaviour

Autonomous agents require operational limits.

The `retry_count` mechanism prevents infinite loops and uncontrolled API usage.

### 5. Make Agent Behaviour Auditable

Every generation, execution, failure, and recovery step is captured in the execution trace.

---

# 🏆 Why ReconGraph?

ReconGraph demonstrates how **agentic AI can be applied to financial reconciliation while maintaining deterministic execution boundaries**.

Instead of building a system where an LLM is trusted to produce perfect SQL, ReconGraph creates a feedback loop:

```text
        LLM
         │
         ▼
    Generate SQL
         │
         ▼
  Deterministic DB
     Execution
         │
    ┌────┴────┐
    │         │
 Success     Error
    │         │
    │         ▼
    │     Error Feedback
    │         │
    │         ▼
    │       LLM
    │         │
    │         ▼
    │    Corrected SQL
    │
    ▼
Reconciliation
```

The fundamental design principle is:

> **The LLM does not need to be perfect. The system needs to be capable of detecting, recovering from, and safely terminating around LLM failures.**

---

# 🔮 Future Enhancements

ReconGraph can be extended into a production-grade financial reconciliation platform through:

### Multi-Source Reconciliation

Support additional sources such as:

* Bank statements
* Payment gateways
* ERP systems
* Accounting platforms
* Internal order management systems

### Human-in-the-Loop Resolution

Allow finance operators to review and approve high-risk reconciliation exceptions.

### Confidence Scoring

Assign confidence scores to transaction matches and exception classifications.

### Advanced Anomaly Detection

Use dedicated ML models to identify anomalous transactions beyond deterministic amount and record matching.

### Production Database Support

Extend the execution layer beyond SQLite to databases such as PostgreSQL or MySQL.

### Advanced Observability

Track operational metrics including:

* SQL generation success rate
* Average retry count
* Reconciliation exception rate
* Query execution time
* Agent failure rate
* API/token consumption

### Persistent Audit Storage

Store execution traces in a dedicated audit datastore for long-term operational analysis and compliance requirements.

---

# ⚠️ Limitations

ReconGraph is currently a **buildathon prototype** and operates on synthetic financial data.

It should not be directly deployed for production financial reconciliation without additional controls covering:

* Authentication and authorization
* Data validation
* PII protection
* Secure secret management
* Database access controls
* Transaction isolation
* Human approval workflows
* Production-grade monitoring
* Comprehensive test coverage
* SQL execution safeguards

LLM-generated SQL should always be treated as untrusted input and validated before execution in a production environment.

---

# 🔐 Security

Do not commit API keys or other secrets to the repository.

Use environment variables:

```env
GEMINI_API_KEY=your_api_key_here
```

Recommended `.gitignore`:

```gitignore
.env
*.db
__pycache__/
*.pyc
```

For production deployments, secrets should be managed through a dedicated secrets-management system rather than committed configuration files.

---

# 👨‍💻 Author

**Atharva Girish Naik**

Developed for the **Razorpay AI Buildathon — Track 04: AI Finance Controller**.

---

## ⭐ Core Takeaway

ReconGraph is more than a conventional Text-to-SQL application.

It combines:

```text
Schema Awareness
       ↓
LLM SQL Generation
       ↓
Deterministic Execution
       ↓
Error Detection
       ↓
Autonomous SQL Healing
       ↓
Bounded Retry Control
       ↓
Exception Isolation
       ↓
Auditable Execution Trace
```

**ReconGraph turns LLM SQL generation from a fragile one-shot operation into a bounded, self-healing reconciliation workflow.**
