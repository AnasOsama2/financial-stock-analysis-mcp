================================================================================
MULTI-MARKET STOCK ANALYSIS MCP SERVER - DOCUMENTATION & SETUP GUIDE
================================================================================

OVERVIEW:
The Multi-Market Stock Analysis MCP Server provides a filing-based, defensible
financial stock analysis engine supporting:
- 🇺🇸 US Market (SEC EDGAR)
- 🇪🇬 EGX Market (Egyptian Exchange / FRA)
- 🇦🇪 DFM Market (Dubai Financial Market)
- 🇦🇪 ADX Market (Abu Dhabi Securities Exchange)

ADAPTERS & RESPONSIBILITIES:
- twelve_data_adapter: Symbol lookup, market quotes, exchange metadata (EGX, DFM, ADX, US).
- egx_disclosures_adapter: EGX/FRA announcements, financial releases (e.g. COMI, HRHO, ETEL).
- dfm_disclosures_adapter: DFM listed-company disclosures and statements (e.g. EMAAR, DIB, DEWA).
- adx_reports_adapter: ADX company financial reports and releases (e.g. EAND, FAB, IHC).
- regional_analysis_engine: Multi-currency (USD, EGP, AED) ratio calculations and red-flag engine.

================================================================================
EXPOSED MCP TOOLS
================================================================================

1. resolve_company
   - Description: Resolves company symbol, CIK, or name across US (SEC), EGX (Egypt), DFM (Dubai), and ADX (Abu Dhabi).
   - Parameters: query (str), market (str)

2. list_disclosures
   - Description: Lists recent disclosures, filing announcements, and regulatory releases across markets.
   - Parameters: ticker_or_symbol (str), market (str), limit (str)

3. get_financial_report
   - Description: Returns financial report metadata, period summary, and direct document source links across markets.
   - Parameters: ticker_or_symbol (str), market (str), period (str)

4. extract_statement
   - Description: Extracts structured financial statement facts for income statement, balance sheet, or cash flow across markets.
   - Parameters: ticker_or_symbol (str), statement_type (str), market (str)

5. calculate_profitability
   - Description: Computes Net Income, Free Cash Flow (FCF), Margins, EBITDA Proxy, and SBC Intensity across markets.
   - Parameters: ticker_or_symbol (str), market (str), period_type (str)

6. compare_periods
   - Description: Produces multi-period financial comparisons and YoY growth rates across markets.
   - Parameters: ticker_or_symbol (str), metric (str), market (str), num_periods (str)

7. detect_red_flags
   - Description: Applies financial red-flag diagnostic tests for cash conversion divergence, margin compression, and receivables lag.
   - Parameters: ticker_or_symbol (str), market (str)

8. get_evidence
   - Description: Returns audit evidence, accession numbers/source IDs, filing URLs, and calculation traces across markets.
   - Parameters: ticker_or_symbol (str), fact_tag (str), market (str)

================================================================================
DOCKER INSTALLATION & SETUP
================================================================================

Build the Docker Image:
  docker build -t stock-analysis-mcp-server:latest .

Configuration Entry (mcp_config.json):
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
================================================================================
