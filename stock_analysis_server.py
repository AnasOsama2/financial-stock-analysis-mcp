#!/usr/bin/env python3
"""
Stock Analysis MCP Server - SEC EDGAR Filing-Based Financial Analysis
"""

import asyncio
import os
import sys
import logging
import time
from datetime import datetime, timezone
import httpx
from mcp.server.fastmcp import FastMCP

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("stock_analysis-server")

# Initialize MCP server - NO PROMPT PARAMETER!
mcp = FastMCP("stock_analysis")

# SEC EDGAR Configuration
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "StockAnalysisMCP/1.0 (financial-mcp@example.com)")
SEC_HEADERS = {"User-Agent": SEC_USER_AGENT}
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"

# Global memory caches
_ticker_to_cik = {}
_cik_to_meta = {}
_cache_facts = {}
_cache_submissions = {}
_last_request_time = 0.0

async def _rate_limited_get(url: str) -> dict:
    """Fetch JSON from SEC EDGAR API with rate limiting and error handling."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < 0.12:
        await asyncio.sleep(0.12 - elapsed)
    _last_request_time = time.time()
    
    async with httpx.AsyncClient(timeout=15.0, headers=SEC_HEADERS) as client:
        response = await client.get(url)
        if response.status_code == 404:
            raise ValueError(f"Resource not found (404) at URL: {url}")
        response.raise_for_status()
        return response.json()

async def _ensure_ticker_map():
    """Load SEC ticker-to-CIK mapping if not already cached."""
    global _ticker_to_cik, _cik_to_meta
    if _ticker_to_cik:
        return
    try:
        data = await _rate_limited_get(TICKER_MAP_URL)
        for item in data.values():
            ticker = str(item.get("ticker", "")).upper()
            cik = str(item.get("cik_str", "")).zfill(10)
            title = item.get("title", "")
            if ticker:
                _ticker_to_cik[ticker] = cik
                _cik_to_meta[cik] = {"ticker": ticker, "title": title, "cik": cik}
                raw_cik = str(item.get("cik_str", ""))
                _ticker_to_cik[raw_cik] = cik
                _ticker_to_cik[cik] = cik
    except Exception as e:
        logger.error(f"Failed to load SEC ticker mapping: {e}")

async def _resolve_cik(query: str) -> dict:
    """Resolve a ticker, CIK, or company name query to SEC metadata dict."""
    await _ensure_ticker_map()
    clean_query = query.strip().upper()
    
    if clean_query in _ticker_to_cik:
        cik = _ticker_to_cik[clean_query]
        return _cik_to_meta.get(cik, {"cik": cik, "ticker": clean_query, "title": clean_query})
    
    if clean_query.isdigit():
        cik = clean_query.zfill(10)
        if cik in _cik_to_meta:
            return _cik_to_meta[cik]
        return {"cik": cik, "ticker": "N/A", "title": f"CIK {cik}"}
        
    for cik, meta in _cik_to_meta.items():
        if clean_query in meta["title"].upper():
            return meta
            
    raise ValueError(f"Could not resolve company for query: '{query}'")

async def _get_company_submissions(cik: str) -> dict:
    """Fetch company submission history from SEC EDGAR."""
    if cik in _cache_submissions:
        return _cache_submissions[cik]
    url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    data = await _rate_limited_get(url)
    _cache_submissions[cik] = data
    return data

async def _get_company_facts(cik: str) -> dict:
    """Fetch all XBRL company facts from SEC EDGAR."""
    if cik in _cache_facts:
        return _cache_facts[cik]
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json"
    data = await _rate_limited_get(url)
    _cache_facts[cik] = data
    return data

def _find_concept_units(facts_data: dict, concept_names: list) -> tuple:
    """Find XBRL fact entries for the first matching concept in US-GAAP taxonomy."""
    gaap = facts_data.get("facts", {}).get("us-gaap", {})
    for concept in concept_names:
        if concept in gaap:
            units_dict = gaap[concept].get("units", {})
            for unit_key, fact_list in units_dict.items():
                if fact_list:
                    return concept, unit_key, fact_list
    return "", "", []

def _filter_facts(fact_list: list, form_types=None, fp_filter=None) -> list:
    """Filter fact entries by form type and fiscal period."""
    results = []
    for f in fact_list:
        if form_types and f.get("form") not in form_types:
            continue
        if fp_filter and f.get("fp") != fp_filter:
            continue
        results.append(f)
    return results

def _format_currency(val) -> str:
    """Format numbers cleanly with currency symbols and scaling."""
    if val is None or val == "":
        return "N/A"
    try:
        num = float(val)
        abs_num = abs(num)
        sign = "-" if num < 0 else ""
        if abs_num >= 1e9:
            return f"{sign}${abs_num / 1e9:,.2f}B"
        elif abs_num >= 1e6:
            return f"{sign}${abs_num / 1e6:,.2f}M"
        elif abs_num >= 1e3:
            return f"{sign}${abs_num / 1e3:,.2f}K"
        else:
            return f"{sign}${abs_num:,.2f}"
    except Exception:
        return str(val)

def _format_pct(val) -> str:
    """Format decimal or percentage values."""
    if val is None or val == "":
        return "N/A"
    try:
        return f"{float(val) * 100:.2f}%"
    except Exception:
        return str(val)

# === MCP TOOLS ===

@mcp.tool()
async def resolve_company(query: str = "") -> str:
    """Resolve company ticker or name to CIK, exchange, title, and SEC metadata."""
    logger.info(f"Executing resolve_company with query='{query}'")
    if not query.strip():
        return "❌ Error: Query parameter is required (e.g. ticker 'AAPL' or name 'Microsoft')."
    
    try:
        meta = await _resolve_cik(query)
        cik = meta["cik"]
        submissions = await _get_company_submissions(cik)
        
        tickers = ", ".join(submissions.get("tickers", [meta.get("ticker", "N/A")]))
        exchanges = ", ".join(submissions.get("exchanges", []))
        sic_desc = submissions.get("sicDescription", "N/A")
        fiscal_end = submissions.get("fiscalYearEnd", "N/A")
        entity_name = submissions.get("name", meta.get("title", "N/A"))
        
        output = [
            f"✅ **Resolved Company Metadata for '{query.strip()}'**",
            "",
            f"| Attribute | Details |",
            f"|---|---|",
            f"| **Entity Name** | {entity_name} |",
            f"| **Primary Ticker** | {meta.get('ticker', 'N/A')} |",
            f"| **All Tickers** | {tickers or 'N/A'} |",
            f"| **CIK** | `{cik}` |",
            f"| **Exchanges** | {exchanges or 'N/A'} |",
            f"| **SIC Industry** | {sic_desc} |",
            f"| **Fiscal Year End** | {fiscal_end} |",
            f"| **SEC EDGAR URL** | https://www.sec.gov/edgar/browse/?CIK={cik} |"
        ]
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error in resolve_company: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def get_filings(ticker_or_cik: str = "", form_type: str = "", limit: str = "10") -> str:
    """Return filing history, accession numbers, filing types, dates, and source URLs for a company."""
    logger.info(f"Executing get_filings for ticker_or_cik='{ticker_or_cik}', form_type='{form_type}', limit='{limit}'")
    if not ticker_or_cik.strip():
        return "❌ Error: ticker_or_cik parameter is required."
    
    try:
        lim = int(limit) if limit.strip().isdigit() else 10
        meta = await _resolve_cik(ticker_or_cik)
        cik = meta["cik"]
        sub = await _get_company_submissions(cik)
        
        recent = sub.get("filings", {}).get("recent", {})
        if not recent or "form" not in recent:
            return f"⚠️ No recent filings found for {meta.get('title', cik)}"
            
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        primary_docs = recent.get("primaryDocument", [])
        descriptions = recent.get("primaryDocDescription", [])
        
        target_form = form_type.strip().upper()
        
        rows = []
        for i in range(len(forms)):
            if len(rows) >= lim:
                break
            current_form = forms[i]
            if target_form and target_form not in current_form.upper():
                continue
                
            acc_raw = accessions[i]
            acc_no_dash = acc_raw.replace("-", "")
            doc = primary_docs[i]
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dash}/{doc}"
            desc = descriptions[i] if i < len(descriptions) else ""
            rep_date = report_dates[i] if i < len(report_dates) else filing_dates[i]
            
            rows.append(f"| {current_form} | {filing_dates[i]} | {rep_date} | `{acc_raw}` | [{doc}]({doc_url}) | {desc} |")
            
        header = [
            f"📁 **SEC Filings History for {meta.get('title', ticker_or_cik)} (CIK: {cik})**",
            f"Filtered by Form: `{target_form or 'ALL'}` | Displaying Top {len(rows)} Results",
            "",
            "| Form | Filing Date | Period End | Accession Number | Document Link | Description |",
            "|---|---|---|---|---|---|"
        ]
        
        if not rows:
            return f"⚠️ No filings matching form type '{form_type}' found for {meta.get('title', ticker_or_cik)}."
            
        return "\n".join(header + rows)
    except Exception as e:
        logger.error(f"Error in get_filings: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def get_statement_facts(ticker_or_cik: str = "", statement_type: str = "income") -> str:
    """Return raw and normalized XBRL income statement, balance sheet, or cash flow facts from SEC filings."""
    logger.info(f"Executing get_statement_facts for ticker_or_cik='{ticker_or_cik}', statement_type='{statement_type}'")
    if not ticker_or_cik.strip():
        return "❌ Error: ticker_or_cik parameter is required."
        
    try:
        meta = await _resolve_cik(ticker_or_cik)
        cik = meta["cik"]
        facts_data = await _get_company_facts(cik)
        
        st = statement_type.strip().lower()
        if st in ["income", "income_statement", "pnl"]:
            concepts = ["Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax", "OperatingIncomeLoss", "NetIncomeLoss", "GrossProfit"]
            st_title = "Income Statement"
        elif st in ["balance", "balance_sheet", "bs"]:
            concepts = ["Assets", "Liabilities", "StockholdersEquity", "CashAndCashEquivalentsAtCarryingValue", "AccountsReceivableNetCurrent", "LongTermDebtNoncurrent"]
            st_title = "Balance Sheet"
        elif st in ["cash", "cash_flow", "cf"]:
            concepts = ["NetCashProvidedByUsedInOperatingActivities", "PaymentsToAcquirePropertyPlantAndEquipment", "ShareBasedCompensation", "DepreciationDepletionAndAmortization"]
            st_title = "Cash Flow Statement"
        else:
            return "❌ Error: Invalid statement_type. Use 'income', 'balance', or 'cash'."
            
        output_rows = []
        for concept in concepts:
            c_name, unit_key, fact_list = _find_concept_units(facts_data, [concept])
            if not fact_list:
                continue
            fy_facts = _filter_facts(fact_list, form_types=["10-K"], fp_filter="FY")
            fy_facts.sort(key=lambda x: x.get("fy", 0), reverse=True)
            
            top_3 = fy_facts[:3]
            for f in top_3:
                fy = f.get("fy", "N/A")
                val_fmt = _format_currency(f.get("val"))
                accn = f.get("accn", "N/A")
                output_rows.append(f"| {st_title} | `{concept}` | FY{fy} | {val_fmt} | `{unit_key}` | `{accn}` |")
                
        if not output_rows:
            return f"⚠️ No XBRL financial statement facts found for {meta.get('title', ticker_or_cik)} under {st_title}."
            
        header = [
            f"📊 **XBRL {st_title} Facts for {meta.get('title', ticker_or_cik)} (CIK: {cik})**",
            "",
            "| Statement | XBRL Tag | Fiscal Year | Formatted Value | Unit | Accession No. |",
            "|---|---|---|---|---|---|"
        ]
        return "\n".join(header + output_rows)
    except Exception as e:
        logger.error(f"Error in get_statement_facts: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def calculate_profitability(ticker_or_cik: str = "", period_type: str = "CY") -> str:
    """Calculate profitability metrics including Net Income, Free Cash Flow, margins, EBITDA proxy, and SBC intensity."""
    logger.info(f"Executing calculate_profitability for ticker_or_cik='{ticker_or_cik}'")
    if not ticker_or_cik.strip():
        return "❌ Error: ticker_or_cik parameter is required."
        
    try:
        meta = await _resolve_cik(ticker_or_cik)
        cik = meta["cik"]
        facts = await _get_company_facts(cik)
        
        _, _, rev_list = _find_concept_units(facts, ["Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax"])
        _, _, net_inc_list = _find_concept_units(facts, ["NetIncomeLoss", "ProfitLoss"])
        _, _, op_inc_list = _find_concept_units(facts, ["OperatingIncomeLoss"])
        _, _, op_cf_list = _find_concept_units(facts, ["NetCashProvidedByUsedInOperatingActivities"])
        _, _, capex_list = _find_concept_units(facts, ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"])
        _, _, da_list = _find_concept_units(facts, ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "Depreciation"])
        _, _, sbc_list = _find_concept_units(facts, ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"])
        
        rev_fy = _filter_facts(rev_list, form_types=["10-K"], fp_filter="FY")
        rev_fy.sort(key=lambda x: x.get("fy", 0), reverse=True)
        if not rev_fy:
            return f"⚠️ Insufficient 10-K data to calculate profitability for {meta.get('title', ticker_or_cik)}."
            
        latest_rev_fact = rev_fy[0]
        latest_fy = latest_rev_fact.get("fy")
        revenue = float(latest_rev_fact.get("val", 0))
        
        def get_val_for_fy(fact_list, target_fy):
            fy_filtered = _filter_facts(fact_list, form_types=["10-K"], fp_filter="FY")
            for f in fy_filtered:
                if f.get("fy") == target_fy:
                    return float(f.get("val", 0)), f.get("accn", "N/A")
            return 0.0, "N/A"
            
        net_inc, net_accn = get_val_for_fy(net_inc_list, latest_fy)
        op_inc, op_accn = get_val_for_fy(op_inc_list, latest_fy)
        op_cf, cf_accn = get_val_for_fy(op_cf_list, latest_fy)
        capex, capex_accn = get_val_for_fy(capex_list, latest_fy)
        da, da_accn = get_val_for_fy(da_list, latest_fy)
        sbc, sbc_accn = get_val_for_fy(sbc_list, latest_fy)
        
        fcf = op_cf - capex
        op_margin = (op_inc / revenue) if revenue else 0.0
        net_margin = (net_inc / revenue) if revenue else 0.0
        ebitda_proxy = op_inc + da
        sbc_intensity = (sbc / revenue) if revenue else 0.0
        sbc_of_opcf = (sbc / op_cf) if op_cf else 0.0
        
        output = [
            f"⚡ **Deterministic Profitability Engine - {meta.get('title', ticker_or_cik)} (FY{latest_fy})**",
            f"Filing Source Accession: `{latest_rev_fact.get('accn', 'N/A')}`",
            "",
            "| Metric | Calculated Value | Formula & Method | Source Accession |",
            "|---|---|---|---|",
            f"| **Revenue** | {_format_currency(revenue)} | Reported Consolidated Revenue | `{latest_rev_fact.get('accn', 'N/A')}` |",
            f"| **Net Income** | {_format_currency(net_inc)} | Reported Net Income | `{net_accn}` |",
            f"| **Operating Income** | {_format_currency(op_inc)} | Reported Operating Income | `{op_accn}` |",
            f"| **Operating Cash Flow** | {_format_currency(op_cf)} | Cash from Operating Activities | `{cf_accn}` |",
            f"| **CapEx** | {_format_currency(capex)} | Property, Plant & Equipment Purchases | `{capex_accn}` |",
            f"| **Free Cash Flow (FCF)** | **{_format_currency(fcf)}** | `Operating Cash Flow − CapEx` | Derived |",
            f"| **Operating Margin** | **{_format_pct(op_margin)}** | `Operating Income ÷ Revenue` | Derived |",
            f"| **Net Margin** | **{_format_pct(net_margin)}** | `Net Income ÷ Revenue` | Derived |",
            f"| **EBITDA Proxy** | {_format_currency(ebitda_proxy)} | `Operating Income + D&A ({_format_currency(da)})` | Derived |",
            f"| **SBC Intensity (Revenue)** | {_format_pct(sbc_intensity)} | `Stock-Based Comp ({_format_currency(sbc)}) ÷ Revenue` | Derived |",
            f"| **SBC % of Operating Cash Flow** | {_format_pct(sbc_of_opcf)} | `Stock-Based Comp ÷ Operating Cash Flow` | Derived |"
        ]
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error in calculate_profitability: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def compare_periods(ticker_or_cik: str = "", metric: str = "Revenues", num_periods: str = "4") -> str:
    """Produce annual or quarterly financial period comparisons with aligned XBRL metadata."""
    logger.info(f"Executing compare_periods for ticker_or_cik='{ticker_or_cik}', metric='{metric}', num_periods='{num_periods}'")
    if not ticker_or_cik.strip():
        return "❌ Error: ticker_or_cik parameter is required."
        
    try:
        n = int(num_periods) if num_periods.strip().isdigit() else 4
        meta = await _resolve_cik(ticker_or_cik)
        cik = meta["cik"]
        facts = await _get_company_facts(cik)
        
        target_metric = metric.strip()
        concept, unit_key, fact_list = _find_concept_units(facts, [target_metric, "Revenues", "SalesRevenueNet", "NetIncomeLoss", "OperatingIncomeLoss"])
        
        if not fact_list:
            return f"⚠️ Metric concept '{target_metric}' not found in US-GAAP facts for {meta.get('title', ticker_or_cik)}."
            
        fy_facts = _filter_facts(fact_list, form_types=["10-K"], fp_filter="FY")
        fy_facts.sort(key=lambda x: x.get("fy", 0), reverse=True)
        selected_facts = fy_facts[:n]
        
        rows = []
        for i, f in enumerate(selected_facts):
            fy = f.get("fy", "N/A")
            val = float(f.get("val", 0))
            val_str = _format_currency(val)
            accn = f.get("accn", "N/A")
            filed = f.get("filed", "N/A")
            
            yoy_str = "N/A"
            if i + 1 < len(selected_facts):
                prev_val = float(selected_facts[i + 1].get("val", 0))
                if prev_val:
                    change = (val - prev_val) / abs(prev_val)
                    sign = "+" if change > 0 else ""
                    yoy_str = f"{sign}{change * 100:.2f}%"
                    
            rows.append(f"| FY{fy} | {val_str} | {yoy_str} | {filed} | `{accn}` |")
            
        header = [
            f"📊 **Period Comparison for Metric `{concept}` - {meta.get('title', ticker_or_cik)}**",
            f"Taxonomy: `us-gaap` | Unit: `{unit_key}`",
            "",
            "| Fiscal Period | Value | YoY Growth | Filing Date | Source Accession |",
            "|---|---|---|---|---|"
        ]
        return "\n".join(header + rows)
    except Exception as e:
        logger.error(f"Error in compare_periods: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def detect_red_flags(ticker_or_cik: str = "") -> str:
    """Apply financial red-flag tests for cash conversion, margin compression, receivables lag, and dilution."""
    logger.info(f"Executing detect_red_flags for ticker_or_cik='{ticker_or_cik}'")
    if not ticker_or_cik.strip():
        return "❌ Error: ticker_or_cik parameter is required."
        
    try:
        meta = await _resolve_cik(ticker_or_cik)
        cik = meta["cik"]
        facts = await _get_company_facts(cik)
        
        _, _, rev_list = _find_concept_units(facts, ["Revenues", "SalesRevenueNet"])
        _, _, net_inc_list = _find_concept_units(facts, ["NetIncomeLoss", "ProfitLoss"])
        _, _, op_inc_list = _find_concept_units(facts, ["OperatingIncomeLoss"])
        _, _, op_cf_list = _find_concept_units(facts, ["NetCashProvidedByUsedInOperatingActivities"])
        _, _, capex_list = _find_concept_units(facts, ["PaymentsToAcquirePropertyPlantAndEquipment"])
        _, _, ar_list = _find_concept_units(facts, ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"])
        _, _, sbc_list = _find_concept_units(facts, ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"])
        
        rev_fy = _filter_facts(rev_list, form_types=["10-K"], fp_filter="FY")
        rev_fy.sort(key=lambda x: x.get("fy", 0), reverse=True)
        if len(rev_fy) < 2:
            return f"⚠️ Insufficient historical 10-K data to evaluate red flags for {meta.get('title', ticker_or_cik)}."
            
        curr_fy = rev_fy[0].get("fy")
        prev_fy = rev_fy[1].get("fy")
        
        def get_val(fact_list, fy):
            for f in _filter_facts(fact_list, form_types=["10-K"], fp_filter="FY"):
                if f.get("fy") == fy:
                    return float(f.get("val", 0))
            return 0.0
            
        c_rev, p_rev = get_val(rev_list, curr_fy), get_val(rev_list, prev_fy)
        c_net, p_net = get_val(net_inc_list, curr_fy), get_val(net_inc_list, prev_fy)
        c_opinc, p_opinc = get_val(op_inc_list, curr_fy), get_val(op_inc_list, prev_fy)
        c_opcf = get_val(op_cf_list, curr_fy)
        c_capex = get_val(capex_list, curr_fy)
        c_ar, p_ar = get_val(ar_list, curr_fy), get_val(ar_list, prev_fy)
        c_sbc = get_val(sbc_list, curr_fy)
        
        c_fcf = c_opcf - c_capex
        rev_growth = ((c_rev - p_rev) / abs(p_rev)) if p_rev else 0.0
        ar_growth = ((c_ar - p_ar) / abs(p_ar)) if p_ar else 0.0
        c_op_margin = (c_opinc / c_rev) if c_rev else 0.0
        p_op_margin = (p_opinc / p_rev) if p_rev else 0.0
        margin_change = c_op_margin - p_op_margin
        sbc_intensity = (c_sbc / c_rev) if c_rev else 0.0
        
        flags = []
        
        if c_net > 0 and c_fcf < 0:
            flags.append(f"| 🚨 High | **Cash Conversion Divergence** | Net Income is positive ({_format_currency(c_net)}), but Free Cash Flow is negative ({_format_currency(c_fcf)}). |")
        else:
            flags.append(f"| ✅ Normal | **Cash Conversion** | FCF ({_format_currency(c_fcf)}) aligns healthy with Net Income ({_format_currency(c_net)}). |")
            
        if rev_growth > 0.05 and margin_change < -0.02:
            flags.append(f"| ⚠️ Medium | **Margin Compression** | Revenue grew {_format_pct(rev_growth)}, but operating margin compressed by {margin_change * 100:.2f}%. |")
        else:
            flags.append(f"| ✅ Normal | **Margin Stability** | Operating margin shift ({margin_change * 100:+.2f}%) aligns with revenue growth ({_format_pct(rev_growth)}). |")
            
        if ar_growth > (rev_growth + 0.10) and c_ar > 0:
            flags.append(f"| ⚠️ Medium | **Receivables Outpacing Revenue** | Accounts Receivable grew {_format_pct(ar_growth)} vs Revenue growth of {_format_pct(rev_growth)}. |")
        else:
            flags.append(f"| ✅ Normal | **Working Capital / Receivables** | Receivables growth ({_format_pct(ar_growth)}) is proportional to revenue growth. |")
            
        if sbc_intensity > 0.08:
            flags.append(f"| ⚠️ Medium | **High SBC Dilution** | Stock-Based Compensation ({_format_currency(c_sbc)}) represents {_format_pct(sbc_intensity)} of total revenue. |")
        else:
            flags.append(f"| ✅ Normal | **Stock-Based Compensation** | SBC intensity ({_format_pct(sbc_intensity)}) is within standard threshold (<8%). |")
            
        header = [
            f"🚩 **Automated Red-Flag Diagnostics for {meta.get('title', ticker_or_cik)} (FY{curr_fy})**",
            "",
            "| Status | Diagnostic Test | Observed Condition & Metric Evidence |",
            "|---|---|---|"
        ]
        return "\n".join(header + flags)
    except Exception as e:
        logger.error(f"Error in detect_red_flags: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def get_evidence(ticker_or_cik: str = "", fact_tag: str = "") -> str:
    """Return filing accession numbers, XBRL fact tags, URLs, and calculation traces supporting analysis results."""
    logger.info(f"Executing get_evidence for ticker_or_cik='{ticker_or_cik}', fact_tag='{fact_tag}'")
    if not ticker_or_cik.strip():
        return "❌ Error: ticker_or_cik parameter is required."
        
    try:
        meta = await _resolve_cik(ticker_or_cik)
        cik = meta["cik"]
        facts_data = await _get_company_facts(cik)
        
        tag = fact_tag.strip() or "Revenues"
        c_name, unit_key, fact_list = _find_concept_units(facts_data, [tag, "SalesRevenueNet", "NetIncomeLoss"])
        
        if not fact_list:
            return f"⚠️ Fact tag '{tag}' not found in SEC EDGAR facts for {meta.get('title', ticker_or_cik)}."
            
        fy_facts = _filter_facts(fact_list, form_types=["10-K"], fp_filter="FY")
        fy_facts.sort(key=lambda x: x.get("fy", 0), reverse=True)
        latest_fact = fy_facts[0] if fy_facts else fact_list[0]
        
        acc_raw = latest_fact.get("accn", "N/A")
        acc_no_dash = acc_raw.replace("-", "")
        fy = latest_fact.get("fy", "N/A")
        val = latest_fact.get("val", "N/A")
        filed = latest_fact.get("filed", "N/A")
        form = latest_fact.get("form", "N/A")
        
        sec_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dash}/" if acc_raw != "N/A" else "N/A"
        
        output = [
            f"🔍 **SEC Audit Evidence & Calculation Trace**",
            "",
            f"| Attribute | Audit Detail |",
            f"|---|---|",
            f"| **Target Entity** | {meta.get('title', ticker_or_cik)} (CIK: `{cik}`) |",
            f"| **XBRL Concept Tag** | `us-gaap:{c_name}` |",
            f"| **Fiscal Period** | FY{fy} (Form `{form}`) |",
            f"| **Reported Fact Value** | **{_format_currency(val)}** (Raw: `{val}`) |",
            f"| **Unit of Measure** | `{unit_key}` |",
            f"| **Filing Date** | {filed} |",
            f"| **SEC Accession Number** | `{acc_raw}` |",
            f"| **SEC EDGAR Directory URL** | [{sec_url}]({sec_url}) |",
            "",
            "> ℹ️ *Note: SEC EDGAR bulk datasets and XBRL facts provide auditability but are secondary to reviewing the full filed form.*"
        ]
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error in get_evidence: {e}")
        return f"❌ Error: {str(e)}"

# === SERVER STARTUP ===
if __name__ == "__main__":
    logger.info("Starting Stock Analysis MCP Server...")
    try:
        mcp.run(transport='stdio')
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
