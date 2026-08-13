================================================================================
STOCK ANALYSIS MCP SERVER - DOCUMENTATION & SETUP GUIDE
================================================================================

OVERVIEW:
The Stock Analysis MCP (Model Context Protocol) Server provides a filing-based,
defensible financial stock analysis engine for U.S. public companies powered by
SEC EDGAR APIs and XBRL company facts datasets.

SERVER METADATA:
- Server Name: stock_analysis
- Container Image: stock-analysis-mcp-server:latest
- Transport: stdio
- Primary Data Source: SEC EDGAR (Zero-cost, no API key required)

================================================================================
EXPOSED MCP TOOLS
================================================================================

1. resolve_company
   - Description: Resolves ticker, numeric CIK, or company name to SEC CIK, exchange,
     title, SIC industry code, and SEC metadata.
   - Parameters:
     * query (str, default: ""): Ticker symbol (e.g. "AAPL"), CIK, or company name.

2. get_filings
   - Description: Returns filing history, accession numbers, filing types, dates, and
     direct SEC EDGAR document links.
   - Parameters:
     * ticker_or_cik (str, default: ""): Ticker symbol or CIK.
     * form_type (str, default: ""): Optional filter (e.g. "10-K", "10-Q", "8-K").
     * limit (str, default: "10"): Max number of filings to display.

3. get_statement_facts
   - Description: Returns raw and normalized XBRL income statement, balance sheet, or
     cash flow statement facts.
   - Parameters:
     * ticker_or_cik (str, default: ""): Ticker symbol or CIK.
     * statement_type (str, default: "income"): Financial statement ("income", "balance", "cash").

4. calculate_profitability
   - Description: Computes deterministic profitability metrics (Net Income, FCF, Margins,
     EBITDA Proxy, SBC Intensity) with full calculation traces.
   - Parameters:
     * ticker_or_cik (str, default: ""): Ticker symbol or CIK.
     * period_type (str, default: "CY"): Period type ("CY" or "FY").

5. compare_periods
   - Description: Produces multi-period aligned financial comparisons with YoY growth rates.
   - Parameters:
     * ticker_or_cik (str, default: ""): Ticker symbol or CIK.
     * metric (str, default: "Revenues"): US-GAAP metric concept tag.
     * num_periods (str, default: "4"): Number of periods to compare.

6. detect_red_flags
   - Description: Runs automated red-flag diagnostics for cash conversion divergence,
     margin compression, receivables lag, and dilution.
   - Parameters:
     * ticker_or_cik (str, default: ""): Ticker symbol or CIK.

7. get_evidence
   - Description: Returns SEC accession numbers, XBRL tags, filing dates, and direct links
     supporting audit evidence.
   - Parameters:
     * ticker_or_cik (str, default: ""): Ticker symbol or CIK.
     * fact_tag (str, default: ""): Specific US-GAAP XBRL tag.

================================================================================
DOCKER & CLAUDE DESKTOP INSTALLATION INSTRUCTIONS
================================================================================

Step 1: Build the Docker Image
------------------------------
Run from the server project directory:
  docker build -t stock-analysis-mcp-server:latest .

Step 2: Custom Catalog Entry
----------------------------
Add an entry to your Docker MCP catalog (~/.docker/mcp/catalogs/custom.yaml):

version: 2
name: custom
displayName: Custom MCP Servers
registry:
  stock_analysis:
    description: "Filing-based financial stock analysis MCP server using SEC EDGAR data."
    title: "Stock Analysis MCP Server"
    type: server
    dateAdded: "2025-01-01T00:00:00Z"
    image: stock-analysis-mcp-server:latest
    ref: ""
    readme: ""
    toolsUrl: ""
    source: ""
    upstream: ""
    icon: ""
    tools:
      - name: resolve_company
      - name: get_filings
      - name: get_statement_facts
      - name: calculate_profitability
      - name: compare_periods
      - name: detect_red_flags
      - name: get_evidence
    metadata:
      category: productivity
      tags:
        - finance
        - sec-edgar
        - stocks
      license: MIT
      owner: local

Step 3: Update Registry
-----------------------
Add to ~/.docker/mcp/registry.yaml under the `registry:` key:

registry:
  stock_analysis:
    ref: ""

Step 4: Configure Claude Desktop
--------------------------------
In %APPDATA%\Claude\claude_desktop_config.json (Windows) or
~/Library/Application Support/Claude/claude_desktop_config.json (macOS), add custom.yaml to args:

{
  "mcpServers": {
    "mcp-toolkit-gateway": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v", "/var/run/docker.sock:/var/run/docker.sock",
        "-v", "C:\\Users\\YOUR_USER\\.docker\\mcp:/mcp",
        "docker/mcp-gateway",
        "--catalog=/mcp/catalogs/docker-mcp.yaml",
        "--catalog=/mcp/catalogs/custom.yaml",
        "--config=/mcp/config.yaml",
        "--registry=/mcp/registry.yaml",
        "--tools-config=/mcp/tools.yaml",
        "--transport=stdio"
      ]
    }
  }
}

================================================================================
