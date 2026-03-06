"""Hyperliquid API client for fetching trader and vault data."""

import requests

BASE_URL = "https://api.hyperliquid.xyz"
STATS_URL = "https://stats-data.hyperliquid.xyz/Mainnet"

INFO_ENDPOINT = f"{BASE_URL}/info"
LEADERBOARD_ENDPOINT = f"{STATS_URL}/leaderboard"


def _post_info(payload: dict) -> dict | list:
    """Make a POST request to the Hyperliquid info endpoint."""
    resp = requests.post(INFO_ENDPOINT, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_leaderboard() -> list[dict]:
    """Fetch the trader leaderboard from the stats endpoint."""
    resp = requests.get(LEADERBOARD_ENDPOINT, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_portfolio(address: str) -> list[dict]:
    """Fetch portfolio performance data for a specific user address."""
    return _post_info({"type": "portfolio", "user": address})


def fetch_clearinghouse_state(address: str) -> dict:
    """Fetch a user's perpetuals account state (positions, margin, etc.)."""
    return _post_info({"type": "clearinghouseState", "user": address})


def fetch_vault_details(vault_address: str) -> dict:
    """Fetch detailed information about a specific vault."""
    return _post_info({"type": "vaultDetails", "vaultAddress": vault_address})


def fetch_vault_summaries() -> list[dict]:
    """Fetch summary info for all vaults. Falls back to stats endpoint if empty."""
    result = _post_info({"type": "vaultSummaries"})
    if result:
        return result
    # Fallback: the official endpoint sometimes returns [] so try stats-data
    resp = requests.get(f"{STATS_URL}/vaults", timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_user_fills(address: str) -> list[dict]:
    """Fetch recent trade fills for a user."""
    return _post_info({"type": "userFills", "user": address})
