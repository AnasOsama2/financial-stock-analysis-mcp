# Stock Analysis MCP Server 📈

A defensible, filing-based **Model Context Protocol (MCP)** server for financial stock analysis of U.S. public companies powered by **SEC EDGAR REST APIs** and XBRL facts datasets.

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![MCP](https://img.shields.io/badge/MCP-FastMCP-green.svg)
![License](https://img.shields.io/badge/License-MIT-brightgreen.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)

---

## 🌟 Features

- **Zero API Keys Required**: Queries the official, free, and public SEC EDGAR REST APIs directly.
- **Deterministic Metric Engine**: Calculates Net Income, Free Cash Flow (`Operating Cash Flow - CapEx`), Operating Margin, Net Margin, EBITDA Proxy, and Stock-Based Compensation intensity with complete calculation traces.
- **Red-Flag Diagnostic Engine**: Automatically flags cash conversion divergence, margin compression, receivables growing faster than revenue, and SBC share dilution.
- **SEC Audit Evidence**: Direct links to SEC filings, 10-K/10-Q documents, and accession numbers.
- **FastMCP Compliant**: Built strictly following MCP standards (single-line docstrings, stdio transport, formatted output).

---

## 🛠️ Exposed MCP Tools

| Tool | Function | Key Arguments |
|---|---|---|
| `resolve_company` | Resolve ticker, CIK, or name to SEC metadata | `query` (e.g. `"AAPL"`) |
| `get_filings` | Retrieve recent filings (10-K, 10-Q, 8-K) with direct URLs | `ticker_or_cik`, `form_type`, `limit` |
| `get_statement_facts` | Pull raw and normalized XBRL income statement, balance sheet, or cash flow facts | `ticker_or_cik`, `statement_type` |
| `calculate_profitability` | Compute Net Income, FCF, Margins, EBITDA Proxy, SBC Intensity | `ticker_or_cik`, `period_type` |
| `compare_periods` | Multi-period aligned comparisons and YoY growth rates | `ticker_or_cik`, `metric`, `num_periods` |
| `detect_red_flags` | Run automated red-flag diagnostics | `ticker_or_cik` |
| `get_evidence` | Return SEC accession numbers, XBRL tags, and source URLs | `ticker_or_cik`, `fact_tag` |

---

## 🚀 Quick Start (Docker)

### 1. Build the Container Image

```bash
docker build -t stock-analysis-mcp-server:latest .
```

### 2. Add to your MCP Client Configuration

In your `claude_desktop_config.json` or `mcp_config.json`:

```json
{
  "mcpServers": {
    "stock_analysis": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "stock-analysis-mcp-server:latest"
      ]
    }
  }
}
```

---

## 💻 Local Development (Without Docker)

### Installation

```bash
pip install -r requirements.txt
```

### Run Server

```bash
python stock_analysis_server.py
```

---

## 📄 License

This project is licensed under the MIT License.
