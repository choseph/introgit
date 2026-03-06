"""Analyze and rank Hyperliquid vaults by profitability."""

from . import api


def get_top_vaults(limit: int = 20, min_tvl: float | None = None) -> list[dict]:
    """Fetch all vaults and return the most profitable ones.

    Args:
        limit: Maximum number of vaults to return.
        min_tvl: If set, only include vaults with TVL >= this value.

    Returns:
        List of vault dicts sorted by all-time PnL descending.
    """
    raw = api.fetch_vault_summaries()

    vaults = []
    for entry in raw:
        if isinstance(entry, dict):
            vault = _parse_vault_summary(entry)
            if vault:
                vaults.append(vault)

    if min_tvl is not None:
        vaults = [v for v in vaults if v["tvl"] >= min_tvl]

    # Sort by PnL descending
    vaults.sort(key=lambda v: v["pnl"], reverse=True)

    return vaults[:limit]


def get_vault_details(vault_address: str) -> dict:
    """Get detailed performance info for a single vault."""
    raw = api.fetch_vault_details(vault_address)

    result = {
        "address": vault_address,
        "name": None,
        "leader": None,
        "description": None,
        "tvl": 0.0,
        "apr": 0.0,
        "leader_commission": 0.0,
        "follower_count": 0,
        "is_closed": False,
        "pnl_by_period": {},
        "volume_by_period": {},
    }

    if not isinstance(raw, dict):
        return result

    result["name"] = raw.get("name")
    result["leader"] = raw.get("leader")
    result["description"] = raw.get("description")
    result["apr"] = _safe_float(raw.get("apr"))
    result["leader_commission"] = _safe_float(raw.get("leaderCommission") or raw.get("leaderFraction"))
    result["is_closed"] = raw.get("isClosed", False)

    followers = raw.get("followers", [])
    result["follower_count"] = len(followers)

    # Sum follower equity for TVL
    total_equity = 0.0
    for f in followers:
        if isinstance(f, dict):
            total_equity += _safe_float(f.get("vaultEquity"))
    result["tvl"] = _safe_float(raw.get("tvl")) or total_equity

    # Parse portfolio performance by period
    portfolio = raw.get("portfolio", [])
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


def _parse_vault_summary(entry: dict) -> dict | None:
    """Parse a vault summary entry into a normalized dict."""
    address = entry.get("vaultAddress") or entry.get("address") or entry.get("vault")
    if not address:
        return None

    return {
        "address": address,
        "name": entry.get("name") or entry.get("vaultName") or address[:10] + "...",
        "leader": entry.get("leader") or entry.get("leaderAddress") or "",
        "tvl": _safe_float(entry.get("tvl") or entry.get("totalVaultEquity") or 0),
        "pnl": _safe_float(entry.get("allTimePnl") or entry.get("pnl") or 0),
        "apr": _safe_float(entry.get("apr") or 0),
        "follower_count": int(_safe_float(entry.get("followerCount") or entry.get("numFollowers") or 0)),
    }


def _safe_float(val) -> float:
    """Safely convert a value to float."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
