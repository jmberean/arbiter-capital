import sqlite3
import time
import json
import os
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich import box

DB_PATH = os.path.join(os.path.dirname(__file__), "axl_network.db")
console = Console()

def get_latest_messages(limit=10):
    if not os.path.exists(DB_PATH):
        return []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, topic, payload, sender, timestamp FROM messages ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return cursor.fetchall()
    except Exception:
        return []

def generate_dashboard():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main")
    )
    
    # Header
    layout["header"].update(Panel("Arbiter Capital - AXL Network Monitor", style="bold white on blue"))
    
    # Table
    table = Table(title="Live AXL Message Stream", box=box.ROUNDED, expand=True)
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Time", style="magenta")
    table.add_column("Topic", style="yellow")
    table.add_column("Sender", style="green")
    table.add_column("Summary", style="white")
    
    messages = get_latest_messages(15)
    for msg in reversed(messages):
        payload = json.loads(msg["payload"])
        
        # Create a short summary based on topic
        summary = ""
        topic = msg["topic"]
        if topic == "MARKET_DATA":
            summary = f"Scenario: {payload.get('market_sentiment', 'N/A')}"
        elif topic == "PROPOSALS":
            summary = f"Prop: {payload.get('proposal_id')} ({payload.get('action')})"
        elif topic == "PROPOSAL_EVALUATIONS":
            summary = f"Result: {payload.get('consensus_status')} - {payload.get('rationale')[:50]}..."
        elif topic == "FIREWALL_CLEARED":
            summary = f"🔥 FIREWALL PASSED: {payload.get('proposal_id')}"
        elif topic == "CONSENSUS_SIGNATURES":
            summary = f"✍️ SIGNATURE from {payload.get('signer_id')}"
        elif topic == "EXECUTION_SUCCESS":
            summary = f"✅ EXECUTED: {payload.get('tx_hash')[:16]}..."
        else:
            summary = str(payload)[:60] + "..."
            
        timestamp = time.strftime("%H:%M:%S", time.localtime(msg["timestamp"]))
        table.add_row(str(msg["id"]), timestamp, topic, msg["sender"], summary)
        
    layout["main"].update(table)
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
