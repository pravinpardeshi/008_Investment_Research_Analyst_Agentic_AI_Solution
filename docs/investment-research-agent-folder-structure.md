# Investment Research Agent - Folder Structure Explained

## Overview

The folder structure is designed for a production-style Agentic AI application.

The architecture separates:

- User interface
- Agent logic
- Workflow orchestration
- Memory
- Tools
- MCP servers
- Data sources
- Evaluation
- Experiment tracking
- Documentation

The goal is to evolve from a simple RAG application into a complete multi-agent research platform.

---

# Project Root

```
investment-research-agent/
```

The root directory contains all components of the project.

```
investment-research-agent/
│
├── frontend/
├── api/
├── mcp/
├── data/
├── benchmarks/
├── mlflow/
├── langfuse/
└── docs/
```

---

# frontend/

## Purpose

Contains the user interface.

The UI allows users to:

- Submit research questions
- View generated investment reports
- Review evidence
- Approve reports
- Monitor agent execution

Example:

```
frontend/
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── templates/
│   ├── index.html
│   ├── report.html
│   └── history.html
│
└── components/
```

Possible technologies:

- HTML
- CSS
- JavaScript
- HTMX

---

# api/

## Purpose

The core backend application.

This contains:

- Agents
- Workflows
- Memory
- Tools
- Evaluation logic
- Data models

---

# api/agents/

## Purpose

Contains individual AI agent implementations.

Example:

```
agents/
├── planner.py
├── researcher.py
├── risk_analyst.py
├── writer.py
└── reviewer.py
```

---

## Planner Agent

Responsible for breaking down user questions.

Example:

Input:

```
Compare RBC and TD Bank as investments
```

Output:

```
Tasks:
1. Analyze profitability
2. Analyze revenue growth
3. Analyze capital strength
4. Analyze risks
5. Generate conclusion
```

---

## Researcher Agent

Responsibilities:

- Search documents
- Retrieve evidence
- Summarize findings

---

## Risk Analyst Agent

Analyzes:

- Market risk
- Regulatory risk
- Credit risk
- Interest-rate risk

---

## Writer Agent

Creates:

- Investment thesis
- Research report
- Executive summary

---

## Reviewer Agent

Checks:

- Completeness
- Evidence quality
- Logical consistency

---

# api/workflows/

## Purpose

Controls agent execution order.

Example:

```
User Question

     |
     v

Planner

     |
     v

Researcher

     |
     v

Risk Analyst

     |
     v

Writer

     |
     v

Reviewer

     |
     v

Final Report
```

Example files:

```
workflows/
├── research_workflow.py
├── review_workflow.py
└── approval_workflow.py
```

Responsibilities:

- Agent sequencing
- Passing context
- Error handling
- Retry handling

---

# api/memory/

## Purpose

Manages short-term and long-term memory.

Examples:

## Short-Term Memory

Stores:

- Current conversation
- Current research task
- Intermediate findings


## Long-Term Memory

Stores:

- Previous reports
- Historical analysis
- Research preferences
- Agent reflections

Example:

```
memory/
├── postgres_memory.py
├── vector_memory.py
└── reflections.py
```

---

# api/tools/

## Purpose

Contains tools used by agents.

Examples:

```
tools/
├── filing_search.py
├── calculator.py
├── document_loader.py
├── qdrant_search.py
└── web_search.py
```

Possible tools:

```
search_filings()

retrieve_documents()

calculate_growth_rate()

search_news()

```

Agents call these tools when additional information is required.

---

# api/evaluation/

## Purpose

Measures agent performance.

Example:

```
evaluation/
├── benchmark_runner.py
├── metrics.py
├── judge.py
└── reports.py
```

Metrics:

- Accuracy
- Completeness
- Citation coverage
- Hallucination rate
- Response latency

---

# api/models/

## Purpose

Contains application data models.

Example:

```
models/
├── company.py
├── report.py
├── finding.py
└── research_run.py
```

Contains:

- SQLAlchemy models
- Pydantic schemas
- Database entities

---

# mcp/

## Purpose

Contains Model Context Protocol servers.

MCP servers expose tools that agents can discover and use.

Example:

```
mcp/

├── filing_server/
├── news_server/
├── metrics_server/
└── report_server/
```

---

# mcp/filing_server/

Provides financial filing tools.

Examples:

```
search_filings()

get_annual_report()

get_quarterly_report()
```

Used by the Research Agent.

---

# mcp/news_server/

Provides news-related capabilities.

Examples:

```
search_news()

get_recent_articles()
```

Used for:

- Market events
- Company announcements
- Risk analysis

---

# mcp/metrics_server/

Provides financial calculations.

Examples:

```
calculate_roe()

calculate_roa()

calculate_growth()

calculate_margin()
```

---

# mcp/report_server/

Provides access to historical research.

Examples:

```
search_previous_reports()

retrieve_report()
```

Useful for:

- Memory
- Trend analysis
- Comparing previous investment theses

---

# data/

## Purpose

Stores source documents.

Example:

```
data/

├── annual_reports/
├── quarterly_reports/
├── earnings_calls/
└── presentations/
```

---

# data/annual_reports/

Contains:

- Company annual reports
- Financial statements
- Management discussion

Example:

```
RBC_2024_Annual_Report.pdf
TD_2024_Annual_Report.pdf
```

---

# data/quarterly_reports/

Contains:

- Quarterly earnings reports
- Financial updates

Example:

```
RBC_Q1_2025.pdf
RBC_Q2_2025.pdf
```

---

# data/earnings_calls/

Contains:

- Earnings transcripts
- Management commentary

Useful for understanding:

- Strategy
- Market outlook
- Risks

---

# data/presentations/

Contains:

- Investor presentations
- Strategy documents

---

# benchmarks/

## Purpose

Contains evaluation datasets.

Example:

```
benchmarks/

├── tasks.json
├── expected_outputs.json
└── evaluation_results/
```

Example task:

```json
{
  "question": "Compare RBC and TD profitability"
}
```

Used to test:

- Agent quality
- Model changes
- Prompt changes

---

# mlflow/

## Purpose

Tracks experiments.

Tracks:

- Model versions
- Prompt versions
- Agent workflow versions
- Evaluation results

Example:

```
Experiment A

Model:
Qwen3

Workflow:
Planner + Researcher

Score:
82%
```

```
Experiment B

Model:
DeepSeek

Workflow:
Planner + Researcher + Risk Analyst

Score:
89%
```

---

# langfuse/

## Purpose

Observability and debugging.

Tracks:

- Agent execution
- Prompts
- Tool calls
- Latency
- Failures

Useful for understanding:

"Why did the agent produce this answer?"

---

# docs/

## Purpose

Project documentation.

Example:

```
docs/

├── architecture.md
├── agents.md
├── workflows.md
├── evaluation.md
└── roadmap.md
```

Documents:

- System design
- Agent responsibilities
- APIs
- MCP interfaces
- Evaluation strategy

---

# Recommended Development Sequence

## Phase 1 - Foundation

Build:

```
frontend/
api/
data/
models/
```

Goal:

Single-agent RAG research assistant.

---

## Phase 2 - Agent System

Add:

```
agents/
workflows/
tools/
```

Goal:

Planner + Researcher + Writer workflow.

---

## Phase 3 - Advanced Intelligence

Add:

```
memory/
benchmarks/
evaluation/
```

Goal:

Persistent memory and quality measurement.

---

## Phase 4 - Enterprise Features

Add:

```
mcp/
langfuse/
mlflow/
```

Goal:

Production-style agent platform.

---

# Final Architecture

```
                    User
                      |
                      v
                 Frontend
                      |
                      v
                  FastAPI
                      |
                      v
              Agent Workflow Engine
                      |
       --------------------------------
       |              |               |
       v              v               v
    Planner      Researcher       Risk Analyst
                      |
                      v
                   Writer
                      |
                      v
                  Reviewer

       --------------------------------

              Memory Layer

          PostgreSQL + Qdrant


       --------------------------------

              Tool Layer

             MCP Servers


       --------------------------------

          Observability Layer

       Langfuse + OpenTelemetry


       --------------------------------

        Experiment Tracking

                MLflow
```

This structure provides a scalable foundation for building a complete Investment Research Analyst Agent and learning advanced Agentic AI engineering patterns.


