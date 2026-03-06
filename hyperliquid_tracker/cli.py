"""CLI entry point for the Hyperliquid Tracker tool."""

import argparse
import json
import sys

from tabulate import tabulate

from . import traders, vaults


def format_usd(val: float) -> str:
    """Format a float as a USD string."""
    if abs(val) >= 1_000_000:
        return f"${val / 1_000_000:,.2f}M"
    if abs(val) >= 1_000:
        return f"${val / 1_000:,.2f}K"
    return f"${val:,.2f}"


def format_pct(val: float) -> str:
    """Format a float as a percentage."""
    return f"{val * 100:.2f}%" if val < 100 else f"{val:.2f}%"


def cmd_top_traders(args):
    """Show the most profitable traders on Hyperliquid."""
    print(f"\nFetching top {args.limit} traders from Hyperliquid leaderboard...\n")

    try:
        top = traders.get_top_traders(
            limit=args.limit,
            min_pnl=args.min_pnl,
        )
    except Exception as e:
        print(f"Error fetching leaderboard: {e}", file=sys.stderr)
        sys.exit(1)

    if not top:
        print("No traders found matching criteria.")
        return

    if args.json:
        print(json.dumps(top, indent=2))
        return

    table = []
    for i, t in enumerate(top, 1):
        table.append([
            i,
            t["display_name"],
            t["address"][:10] + "...",
            format_usd(t["pnl"]),
            format_pct(t["roi"]),
            format_usd(t["account_value"]),
        ])

    headers = ["#", "Name", "Address", "All-Time PnL", "ROI", "Account Value"]
    print(tabulate(table, headers=headers, tablefmt="simple"))
    print(f"\nTotal traders shown: {len(top)}")


def cmd_top_vaults(args):
    """Show the most profitable vaults on Hyperliquid."""
    print(f"\nFetching top {args.limit} vaults from Hyperliquid...\n")

    try:
        top = vaults.get_top_vaults(
            limit=args.limit,
            min_tvl=args.min_tvl,
        )
    except Exception as e:
        print(f"Error fetching vaults: {e}", file=sys.stderr)
        sys.exit(1)

    if not top:
        print("No vaults found matching criteria.")
        return

    if args.json:
        print(json.dumps(top, indent=2))
        return

    table = []
    for i, v in enumerate(top, 1):
        table.append([
            i,
            v["name"],
            v["address"][:10] + "...",
            format_usd(v["pnl"]),
            format_pct(v["apr"]),
            format_usd(v["tvl"]),
            v["follower_count"],
        ])

    headers = ["#", "Name", "Address", "All-Time PnL", "APR", "TVL", "Followers"]
    print(tabulate(table, headers=headers, tablefmt="simple"))
    print(f"\nTotal vaults shown: {len(top)}")


def cmd_trader_detail(args):
    """Show detailed info for a specific trader."""
    print(f"\nFetching details for trader {args.address}...\n")

    try:
        detail = traders.get_trader_details(args.address)
    except Exception as e:
        print(f"Error fetching trader details: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(detail, indent=2))
        return

    print(f"Address:       {detail['address']}")
    print(f"Account Value: {format_usd(detail['account_value'] or 0)}")

    if detail["pnl_by_period"]:
        print("\nPnL by Period:")
        for period, pnl in detail["pnl_by_period"].items():
            print(f"  {period:15s} {format_usd(pnl)}")

    if detail["volume_by_period"]:
        print("\nVolume by Period:")
        for period, vol in detail["volume_by_period"].items():
            print(f"  {period:15s} {format_usd(vol)}")

    if detail["positions"]:
        print("\nOpen Positions:")
        pos_table = []
        for p in detail["positions"]:
            pos_table.append([
                p["coin"],
                f"{p['size']:.4f}",
                format_usd(p["entry_price"]),
                format_usd(p["unrealized_pnl"]),
                f"{p['leverage']:.1f}x" if p["leverage"] else "N/A",
            ])
        headers = ["Coin", "Size", "Entry Price", "Unrealized PnL", "Leverage"]
        print(tabulate(pos_table, headers=headers, tablefmt="simple"))
    else:
        print("\nNo open positions.")


def cmd_vault_detail(args):
    """Show detailed info for a specific vault."""
    print(f"\nFetching details for vault {args.address}...\n")

    try:
        detail = vaults.get_vault_details(args.address)
    except Exception as e:
        print(f"Error fetching vault details: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(detail, indent=2))
        return

    print(f"Name:              {detail['name'] or 'N/A'}")
    print(f"Address:           {detail['address']}")
    print(f"Leader:            {detail['leader'] or 'N/A'}")
    print(f"TVL:               {format_usd(detail['tvl'])}")
    print(f"APR:               {format_pct(detail['apr'])}")
    print(f"Leader Commission: {format_pct(detail['leader_commission'])}")
    print(f"Followers:         {detail['follower_count']}")
    print(f"Closed:            {'Yes' if detail['is_closed'] else 'No'}")

    if detail.get("description"):
        print(f"\nDescription: {detail['description']}")

    if detail["pnl_by_period"]:
        print("\nPnL by Period:")
        for period, pnl in detail["pnl_by_period"].items():
            print(f"  {period:15s} {format_usd(pnl)}")

    if detail["volume_by_period"]:
        print("\nVolume by Period:")
        for period, vol in detail["volume_by_period"].items():
            print(f"  {period:15s} {format_usd(vol)}")


def main():
    parser = argparse.ArgumentParser(
        prog="hl-tracker",
        description="Identify extremely profitable Hyperliquid traders and vaults.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- top-traders ---
    p_traders = subparsers.add_parser("top-traders", help="Show most profitable traders")
    p_traders.add_argument("-n", "--limit", type=int, default=20, help="Number of traders to show (default: 20)")
    p_traders.add_argument("--min-pnl", type=float, default=None, help="Minimum all-time PnL filter (USD)")
    p_traders.add_argument("--json", action="store_true", help="Output raw JSON")
    p_traders.set_defaults(func=cmd_top_traders)

    # --- top-vaults ---
    p_vaults = subparsers.add_parser("top-vaults", help="Show most profitable vaults")
    p_vaults.add_argument("-n", "--limit", type=int, default=20, help="Number of vaults to show (default: 20)")
    p_vaults.add_argument("--min-tvl", type=float, default=None, help="Minimum TVL filter (USD)")
    p_vaults.add_argument("--json", action="store_true", help="Output raw JSON")
    p_vaults.set_defaults(func=cmd_top_vaults)

    # --- trader ---
    p_trader = subparsers.add_parser("trader", help="Show details for a specific trader")
    p_trader.add_argument("address", help="Trader wallet address (0x...)")
    p_trader.add_argument("--json", action="store_true", help="Output raw JSON")
    p_trader.set_defaults(func=cmd_trader_detail)

    # --- vault ---
    p_vault = subparsers.add_parser("vault", help="Show details for a specific vault")
    p_vault.add_argument("address", help="Vault address (0x...)")
    p_vault.add_argument("--json", action="store_true", help="Output raw JSON")
    p_vault.set_defaults(func=cmd_vault_detail)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
