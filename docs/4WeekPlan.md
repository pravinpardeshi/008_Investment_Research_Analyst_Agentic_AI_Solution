# Investment Research Analyst Agent

## A Practical Agentic AI Capstone Project for Financial Services

---

# Why This Use Case?

The Investment Research Analyst Agent is an ideal project because it naturally combines:

* Agent orchestration
* Planning
* RAG
* Multi-agent collaboration
* MCP tools
* Memory
* Evaluation
* Observability
* Human-in-the-loop workflows

Unlike many toy agent projects, this closely resembles systems that banks, asset managers, wealth-management firms, and research organizations are actively exploring.

Most importantly:

✅ Can be built entirely on a personal laptop

✅ Does not require proprietary financial data

✅ Uses publicly available company reports and filings

---

# Project Vision

Given a question such as:

> Compare RBC and TD Bank as long-term investments.

The system should:

1. Create a research plan
2. Gather supporting evidence
3. Analyze financial performance
4. Identify risks
5. Generate an investment thesis
6. Produce an analyst report
7. Store findings for future reuse

---

# High-Level Architecture

```text
User
 ↓
Planner
 ↓
Research Tasks
 ↓
Research Agent
 ↓
Evidence Store
 ↓
Risk Analyst
 ↓
Investment Thesis Generator
 ↓
Reviewer
 ↓
Final Report
```

---

# Technology Stack

## LLM Layer

* Ollama
* Qwen 3 14B (recommended)
* Gemma 3
* DeepSeek
* Llama 3.1

---

## Backend

* FastAPI
* FastMCP

---

## Storage

* PostgreSQL

Stores:

* Research runs
* Findings
* Reflections
* User preferences
* Agent state

---

## Vector Database

* Qdrant (recommended)

Stores:

* Annual reports
* Quarterly reports
* Earnings transcripts
* Investor presentations

---

## Observability

* OpenTelemetry
* Langfuse

---

## Experiment Tracking

* MLflow

---

## Frontend

* HTML
* CSS
* JavaScript
* HTMX (optional)

---

# Public Data Sources

The project does not require proprietary data.

Use:

## Annual Reports

Examples:

* Royal Bank of Canada (RBC)
* Toronto-Dominion Bank (TD)
* Bank of Nova Scotia (Scotiabank)

---

## Quarterly Reports

Useful for:

* Trend analysis
* Earnings analysis

---

## Investor Presentations

Useful for:

* Strategic priorities
* Growth plans
* Risk disclosures

---

## Earnings Call Transcripts

Useful for:

* Management commentary
* Business outlook

---

## News Articles

Useful for:

* Recent developments
* Market sentiment

---

# Development Roadmap

---

# Phase 1 — MVP Research Assistant

## Goal

Build a single-agent research system.

---

## Workflow

```text
Question
 ↓
Retriever
 ↓
Context
 ↓
LLM
 ↓
Answer
```

---

## Example Query

> Compare RBC and TD Bank as long-term investments.

---

## Features

### Document Ingestion

```text
PDF
 ↓
Chunk
 ↓
Embed
 ↓
Qdrant
```

Supported documents:

* Annual reports
* Quarterly reports
* Investor presentations

---

### Basic RAG

Retrieve relevant content from:

* Financial reports
* Presentations
* Earnings transcripts

---

## Deliverable

Single-agent financial research assistant.

---

# Phase 2 — Planner + Researcher

## Goal

Move beyond simple retrieval.

---

## Planner Agent

Input:

> Compare RBC and TD Bank.

Output:

```json
{
  "tasks": [
    "Analyze profitability",
    "Analyze revenue growth",
    "Analyze capital strength",
    "Analyze risk factors",
    "Generate investment conclusion"
  ]
}
```

---

## Research Agent

For each task:

```text
Task
 ↓
Retrieve Documents
 ↓
Analyze Evidence
 ↓
Store Findings
```

---

## Suggested Database Tables

### research_runs

```sql
CREATE TABLE research_runs (
    id SERIAL PRIMARY KEY,
    query TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### findings

```sql
CREATE TABLE findings (
    id SERIAL PRIMARY KEY,
    run_id INT,
    topic TEXT,
    finding TEXT
);
```

---

## Deliverable

Planner-driven research workflow.

---

# Phase 3 — Multi-Agent System

## Goal

Introduce specialization.

---

## Agents

### Planner

Creates research plan.

---

### Researcher

Collects supporting evidence.

---

### Risk Analyst

Identifies:

* Credit risk
* Market risk
* Regulatory risk
* Interest-rate risk

---

### Writer

Generates analyst memo.

---

### Reviewer

Checks:

* Completeness
* Consistency
* Missing evidence

---

## Workflow

```text
User Query
      ↓
Planner
      ↓
Researcher
      ↓
Risk Analyst
      ↓
Writer
      ↓
Reviewer
      ↓
Final Memo
```

---

## Deliverable

Multi-agent research platform.

---

# Phase 4 — Memory Layer

## Goal

Build long-running intelligence.

---

## Store

### Research Reports

Historical reports.

---

### Findings

Previous conclusions.

---

### Reflection Notes

Lessons learned.

---

### Preferred Sources

Track high-quality evidence sources.

---

## Reflection Example

After each report:

```json
{
  "what_worked": "Quarterly reports provided strongest evidence",
  "what_failed": "Interest-rate sensitivity analysis was incomplete",
  "future_hint": "Always analyze net interest margin trends"
}
```

Store reflections in PostgreSQL.

---

## Deliverable

Persistent agent memory.

---

# Phase 5 — MCP Tool Ecosystem

## Goal

Introduce external tools.

---

## Filing Search Tool

```python
search_company_filings(company)
```

---

## Financial Metrics Tool

```python
get_financial_metrics(company)
```

---

## News Search Tool

```python
search_recent_news(company)
```

---

## Historical Report Search Tool

```python
search_previous_reports(query)
```

---

## MCP Workflow

```text
Research Agent
      ↓
Need Information
      ↓
MCP Tool Call
      ↓
Retrieve Data
      ↓
Continue Analysis
```

---

## Deliverable

Tool-enabled research agent.

---

# Phase 6 — Evaluation Framework

## Goal

Measure system quality.

---

## Benchmark Dataset

Create approximately 50–100 tasks.

---

## Example Tasks

### Task 1

Compare RBC and TD.

---

### Task 2

Analyze risks facing Canadian banks.

---

### Task 3

Evaluate impact of interest-rate cuts.

---

### Task 4

Analyze earnings trends.

---

## Metrics

### Completeness

Did all planned tasks get addressed?

---

### Citation Coverage

Was sufficient evidence used?

---

### Consistency

Does the conclusion align with findings?

---

### Hallucination Rate

Did the model invent unsupported facts?

---

## Deliverable

Automated evaluation harness.

---

# Phase 7 — Observability

## Goal

Understand system behavior.

---

## Langfuse

Track:

* Prompts
* Agent execution
* Tool usage
* Latency

---

## OpenTelemetry

Track:

* Traces
* Metrics
* Errors

---

## Deliverable

Full execution visibility.

---

# Phase 8 — Experiment Tracking

## Goal

Track improvements systematically.

---

## MLflow

Track:

### Models

Examples:

* Qwen 3
* DeepSeek
* Gemma

---

### Prompt Versions

Examples:

* Planner v1
* Planner v2
* Researcher v3

---

### Agent Graph Versions

Examples:

* Single Agent
* Planner + Researcher
* Planner + Researcher + Risk Analyst

---

### Evaluation Results

Track:

* Success rate
* Latency
* Hallucination rate
* Completeness

---

## Deliverable

Experiment management system.

---

# Suggested Folder Structure

```text
investment-research-agent/
│
├── frontend/
│
├── api/
│   ├── agents/
│   ├── workflows/
│   ├── memory/
│   ├── tools/
│   ├── evaluation/
│   └── models/
│
├── mcp/
│   ├── filing_server/
│   ├── news_server/
│   ├── metrics_server/
│   └── report_server/
│
├── data/
│   ├── annual_reports/
│   ├── quarterly_reports/
│   ├── earnings_calls/
│   └── presentations/
│
├── benchmarks/
│
├── mlflow/
│
├── langfuse/
│
└── docs/
```

---

# Recommended Initial Companies

Start with three companies in the same sector.

## Canadian Banks

* Royal Bank of Canada (RBC)
* Toronto-Dominion Bank (TD)
* Bank of Nova Scotia (Scotiabank)

Benefits:

* Similar business models
* Similar reporting structures
* Easier comparisons

---

# Final Portfolio Outcome

By the end of the project you will have:

* Multi-agent orchestration
* Financial document RAG
* MCP tool integration
* Persistent memory
* Reflection loops
* Evaluation framework
* Langfuse observability
* OpenTelemetry tracing
* MLflow experiment tracking
* Human-review workflow

This results in a realistic, enterprise-style Agentic AI platform that demonstrates advanced AI engineering skills while remaining fully implementable on a personal laptop.
