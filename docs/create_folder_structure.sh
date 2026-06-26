#!/bin/bash

PROJECT_NAME="investment-research-agent"

echo "Creating project structure: $PROJECT_NAME"

mkdir -p "$PROJECT_NAME"

cd "$PROJECT_NAME" || exit 1

# Frontend
mkdir -p frontend/{static/{css,js,images},templates,components}

# Backend API
mkdir -p api/{agents,workflows,memory,tools,evaluation,models}

# MCP Servers
mkdir -p mcp/{filing_server,news_server,metrics_server,report_server}

# Data directories
mkdir -p data/{annual_reports,quarterly_reports,earnings_calls,presentations}

# Evaluation benchmarks
mkdir -p benchmarks/{evaluation_results}

# Experiment tracking
mkdir -p mlflow
mkdir -p langfuse

# Documentation
mkdir -p docs

# Configuration
mkdir -p config

# Tests
mkdir -p tests/{agents,workflows,tools}

# Logs
mkdir -p logs

# Create initial placeholder files

touch README.md
touch .gitignore
touch docker-compose.yml
touch requirements.txt
touch pyproject.toml

# API placeholders
touch api/main.py
touch api/__init__.py

# Agent placeholders
touch api/agents/{planner,researcher,risk_analyst,writer,reviewer}.py

# Workflow placeholders
touch api/workflows/research_workflow.py
touch api/workflows/review_workflow.py

# Memory placeholders
touch api/memory/postgres_memory.py
touch api/memory/vector_memory.py
touch api/memory/reflections.py

# Tool placeholders
touch api/tools/{filing_search,document_loader,qdrant_search,calculator}.py

# Evaluation placeholders
touch api/evaluation/{benchmark_runner,metrics,judge}.py

# Model placeholders
touch api/models/{company,report,finding,research_run}.py

# MCP placeholders
touch mcp/filing_server/server.py
touch mcp/news_server/server.py
touch mcp/metrics_server/server.py
touch mcp/report_server/server.py

# Documentation placeholders
touch docs/{architecture,agents,workflows,evaluation,roadmap}.md

# Benchmark files
touch benchmarks/{tasks.json,expected_outputs.json}

echo ""
echo "Project structure created successfully!"
echo ""
echo "Location:"
pwd
echo ""
echo "Directory tree:"
tree -L 3

