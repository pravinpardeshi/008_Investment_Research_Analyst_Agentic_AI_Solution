# Investment Research Analyst Agent - MVP Specification

## Objective

Build a local-first Agentic AI application that acts as an Investment Research Analyst.

The system should analyze publicly available company documents and generate structured investment research reports.

The application must run entirely on a personal workstation using Ollama-hosted models.

---

# Business Problem

Investment analysts spend significant time:

- Reading annual reports
- Reviewing quarterly filings
- Comparing companies
- Identifying risks
- Writing investment memos

The goal is to automate the first-pass research process.

The system should gather evidence, analyze documents, identify risks, and produce a professional investment research report.

---

# Example User Questions

- Compare RBC and TD Bank as long-term investments.
- Analyze the risks facing TD Bank.
- Summarize RBC's recent earnings performance.
- Compare profitability trends between RBC and Scotiabank.
- What are the major strategic initiatives mentioned in RBC annual reports?

---

# Scope

## In Scope

- Document ingestion
- Vector search
- Multi-agent workflow
- Investment report generation
- Report storage
- Historical report retrieval
- Local LLM execution using Ollama

## Out of Scope

- Real-time market data
- Trading recommendations
- Portfolio optimization
- Stock price forecasting
- External paid APIs

---

# Technology Stack

## Backend

- Python 3.12
- FastAPI

## Database

- PostgreSQL

## Vector Database

- Qdrant

## LLM

- Ollama

Recommended models:

- qwen3:14b
- llama3.1:8b

## Embeddings

Use local embedding model via Ollama.

## Frontend

- HTML
- CSS
- JavaScript

No React required.

---

# User Workflow

## Step 1

User uploads documents.

Examples:

- Annual reports
- Quarterly reports
- Investor presentations
- Earnings call transcripts

---

## Step 2

System processes documents.

Pipeline:

PDF
→ Extract text
→ Chunk text
→ Generate embeddings
→ Store in Qdrant

Metadata stored in PostgreSQL.

---

## Step 3

User submits research question.

Example:

Compare RBC and TD Bank as long-term investments.

---

## Step 4

Planner Agent creates research plan.

Example:

1. Analyze profitability
2. Analyze revenue growth
3. Analyze capital strength
4. Analyze strategic initiatives
5. Analyze risks
6. Generate conclusion

---

## Step 5

Research Agent executes each task.

For every task:

- Search Qdrant
- Retrieve evidence
- Summarize findings

Store findings in PostgreSQL.

---

## Step 6

Risk Analyst reviews findings.

Identify:

- Regulatory risks
- Market risks
- Interest-rate risks
- Credit risks

Store results.

---

## Step 7

Writer Agent creates report.

Report sections:

### Executive Summary

### Company Overview

### Financial Analysis

### Strategic Analysis

### Risk Analysis

### Investment Thesis

### Conclusion

---

## Step 8

Reviewer Agent validates report.

Checks:

- Missing sections
- Unsupported conclusions
- Lack of evidence

Reviewer can request revisions.

Maximum 2 review cycles.

---

## Step 9

Final report stored in PostgreSQL.

---

# Functional Requirements

## Document Management

### Upload Document

Endpoint:

POST /documents/upload

Accept:

- PDF
- DOCX
- TXT

Store metadata in PostgreSQL.

Store embeddings in Qdrant.

---

### List Documents

Endpoint:

GET /documents

Returns:

- Document name
- Company
- Upload date

---

# Research Requests

## Create Research Request

Endpoint:

POST /research

Request:

```json
{
  "question": "Compare RBC and TD Bank as long-term investments."
}
```

Response:

```json
{
  "research_id": 123
}
```

---

## Get Research Status

Endpoint:

GET /research/{id}

Returns:

```json
{
  "status": "completed"
}
```

Possible statuses:

- pending
- running
- completed
- failed

---

## Get Final Report

Endpoint:

GET /research/{id}/report

Returns generated report.

---

# Agent Requirements

## Planner Agent

Input:

User question.

Output:

List of research tasks.

Example:

```json
[
  "Analyze profitability",
  "Analyze revenue growth",
  "Analyze risks"
]
```

---

## Research Agent

Input:

Research task.

Responsibilities:

- Query vector database
- Retrieve evidence
- Summarize findings

Output:

Structured finding.

Example:

```json
{
  "topic": "profitability",
  "summary": "RBC reported higher ROE than TD."
}
```

---

## Risk Analyst Agent

Input:

Research findings.

Output:

Risk assessment.

Example:

```json
{
  "risk_type": "interest_rate",
  "description": "Profitability sensitive to rate reductions."
}
```

---

## Writer Agent

Input:

Research findings.

Output:

Complete investment memo.

Markdown format.

---

## Reviewer Agent

Input:

Draft report.

Output:

Review comments.

Example:

```json
{
  "approved": false,
  "comments": [
    "Risk section lacks evidence."
  ]
}
```

---

# Database Schema

## documents

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename TEXT,
    company TEXT,
    uploaded_at TIMESTAMP DEFAULT NOW()
);
```

---

## research_runs

```sql
CREATE TABLE research_runs (
    id SERIAL PRIMARY KEY,
    question TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## findings

```sql
CREATE TABLE findings (
    id SERIAL PRIMARY KEY,
    research_run_id INT,
    topic TEXT,
    content TEXT
);
```

---

## reports

```sql
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    research_run_id INT,
    report_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

# Memory Requirements

Store:

- Previous reports
- Previous findings
- Historical research questions

Allow future retrieval.

---

# Evaluation Requirements

Metrics:

- Report completeness
- Citation count
- Number of retrieved chunks
- Agent execution time

Store metrics in PostgreSQL.

---

# Non-Functional Requirements

## Local First

No cloud dependencies.

---

## Modular

Agents must be independent classes.

---

## Extensible

Additional agents should be easy to add.

---

## Observable

Log:

- Agent execution
- Prompt inputs
- Prompt outputs
- Tool calls

---

# Project Structure

Use the previously defined folder structure.

---

# Success Criteria

A user can:

1. Upload company reports.
2. Ask an investment research question.
3. Observe multi-agent execution.
4. Receive a structured investment report.
5. Retrieve historical reports.
6. Run entirely on a local machine using Ollama.