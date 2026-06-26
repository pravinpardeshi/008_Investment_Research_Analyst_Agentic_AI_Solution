import asyncio
import json
import logging
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import TextContent, Tool

from api.tools.qdrant_search import QdrantSearch

logger = logging.getLogger(__name__)

server = Server("investment-research")

_FINANCIAL_DATA: dict[str, dict[str, Any]] = {}
_PEER_MAP: dict[str, list[str]] = {}


def _load_company_data():
    global _FINANCIAL_DATA, _PEER_MAP
    try:
        search = QdrantSearch()
        results = search.client.scroll(
            collection_name="investment_docs",
            limit=1000,
            with_payload=True,
        )
        companies: dict[str, dict[str, Any]] = {}
        for point in results[0]:
            payload = point.payload or {}
            filename = payload.get("filename", "")
            company = payload.get("company", "")
            text = payload.get("text", "")
            if company and company not in companies:
                companies[company] = {"name": company, "filenames": set(), "snippets": []}
            if company:
                companies[company]["filenames"].add(filename)
            if company and text and len(companies[company]["snippets"]) < 5:
                companies[company]["snippets"].append(text[:300])

        for name, data in companies.items():
            data["filenames"] = list(data["filenames"])
            _FINANCIAL_DATA[name.lower()] = data

        _PEER_MAP = {
            "rbc": ["td", "bmo", "scotiabank", "cibc", "national bank"],
            "td": ["rbc", "bmo", "scotiabank", "cibc"],
            "bmo": ["rbc", "td", "scotiabank", "cibc"],
            "jpmorgan": ["goldman sachs", "bank of america", "citigroup", "morgan stanley"],
            "goldman sachs": ["jpmorgan", "morgan stanley", "bank of america"],
            "microsoft": ["apple", "google", "amazon", "meta"],
            "apple": ["microsoft", "google", "amazon", "meta"],
            "google": ["microsoft", "apple", "amazon", "meta"],
            "amazon": ["microsoft", "apple", "google", "walmart"],
        }
        logger.info("Loaded %d companies from Qdrant for MCP tools", len(companies))
    except Exception as e:
        logger.warning("Could not load company data for MCP: %s", e)


def _ticker_hint(company: str) -> str:
    tickers = {
        "rbc": "RY", "td": "TD", "bmo": "BMO", "scotiabank": "BNS",
        "cibc": "CM", "national bank": "NA", "jpmorgan": "JPM",
        "goldman sachs": "GS", "morgan stanley": "MS",
        "bank of america": "BAC", "citigroup": "C",
        "microsoft": "MSFT", "apple": "AAPL", "google": "GOOGL",
        "amazon": "AMZN", "meta": "META", "walmart": "WMT",
        "nvidia": "NVDA", "tesla": "TSLA",
    }
    return tickers.get(company.lower(), company.upper()[:4])


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_stock_ticker",
            description="Look up the stock ticker symbol for a company name",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "Full company name (e.g. 'Royal Bank of Canada')"},
                },
                "required": ["company_name"],
            },
        ),
        Tool(
            name="get_company_info",
            description="Get company overview, description, and available documents",
            inputSchema={
                "type": "object",
                "properties": {
                    "company": {"type": "string", "description": "Company name or ticker"},
                },
                "required": ["company"],
            },
        ),
        Tool(
            name="get_peers",
            description="Get peer/competitor companies for a given company",
            inputSchema={
                "type": "object",
                "properties": {
                    "company": {"type": "string", "description": "Company name or ticker"},
                },
                "required": ["company"],
            },
        ),
        Tool(
            name="search_documents",
            description="Search uploaded investment documents for relevant information",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {"type": "integer", "description": "Number of results (default 5)"},
                },
                "required": ["query"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "get_stock_ticker":
            company = arguments.get("company_name", "")
            key = company.lower().strip()
            ticker = _ticker_hint(key)
            info = _FINANCIAL_DATA.get(key, {})
            result = {"ticker": ticker, "company": company, "has_documents": bool(info)}
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_company_info":
            company = arguments.get("company", "").lower().strip()
            info = _FINANCIAL_DATA.get(company)
            if info:
                result = {
                    "name": info["name"],
                    "documents": info["filenames"],
                    "ticker": _ticker_hint(company),
                    "snippets": info["snippets"],
                }
            else:
                result = {
                    "name": company.title(),
                    "ticker": _ticker_hint(company),
                    "documents": [],
                    "note": "No uploaded documents found for this company. Upload annual reports first.",
                }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_peers":
            company = arguments.get("company", "").lower().strip()
            peers = _PEER_MAP.get(company, [])
            if not peers:
                return [TextContent(type="text", text=json.dumps({
                    "company": company,
                    "peers": [],
                    "note": "No peer data available. The peer map covers major banks and tech companies.",
                }, indent=2))]
            peer_info = []
            for p in peers:
                info = _FINANCIAL_DATA.get(p, {})
                peer_info.append({
                    "name": p.title(),
                    "ticker": _ticker_hint(p),
                    "has_documents": bool(info),
                })
            return [TextContent(type="text", text=json.dumps({
                "company": company,
                "peers": peer_info,
            }, indent=2))]

        elif name == "search_documents":
            query = arguments.get("query", "")
            top_k = min(int(arguments.get("top_k", 5)), 20)
            try:
                from api.utils.llm import get_embedding
                vector = get_embedding(query)
                search = QdrantSearch()
                results = search.search(vector, top_k=top_k)
                docs = [
                    {
                        "text": r["text"][:500],
                        "filename": r.get("filename", ""),
                        "company": r.get("company", ""),
                        "score": round(r.get("score", 0), 3),
                    }
                    for r in results
                ]
                return [TextContent(type="text", text=json.dumps({"results": docs}, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e), "results": []}))]

        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    except Exception as e:
        logger.error("MCP tool %s failed: %s", name, e)
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def serve(host: str = "127.0.0.1", port: int = 8100):
    from mcp.server.stdio import stdio_server

    _load_company_data()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="investment-research",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def run_server(host: str = "127.0.0.1", port: int = 8100):
    asyncio.run(serve(host, port))


if __name__ == "__main__":
    run_server()
