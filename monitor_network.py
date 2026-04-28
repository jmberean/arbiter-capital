import sqlite3
import time
import json
import os
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich import box

DB_PATH = os.path.join(os.path.dirname(__file__), "axl_network.db")
STORAGE_PATH = os.path.join(os.path.dirname(__file__), "0g_storage")
console = Console()


def _db_query(sql: str, params: tuple = ()) -> list:
    if not os.path.exists(DB_PATH):
        return []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(sql, params).fetchall()
    except Exception:
        return []


# ── Pane 1: AXL stream ──────────────────────────────────────────────────────

def _axl_table() -> Table:
    table = Table(title="AXL Stream", box=box.SIMPLE_HEAD, expand=True, show_lines=False)
    table.add_column("ID", justify="right", style="cyan", no_wrap=True, width=6)
    table.add_column("Time", style="magenta", width=8)
    table.add_column("Topic", style="yellow", width=22)
    table.add_column("Sender", style="green", width=18)
    table.add_column("Summary", style="white")

    rows = _db_query(
        "SELECT id, topic, payload, sender, timestamp FROM messages ORDER BY id DESC LIMIT 12"
    )
    distinct_senders_60s = len({
        r["sender"] for r in _db_query(
            "SELECT DISTINCT sender FROM messages WHERE timestamp > ?",
            (time.time() - 60,)
        )
    })

    for msg in reversed(rows):
        payload = json.loads(msg["payload"])
        topic = msg["topic"]
        if topic == "MARKET_DATA":
            summary = f"sentiment={payload.get('market_sentiment', '?')}"
        elif topic == "PROPOSALS":
            summary = f"{payload.get('proposal_id')} {payload.get('action')}"
        elif topic == "PROPOSAL_EVALUATIONS":
            status = payload.get("consensus_status", "?")
            summary = f"{status} — {str(payload.get('rationale', ''))[:40]}"
        elif topic == "FIREWALL_CLEARED":
            summary = f"PASSED: {payload.get('proposal_id')}"
        elif topic == "CONSENSUS_SIGNATURES":
            summary = f"sig from {payload.get('signer_id', '?')}"
        elif topic == "EXECUTION_SUCCESS":
            tx = str(payload.get("tx_hash", ""))
            summary = f"tx={tx[:16]}…"
        elif topic == "HEARTBEAT":
            summary = f"daemon={payload.get('daemon_id', '?')}"
        elif topic == "ATTACK_REJECTED":
            summary = f"[red]REJECTED: {payload.get('attack_kind', '?')}[/red]"
        else:
            summary = str(payload)[:55] + "…"
        ts = time.strftime("%H:%M:%S", time.localtime(msg["timestamp"]))
        table.add_row(str(msg["id"]), ts, topic, msg["sender"], summary)

    table.caption = f"Distinct senders (60s): {distinct_senders_60s}"
    return table


# ── Pane 2: Treasury state ───────────────────────────────────────────────────

def _treasury_panel() -> Panel:
    rows = _db_query(
        "SELECT payload FROM messages WHERE topic='EXECUTION_SUCCESS' ORDER BY id DESC LIMIT 3"
    )
    lines: list[str] = []
    for (r,) in [(msg["payload"],) for msg in rows]:
        d = json.loads(r)
        lines.append(f"tx={str(d.get('tx_hash', ''))[:20]}…  nonce={d.get('safe_nonce', '?')}")

    sbt_rows = _db_query(
        "SELECT payload FROM messages WHERE topic='SBT_MINTED' ORDER BY id DESC LIMIT 3"
    )
    sbt_lines = [f"SBT token_id={json.loads(m['payload']).get('token_id', '?')}" for m in sbt_rows]

    nonce_rows = _db_query(
        "SELECT payload FROM messages WHERE topic='EXECUTION_SUCCESS' ORDER BY id DESC LIMIT 1"
    )
    nonce = json.loads(nonce_rows[0]["payload"]).get("safe_nonce", "?") if nonce_rows else "?"

    body = "\n".join(
        ["[bold]Recent executions:[/bold]"] + (lines or ["  (none yet)"]) +
        ["", "[bold]SBT mints:[/bold]"] + (sbt_lines or ["  (none yet)"]) +
        [f"", f"Safe nonce (last): {nonce}"]
    )
    return Panel(body, title="Treasury State", border_style="blue")


# ── Pane 3: Audit chain tail ─────────────────────────────────────────────────

def _audit_panel() -> Panel:
    lines: list[str] = []
    try:
        from memory.audit_chain import AuditChainHead
        head = AuditChainHead().head
        if not head:
            raise ValueError("no head")
        lines.append(f"[bold]Head:[/bold] {str(head)[:24]}…")
        cur = head
        count = 0
        while cur and count < 5:
            local_path = os.path.join(STORAGE_PATH, f"{cur}.json")
            if os.path.exists(local_path):
                with open(local_path) as f:
                    receipt = json.load(f)
                rtype = receipt.get("receipt_type", "?")
                rid = str(receipt.get("receipt_id", ""))[:10]
                prev = str(receipt.get("prev_0g_tx_hash") or "")
                lines.append(f"  {rtype} id={rid}  prev={prev[:12] + '…' if prev else 'genesis'}")
                cur = receipt.get("prev_0g_tx_hash")
            else:
                lines.append(f"  (on-chain: {str(cur)[:16]}…)")
                break
            count += 1
    except Exception as e:
        lines = [f"[dim]{e}[/dim]"]

    body = "\n".join(lines) if lines else "(no receipts)"
    return Panel(body, title="Audit Chain Tail", border_style="green")


# ── Pane 4: Watchdog evidence ────────────────────────────────────────────────

def _watchdog_panel() -> Panel:
    rows = _db_query(
        "SELECT payload, timestamp FROM messages WHERE topic='ATTACK_REJECTED' ORDER BY id DESC LIMIT 8"
    )
    lines: list[str] = []
    for msg in rows:
        d = json.loads(msg["payload"])
        ts = time.strftime("%H:%M:%S", time.localtime(msg["timestamp"]))
        kind = d.get("attack_kind", "?")
        defender = d.get("detected_by", d.get("defender", "?"))
        lines.append(f"[red]{ts}[/red]  [{kind}]  defender={defender}")
    body = "\n".join(lines) if lines else "[dim](no attacks recorded)[/dim]"
    return Panel(body, title="Watchdog Evidence", border_style="red")


# ── Layout ────────────────────────────────────────────────────────────────────

def generate_dashboard() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="top"),
        Layout(name="bottom"),
    )
    layout["top"].split_row(
        Layout(name="axl", ratio=2),
        Layout(name="treasury", ratio=1),
    )
    layout["bottom"].split_row(
        Layout(name="audit", ratio=1),
        Layout(name="watchdog", ratio=1),
    )

    layout["header"].update(
        Panel("Arbiter Capital — God View Monitor", style="bold white on dark_blue")
    )
    layout["axl"].update(_axl_table())
    layout["treasury"].update(_treasury_panel())
    layout["audit"].update(_audit_panel())
    layout["watchdog"].update(_watchdog_panel())
    return layout


def run_monitor():
    with Live(generate_dashboard(), refresh_per_second=1, screen=True) as live:
        while True:
            time.sleep(1)
            live.update(generate_dashboard())


if __name__ == "__main__":
    try:
        run_monitor()
    except KeyboardInterrupt:
        pass
