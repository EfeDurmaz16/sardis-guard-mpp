#!/usr/bin/env python3
"""Sardis Guard CLI — interact with the MPP policy firewall from your terminal.

Wraps `tempo request` for MPP-gated endpoints and `curl` for free endpoints.

Usage:
    python src/cli.py evaluate --amount 1.50 --merchant perplexity.ai
    python src/cli.py simulate --amount 100 --merchant gambling.com
    python src/cli.py mandate
    python src/cli.py mandate --update --max-per-tx 10 --max-daily 200
    python src/cli.py stats
    python src/cli.py audit
    python src/cli.py health
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import textwrap

# ──────────────────────────────────────────────────────────────────────────────
# ANSI color helpers (no external deps)
# ──────────────────────────────────────────────────────────────────────────────

NO_COLOR = os.environ.get("NO_COLOR") is not None or not sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if NO_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def bold(t: str) -> str:
    return _c("1", t)


def dim(t: str) -> str:
    return _c("2", t)


def green(t: str) -> str:
    return _c("32", t)


def red(t: str) -> str:
    return _c("31", t)


def yellow(t: str) -> str:
    return _c("33", t)


def cyan(t: str) -> str:
    return _c("36", t)


def magenta(t: str) -> str:
    return _c("35", t)


def bg_green(t: str) -> str:
    return _c("42;97", t)


def bg_red(t: str) -> str:
    return _c("41;97", t)


def bg_cyan(t: str) -> str:
    return _c("46;97", t)


# Symbols
CHECK = green("✓")
CROSS = red("✗")
ARROW = cyan("→")
BULLET = dim("•")
SHIELD = "🛡"
COIN = "💰"
LOCK = "🔒"

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_GUARD_URL = "https://dendric-margie-answerlessly.ngrok-free.dev"

# ──────────────────────────────────────────────────────────────────────────────
# Transport: tempo request (MPP-paid) or curl (free)
# ──────────────────────────────────────────────────────────────────────────────


def _tempo_request(
    method: str,
    url: str,
    body: dict | None = None,
) -> dict:
    """Call an MPP-gated endpoint via `tempo request -j` (JSON output)."""
    cmd = ["tempo", "request", "-j"]

    if method == "PUT":
        cmd += ["-X", "PUT"]
    elif method == "POST":
        cmd += ["-X", "POST"]
    # GET is default

    if body is not None:
        cmd += ["--json", json.dumps(body)]

    cmd.append(url)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        print(red("Error: `tempo` CLI not found. Install it with: npm i -g @anthropic-ai/sdk"))
        print(dim("  Or set it up from https://tempo.com"))
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(red("Error: Request timed out after 30s"))
        sys.exit(1)

    output = result.stdout.strip()
    if result.returncode != 0:
        stderr = result.stderr.strip()
        print(red(f"Error: tempo request failed (exit {result.returncode})"))
        if stderr:
            print(dim(stderr))
        if output:
            print(dim(output))
        sys.exit(1)

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        # tempo may wrap the JSON with extra output lines; try to find it
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        print(red("Error: Could not parse JSON response from server"))
        print(dim(f"Raw output:\n{output}"))
        sys.exit(1)


def _curl_request(url: str) -> dict:
    """Call a free endpoint via curl."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-H", "ngrok-skip-browser-warning: 1", url],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError:
        print(red("Error: `curl` not found"))
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(red("Error: Request timed out"))
        sys.exit(1)

    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        print(red("Error: Could not parse response"))
        print(dim(result.stdout[:500]))
        sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# Display helpers
# ──────────────────────────────────────────────────────────────────────────────

BANNER = r"""
   ___              _ _       ___                     _
  / __| __ _ _ _ __| (_)___  / __|_  _ __ _ _ _ __| |
  \__ \/ _` | '_/ _` | (_-< | (_ | || / _` | '_/ _` |
  |___/\__,_|_| \__,_|_/__/  \___|\_,_\__,_|_| \__,_|
"""

DIVIDER_WIDTH = 62


def banner():
    print(cyan(BANNER))
    print(dim("  MPP Policy Firewall CLI".center(DIVIDER_WIDTH)))
    print()


def divider(title: str = ""):
    if title:
        pad = DIVIDER_WIDTH - len(title) - 4
        left = pad // 2
        right = pad - left
        print(dim("─" * left + "[ ") + bold(title) + dim(" ]" + "─" * right))
    else:
        print(dim("─" * DIVIDER_WIDTH))


def kv(key: str, value: str, indent: int = 2):
    print(" " * indent + dim(f"{key}:") + " " + value)


def section(title: str):
    print()
    print(f"  {bold(title)}")
    print()


def print_payment_info(payment: dict):
    """Show MPP payment receipt."""
    tx = payment.get("tx", "N/A")
    method = payment.get("method", "tempo")
    amount = payment.get("amount_charged", "?")
    currency = payment.get("currency", "USDC")

    print()
    divider("MPP Payment")
    kv("Tx Hash", cyan(str(tx)))
    kv("Method", method)
    kv("Charged", f"${amount} {currency}")
    divider()


def print_checks(checks: list[dict]):
    """Render the 12-check grid."""
    print()
    for i, c in enumerate(checks, 1):
        result = c.get("result", "FAIL")
        name = c.get("name", "unknown")
        reason = c.get("reason", "")
        latency = c.get("latency_ms", 0)

        if result == "PASS":
            icon = CHECK
            result_str = green("PASS")
        elif result == "SKIP":
            icon = yellow("○")
            result_str = yellow("SKIP")
        else:
            icon = CROSS
            result_str = red("FAIL")

        num = dim(f"{i:>2}.")
        name_padded = f"{name:<22}"
        lat = dim(f"{latency:>6.1f}ms")

        print(f"  {num} {icon} {result_str}  {name_padded}  {lat}  {dim(reason)}")


# ──────────────────────────────────────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────────────────────────────────────


def cmd_evaluate(args):
    """Evaluate a payment against the 12-check policy engine."""
    banner()
    divider("EVALUATE PAYMENT")
    print()
    kv("Amount", bold(f"${args.amount}"))
    kv("Merchant", bold(args.merchant))
    kv("Currency", args.currency)
    kv("Network", args.network)
    if args.category != "general":
        kv("Category", args.category)
    if args.memo:
        kv("Memo", args.memo)

    body = {
        "amount": str(args.amount),
        "merchant": args.merchant,
        "currency": args.currency,
        "network": args.network,
        "category": args.category,
    }
    if args.memo:
        body["memo"] = args.memo

    print()
    print(dim("  Sending payment + policy request via MPP..."))
    print()

    data = _tempo_request("POST", f"{args.url}/evaluate", body)

    verdict = data.get("verdict", {})
    allowed = verdict.get("allowed", False)
    summary = verdict.get("summary", "")
    total_ms = verdict.get("total_latency_ms", 0)
    checks = verdict.get("checks", [])

    # Big verdict banner
    if allowed:
        print(f"  {bg_green(' PASS ')}  {green(summary)}")
    else:
        print(f"  {bg_red(' FAIL ')}  {red(summary)}")

    section(f"{SHIELD}  Policy Checks ({len(checks)}/12)")
    print_checks(checks)

    kv("Total Latency", f"{total_ms:.1f}ms", indent=4)

    agent = data.get("agent", "unknown")
    print()
    kv("Agent", dim(agent))

    if "payment" in data:
        print_payment_info(data["payment"])


def cmd_simulate(args):
    """Dry-run policy evaluation (no state changes)."""
    banner()
    divider("SIMULATE (DRY RUN)")
    print()
    kv("Amount", bold(f"${args.amount}"))
    kv("Merchant", bold(args.merchant))
    kv("Currency", args.currency)
    kv("Network", args.network)
    if args.category != "general":
        kv("Category", args.category)

    body = {
        "amount": str(args.amount),
        "merchant": args.merchant,
        "currency": args.currency,
        "network": args.network,
        "category": args.category,
    }
    if args.memo:
        body["memo"] = args.memo

    print()
    print(dim("  Sending simulation request via MPP..."))
    print()

    data = _tempo_request("POST", f"{args.url}/simulate", body)

    verdict = data.get("verdict", {})
    allowed = verdict.get("allowed", False)
    summary = verdict.get("summary", "")
    checks = verdict.get("checks", [])

    if allowed:
        print(f"  {bg_green(' PASS ')}  {green(summary)}")
    else:
        print(f"  {bg_red(' FAIL ')}  {red(summary)}")

    print(f"  {dim('(simulation — no spending state updated)')}")

    section(f"{SHIELD}  Policy Checks")
    print_checks(checks)

    if "payment" in data:
        print_payment_info(data["payment"])


def cmd_mandate(args):
    """View or update spending mandate."""
    banner()

    if args.update:
        # PUT /mandate
        divider("UPDATE MANDATE")
        body: dict = {}
        if args.max_per_tx is not None:
            body["max_per_tx"] = str(args.max_per_tx)
        if args.max_daily is not None:
            body["max_daily"] = str(args.max_daily)
        if args.allowed_merchant:
            body["allowed_merchants"] = args.allowed_merchant
        if args.block_merchant:
            body["blocked_merchants"] = args.block_merchant
        if args.allowed_chain:
            body["allowed_chains"] = args.allowed_chain
        if args.allowed_currency:
            body["allowed_currencies"] = args.allowed_currency
        if args.require_memo is not None:
            body["require_memo"] = args.require_memo
        if args.cooldown is not None:
            body["cooldown_seconds"] = args.cooldown

        if not body:
            print()
            print(yellow("  No updates specified. Use --max-per-tx, --max-daily, etc."))
            sys.exit(1)

        print()
        print(dim("  Changes to apply:"))
        for k, v in body.items():
            kv(k, bold(str(v)), indent=4)

        print()
        print(dim("  Sending update via MPP..."))
        print()

        data = _tempo_request("PUT", f"{args.url}/mandate", body)

        if data.get("mandate_updated"):
            print(f"  {CHECK}  {green('Mandate updated successfully')}")
        else:
            print(f"  {CROSS}  {red('Update may have failed')}")

        agent = data.get("agent", "unknown")
        kv("Agent", dim(agent))

        if "payment" in data:
            print_payment_info(data["payment"])

    else:
        # GET /mandate
        divider("SPENDING MANDATE")
        print()
        print(dim("  Fetching mandate via MPP..."))
        print()

        data = _tempo_request("GET", f"{args.url}/mandate")
        mandate = data.get("mandate", {})
        agent = data.get("agent", "unknown")

        kv("Agent", bold(agent))
        print()

        divider("Limits")
        kv("Max per Transaction", bold(f"${mandate.get('max_per_tx', '?')}"))
        kv("Max Daily Spending", bold(f"${mandate.get('max_daily', '?')}"))
        kv("Active", green("Yes") if mandate.get("active") else red("No"))
        kv("Require Memo", "Yes" if mandate.get("require_memo") else dim("No"))
        cooldown = mandate.get("cooldown_seconds", 0)
        kv("Cooldown", f"{cooldown}s" if cooldown else dim("None"))

        print()
        divider("Allowed Chains & Currencies")
        chains = mandate.get("allowed_chains", [])
        currencies = mandate.get("allowed_currencies", [])
        kv("Chains", ", ".join(chains) if chains else dim("all"))
        kv("Currencies", ", ".join(currencies) if currencies else dim("all"))

        print()
        divider("Merchant Rules")
        allowed = mandate.get("allowed_merchants", [])
        blocked = mandate.get("blocked_merchants", [])
        kv("Allowlist", ", ".join(allowed) if allowed else dim("(open — all allowed)"))
        kv("Blocklist", ", ".join(red(m) for m in blocked) if blocked else dim("(none)"))

        print()
        divider("Category Rules")
        allowed_cat = mandate.get("allowed_categories", [])
        blocked_cat = mandate.get("blocked_categories", [])
        kv("Allowlist", ", ".join(allowed_cat) if allowed_cat else dim("(open — all allowed)"))
        kv("Blocklist", ", ".join(red(c) for c in blocked_cat) if blocked_cat else dim("(none)"))

        if "payment" in data:
            print_payment_info(data["payment"])


def cmd_stats(args):
    """Show agent spending stats."""
    banner()
    divider("SPENDING STATS")
    print()
    print(dim("  Fetching stats via MPP..."))
    print()

    data = _tempo_request("GET", f"{args.url}/stats")

    agent = data.get("agent", "unknown")
    stats = data.get("stats", {})

    kv("Agent", bold(agent))
    print()

    spent = stats.get("spent_today", "0")
    tx_count = stats.get("tx_count_today", 0)
    last_ts = stats.get("last_payment_ts", 0)

    # Spending bar visualization
    spent_f = float(spent)
    bar_max = 50.0  # assume $50 daily for bar scale
    bar_len = 30
    filled = int(min(spent_f / bar_max, 1.0) * bar_len)
    bar = green("█" * filled) + dim("░" * (bar_len - filled))

    kv("Spent Today", f"{bold(f'${spent}')}  {bar}  {dim(f'(of $50 daily)')}")
    kv("Transactions", bold(str(tx_count)))

    if last_ts and float(last_ts) > 0:
        import datetime
        ts = datetime.datetime.fromtimestamp(float(last_ts))
        kv("Last Payment", ts.strftime("%Y-%m-%d %H:%M:%S"))
    else:
        kv("Last Payment", dim("None"))

    if "payment" in data:
        print_payment_info(data["payment"])


def cmd_audit(args):
    """Show full audit trail."""
    banner()
    divider("AUDIT TRAIL")
    print()
    print(dim("  Fetching audit log via MPP..."))
    print()

    data = _tempo_request("GET", f"{args.url}/audit")

    entries = data.get("audit_log", data.get("entries", []))
    agent = data.get("agent", "unknown")

    kv("Agent", bold(agent))
    kv("Entries", bold(str(len(entries))))
    print()

    if not entries:
        print(dim("  No audit entries yet."))
    else:
        for i, entry in enumerate(entries, 1):
            ts = entry.get("timestamp", "")
            action = entry.get("action", entry.get("type", "unknown"))
            amount = entry.get("amount", "")
            merchant = entry.get("merchant", "")
            result = entry.get("result", entry.get("verdict", ""))

            if isinstance(result, dict):
                allowed = result.get("allowed", False)
                result_str = green("PASS") if allowed else red("FAIL")
            elif isinstance(result, str):
                result_str = green(result) if result.upper() in ("PASS", "ALLOWED", "TRUE") else red(result)
            else:
                result_str = dim("?")

            num = dim(f"  {i:>3}.")
            print(f"{num} {result_str}  ${amount:<10}  {merchant:<25}  {dim(str(ts))}")

    if "payment" in data:
        print_payment_info(data["payment"])


def cmd_health(args):
    """Health check (free, no payment required)."""
    banner()
    divider("HEALTH CHECK")
    print()

    data = _curl_request(f"{args.url}/health")

    status = data.get("status", "unknown")
    agents = data.get("agents_tracked", 0)
    mandates = data.get("mandates_active", 0)

    if status == "ok":
        print(f"  {CHECK}  Status: {bg_green(' OK ')}")
    else:
        print(f"  {CROSS}  Status: {bg_red(f' {status.upper()} ')}")

    print()
    kv("Agents Tracked", bold(str(agents)))
    kv("Active Mandates", bold(str(mandates)))
    kv("Guard URL", dim(args.url))
    kv("Endpoint", dim("/health (free)"))
    divider()
    print()


# ──────────────────────────────────────────────────────────────────────────────
# Argument parser
# ──────────────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sardis-guard",
        description=textwrap.dedent("""\
            Sardis Guard CLI — MPP Policy Firewall for AI Agent Payments.

            Evaluate, simulate, and manage spending policies for AI agents
            through the Machine Payments Protocol (MPP).
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              %(prog)s evaluate --amount 1.50 --merchant perplexity.ai
              %(prog)s simulate --amount 100 --merchant gambling.com
              %(prog)s mandate
              %(prog)s mandate --update --max-per-tx 10 --max-daily 200 --block-merchant gambling.com
              %(prog)s stats
              %(prog)s audit
              %(prog)s health
        """),
    )

    parser.add_argument(
        "--url",
        default=os.environ.get("SARDIS_GUARD_URL", DEFAULT_GUARD_URL),
        help="Sardis Guard server URL (default: $SARDIS_GUARD_URL or ngrok URL)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── evaluate ──
    p_eval = sub.add_parser("evaluate", help="Evaluate a payment against the policy engine ($0.001)")
    p_eval.add_argument("--amount", required=True, type=float, help="Payment amount (e.g. 1.50)")
    p_eval.add_argument("--merchant", required=True, help="Merchant identifier (e.g. perplexity.ai)")
    p_eval.add_argument("--currency", default="USDC", help="Token (default: USDC)")
    p_eval.add_argument("--network", default="tempo", help="Chain (default: tempo)")
    p_eval.add_argument("--category", default="general", help="Spending category")
    p_eval.add_argument("--memo", default=None, help="Transaction memo")
    p_eval.set_defaults(func=cmd_evaluate)

    # ── simulate ──
    p_sim = sub.add_parser("simulate", help="Dry-run policy evaluation ($0.0005)")
    p_sim.add_argument("--amount", required=True, type=float, help="Payment amount")
    p_sim.add_argument("--merchant", required=True, help="Merchant identifier")
    p_sim.add_argument("--currency", default="USDC", help="Token (default: USDC)")
    p_sim.add_argument("--network", default="tempo", help="Chain (default: tempo)")
    p_sim.add_argument("--category", default="general", help="Spending category")
    p_sim.add_argument("--memo", default=None, help="Transaction memo")
    p_sim.set_defaults(func=cmd_simulate)

    # ── mandate ──
    p_man = sub.add_parser("mandate", help="View or update spending mandate")
    p_man.add_argument("--update", action="store_true", help="Update mandate (PUT instead of GET)")
    p_man.add_argument("--max-per-tx", type=float, default=None, help="Max amount per transaction")
    p_man.add_argument("--max-daily", type=float, default=None, help="Max daily spending limit")
    p_man.add_argument("--allowed-merchant", action="append", default=[], help="Add to merchant allowlist (repeatable)")
    p_man.add_argument("--block-merchant", action="append", default=[], help="Add to merchant blocklist (repeatable)")
    p_man.add_argument("--allowed-chain", action="append", default=[], help="Allowed chains (repeatable)")
    p_man.add_argument("--allowed-currency", action="append", default=[], help="Allowed currencies (repeatable)")
    p_man.add_argument("--require-memo", type=bool, default=None, help="Require memo on payments")
    p_man.add_argument("--cooldown", type=int, default=None, help="Seconds between payments")
    p_man.set_defaults(func=cmd_mandate)

    # ── stats ──
    p_stats = sub.add_parser("stats", help="View agent spending stats ($0.0001)")
    p_stats.set_defaults(func=cmd_stats)

    # ── audit ──
    p_audit = sub.add_parser("audit", help="View full audit trail ($0.001)")
    p_audit.set_defaults(func=cmd_audit)

    # ── health ──
    p_health = sub.add_parser("health", help="Health check (free)")
    p_health.set_defaults(func=cmd_health)

    return parser


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print()
        print(dim("  Interrupted."))
        sys.exit(130)
    except Exception as e:
        print()
        print(red(f"  Error: {e}"))
        sys.exit(1)


if __name__ == "__main__":
    main()
