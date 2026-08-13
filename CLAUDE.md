# CLAUDE.md - Stock Analysis MCP Server Developer Guide

## Core Guidelines & Architectural Constraints

### FastMCP Development Rules
1. **Single-Line Docstrings**: ALL `@mcp.tool()` function docstrings MUST be strictly a single line. Multi-line docstrings cause MCP gateway panic errors.
2. **No `@mcp.prompt()` Decorators**: Do not add prompt decorators as they break compatibility with Claude Desktop.
3. **No Prompt Argument**: Initialize FastMCP without prompt parameters: `mcp = FastMCP("stock_analysis")`.
4. **No Complex Typing Hints**: Do not use `typing` module imports (`Optional`, `Union`, `List[str]`). Use basic Python types (`str`, `int`, `float`, `dict`, `list`).
5. **Default to Empty Strings**: All optional tool arguments MUST default to `""` (empty string) rather than `None`.
6. **Formatted String Returns**: All tools must return clean Markdown-formatted string outputs containing status emojis (`✅`, `❌`, `📊`, `⚡`, `⚠️`, `🚨`, `🔍`).
7. **Logging to Stderr**: Ensure all server logging writes exclusively to `sys.stderr` to keep standard I/O clean for MCP protocol messages.

### SEC EDGAR API Usage
- **User-Agent Compliance**: SEC EDGAR strictly enforces rate limits (max 10 requests/sec) and requires a descriptive User-Agent header (e.g., `StockAnalysisMCP/1.0 (contact@example.com)`).
- **XBRL Facts Mapping**: Primary financials rely on US-GAAP taxonomy concept tags (`Revenues`, `SalesRevenueNet`, `NetIncomeLoss`, `OperatingIncomeLoss`, `NetCashProvidedByUsedInOperatingActivities`, `PaymentsToAcquirePropertyPlantAndEquipment`).

## Key Development Commands

### Local Testing & Compilation
```powershell
# Verify syntax and compile python script
python -m py_compile stock_analysis_server.py

# Test Docker container build
docker build -t stock-analysis-mcp-server:latest .
```

### Docker Run Test
```powershell
docker run -i --rm stock-analysis-mcp-server:latest
```
