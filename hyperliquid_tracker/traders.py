"""Analyze and rank Hyperliquid traders by profitability."""

from . import api


def get_top_traders(limit: int = 20, min_pnl: float | None = None) -> list[dict]:
    """Fetch the leaderboard and return the most profitable traders.

    Args:
        limit: Maximum number of traders to return.
        min_pnl: If set, only include traders with all-time PnL >= this value.

    Returns:
        List of trader dicts sorted by all-time PnL descending.
    """
    raw = api.fetch_leaderboard()

    traders = []
    for entry in raw:
        # The leaderboard response can vary in structure;
        # handle both flat and nested formats.
        if isinstance(entry, dict):
            trader = _parse_leaderboard_entry(entry)
            if trader:
                traders.append(trader)
        elif isinstance(entry, list) and len(entry) >= 2:
            # Some formats return [address, {...stats}]
            addr = entry[0]
            stats = entry[1] if isinstance(entry[1], dict) else {}
            trader = _parse_leaderboard_entry(stats, default_address=addr)
            if trader:
                traders.append(trader)

    # Sort by all-time PnL descending
    traders.sort(key=lambda t: t["pnl"], reverse=True)

    if min_pnl is not None:
        traders = [t for t in traders if t["pnl"] >= min_pnl]

    return traders[:limit]


def get_trader_details(address: str) -> dict:
    """Get detailed performance info for a single trader."""
    portfolio = api.fetch_portfolio(address)
    clearinghouse = api.fetch_clearinghouse_state(address)

    result = {
        "address": address,
        "account_value": None,
        "pnl_by_period": {},
        "volume_by_period": {},
        "positions": [],
    }

    # Parse clearinghouse state
    if isinstance(clearinghouse, dict):
        margin = clearinghouse.get("marginSummary") or clearinghouse.get("crossMarginSummary", {})
        if margin:
            result["account_value"] = _safe_float(margin.get("accountValue"))

        for pos in clearinghouse.get("assetPositions", []):
            p = pos.get("position", pos)
            result["positions"].append({
                "coin": p.get("coin"),
                "size": _safe_float(p.get("szi")),
                "entry_price": _safe_float(p.get("entryPx")),
                "unrealized_pnl": _safe_float(p.get("unrealizedPnl")),
                "leverage": _safe_float(p.get("leverage", {}).get("value") if isinstance(p.get("leverage"), dict) else p.get("leverage")),
            })

    # Parse portfolio performance
    if isinstance(portfolio, list):
        for period_data in portfolio:
            if not isinstance(period_data, list) or len(period_data) < 2:
                continue
            period_name = period_data[0]
            pdata = period_data[1] if isinstance(period_data[1], dict) else {}

            pnl_history = pdata.get("pnlHistory", [])
            if pnl_history:
                last_pnl = pnl_history[-1]
                if isinstance(last_pnl, list) and len(last_pnl) >= 2:
                    result["pnl_by_period"][period_name] = _safe_float(last_pnl[1])
                elif isinstance(last_pnl, dict):
                    result["pnl_by_period"][period_name] = _safe_float(last_pnl.get("pnl"))

            result["volume_by_period"][period_name] = _safe_float(pdata.get("vlm"))

    return result


def _parse_leaderboard_entry(entry: dict, default_address: str = "") -> dict | None:
    """Parse a single leaderboard entry into a normalized dict."""
    address = entry.get("ethAddress") or entry.get("address") or entry.get("user") or default_address
    if not address:
        return None

    # Try various field names the API might use
    pnl = _safe_float(
        entry.get("allTimePnl")
        or entry.get("pnl")
        or entry.get("totalPnl")
        or entry.get("accountValue")
        or 0
    )

    return {
        "address": address,
        "display_name": entry.get("displayName") or entry.get("name") or address[:10] + "...",
        "pnl": pnl,
        "roi": _safe_float(entry.get("roi") or entry.get("allTimeRoi") or 0),
        "account_value": _safe_float(entry.get("accountValue") or 0),
        "volume": _safe_float(entry.get("vlm") or entry.get("volume") or 0),
        "win_rate": _safe_float(entry.get("winRate") or 0),
    }


def _safe_float(val) -> float:
    """Safely convert a value to float."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
