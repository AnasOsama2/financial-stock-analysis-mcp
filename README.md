# Multi-Market Stock Analysis MCP Server 📈🌍

A **Model Context Protocol (MCP)** server for financial stock analysis. US data is live from **SEC EDGAR**. Egypt (EGX), Dubai (DFM) and Abu Dhabi (ADX) currently return **demo data** only.

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![MCP](https://img.shields.io/badge/MCP-FastMCP-green.svg)
![Markets](https://img.shields.io/badge/Markets-US%20%7C%20EGX%20%7C%20DFM%20%7C%20ADX-orange.svg)
![License](https://img.shields.io/badge/License-MIT-brightgreen.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)

---

## 🏛️ Data Sources and Status

| Market | Status | Source |
|---|---|---|
| US | Live | SEC EDGAR (company tickers and XBRL company facts) |
| Egypt (EGX): `COMI`, `HRHO`, `ETEL` | **Demo data** | Hardcoded sample figures in `stock_analysis_server.py`. Not from real filings. |
| Dubai (DFM): `EMAAR`, `DIB`, `DEWA` | **Demo data** | Same as above |
| Abu Dhabi (ADX): `EAND`, `FAB`, `IHC` | **Demo data** | Same as above |

Regional outputs start with a DEMO DATA notice and use a placeholder instead of a filing ID. Symbol search can optionally use Twelve Data when `TWELVE_DATA_API_KEY` is set. Connecting real EGX/DFM/ADX disclosure feeds is future work.

---

## 🛠️ Unified MCP Tools

| Tool | Description | Key Arguments |
|---|---|---|
| `resolve_company` | Resolve symbol, CIK, or name across US, EGX, DFM, and ADX | `query`, `market` |
| `list_disclosures` | List recent disclosures, filing announcements, and regulatory releases | `ticker_or_symbol`, `market`, `limit` |
| `get_financial_report` | Return financial report metadata, summary, and direct document source links | `ticker_or_symbol`, `market`, `period` |
| `extract_statement` | Extract structured financial statement facts (Income, Balance, Cash Flow) | `ticker_or_symbol`, `statement_type`, `market` |
| `calculate_profitability` | Compute Net Income, Free Cash Flow (`Operating Cash Flow - CapEx`), Margins, EBITDA Proxy, SBC | `ticker_or_symbol`, `market`, `period_type` |
| `compare_periods` | Multi-period financial comparisons and YoY growth rates | `ticker_or_symbol`, `metric`, `market`, `num_periods` |
| `detect_red_flags` | Apply financial red-flag diagnostic tests (cash conversion, margin compression, receivables lag) | `ticker_or_symbol`, `market` |
| `get_evidence` | Return audit evidence, accession numbers/source IDs, filing URLs, and calculation traces | `ticker_or_symbol`, `fact_tag`, `market` |

---

## 🚀 Quick Start (Docker)

```bash
# Build Docker image
docker build -t stock-analysis-mcp-server:latest .

# Run container interactively
docker run -i --rm stock-analysis-mcp-server:latest
```

---

## 💻 Configuration (`mcp_config.json`)

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

## 📄 License

This project is licensed under the MIT License.
