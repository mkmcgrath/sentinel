#!/usr/bin/env python3
"""
Sentinel TUI Dashboard
Terminal-based monitoring dashboard using Textual
"""
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

import httpx
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, DataTable, Static, Button, Label
from textual.reactive import reactive
from textual.timer import Timer
from rich.text import Text


class NodeStatus(Static):
    """Widget to display status of all nodes"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nodes = []

    def update_nodes(self, nodes: List[Dict[str, Any]]):
        """Update the nodes data"""
        self.nodes = nodes
        self.update_display()

    def update_display(self):
        """Update the display with current node data"""
        if not self.nodes:
            self.update("[dim]No nodes reporting[/dim]")
            return

        # Build table content
        lines = []
        lines.append("[bold cyan]NODE OVERVIEW[/bold cyan]")
        lines.append("")

        # Header
        lines.append(
            f"{'Node':<15} {'Status':<10} {'CPU':<8} {'MEM':<8} {'DISK':<8} {'Last Seen':<15}"
        )
        lines.append("-" * 80)

        # Nodes
        for node in self.nodes:
            node_id = node.get('node_id', 'unknown')[:14]
            status = node.get('status', 'unknown')
            cpu = node.get('last_cpu_percent')
            mem = node.get('last_memory_percent')
            disk = node.get('last_disk_percent')
            last_seen = node.get('last_seen', '')

            # Format status with color
            if status == 'online':
                status_str = f"[green]{status:<10}[/green]"
            elif status == 'offline':
                status_str = f"[red]{status:<10}[/red]"
            else:
                status_str = f"[yellow]{status:<10}[/yellow]"

            # Format metrics
            cpu_str = f"{cpu:>5.1f}%" if cpu is not None else "--"
            mem_str = f"{mem:>5.1f}%" if mem is not None else "--"
            disk_str = f"{disk:>5.1f}%" if disk is not None else "--"

            # Format last seen
            if last_seen:
                try:
                    dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                    delta = datetime.now(dt.tzinfo) - dt
                    if delta.total_seconds() < 60:
                        last_seen_str = f"{int(delta.total_seconds())}s ago"
                    elif delta.total_seconds() < 3600:
                        last_seen_str = f"{int(delta.total_seconds() / 60)}m ago"
                    else:
                        last_seen_str = f"{int(delta.total_seconds() / 3600)}h ago"
                except:
                    last_seen_str = "unknown"
            else:
                last_seen_str = "never"

            lines.append(
                f"{node_id:<15} {status_str} {cpu_str:<8} {mem_str:<8} {disk_str:<8} {last_seen_str:<15}"
            )

        self.update("\n".join(lines))


class AlertsWidget(Static):
    """Widget to display active alerts"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.alerts = []

    def update_alerts(self, alerts: List[Dict[str, Any]]):
        """Update the alerts data"""
        self.alerts = alerts
        self.update_display()

    def update_display(self):
        """Update the display with current alerts"""
        if not self.alerts:
            self.update("[dim]No active alerts[/dim]")
            return

        lines = []
        lines.append("[bold yellow]ACTIVE ALERTS[/bold yellow]")
        lines.append("")

        for alert in self.alerts[:5]:  # Show max 5 alerts
            node_id = alert.get('node_id', 'N/A')
            alert_name = alert.get('alert_name', 'Unknown')
            value = alert.get('value', 0)
            triggered = alert.get('triggered', '')

            try:
                dt = datetime.fromisoformat(triggered.replace('Z', '+00:00'))
                delta = datetime.now(dt.tzinfo) - dt
                if delta.total_seconds() < 60:
                    time_str = f"{int(delta.total_seconds())}s ago"
                elif delta.total_seconds() < 3600:
                    time_str = f"{int(delta.total_seconds() / 60)}m ago"
                else:
                    time_str = f"{int(delta.total_seconds() / 3600)}h ago"
            except:
                time_str = "unknown"

            lines.append(f"[red]![/red] {node_id}: {alert_name} (value: {value:.1f}) - {time_str}")

        self.update("\n".join(lines))


class StatsWidget(Static):
    """Widget to display overall statistics"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stats = {}

    def update_stats(self, stats: Dict[str, Any]):
        """Update the statistics"""
        self.stats = stats
        self.update_display()

    def update_display(self):
        """Update the display with statistics"""
        total = self.stats.get('total_nodes', 0)
        online = self.stats.get('online_nodes', 0)
        metrics = self.stats.get('total_metrics', 0)

        content = f"""[bold cyan]STATISTICS[/bold cyan]

Total Nodes:    {total}
Online Nodes:   [green]{online}[/green]
Total Metrics:  {metrics:,}
"""
        self.update(content)


class SentinelDashboard(App):
    """Sentinel monitoring dashboard TUI application"""

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        height: 100%;
        padding: 1;
    }

    #node-status {
        height: 60%;
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }

    #bottom-container {
        height: 35%;
        layout: horizontal;
    }

    #alerts {
        width: 70%;
        border: solid yellow;
        padding: 1;
        margin-right: 1;
    }

    #stats {
        width: 30%;
        border: solid cyan;
        padding: 1;
    }

    Button {
        margin: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("d", "toggle_dark", "Toggle Dark Mode"),
    ]

    def __init__(self, server_url: str):
        super().__init__()
        self.server_url = server_url.rstrip('/')
        self.auto_refresh_timer: Optional[Timer] = None

    def compose(self) -> ComposeResult:
        """Create child widgets"""
        yield Header()
        with Container(id="main-container"):
            yield NodeStatus(id="node-status")
            with Horizontal(id="bottom-container"):
                yield AlertsWidget(id="alerts")
                yield StatsWidget(id="stats")
        yield Footer()

    def on_mount(self) -> None:
        """Called when app is mounted"""
        self.title = "Sentinel Dashboard"
        self.sub_title = f"Monitoring {self.server_url}"

        # Start auto-refresh timer (every 5 seconds)
        self.auto_refresh_timer = self.set_interval(5.0, self.refresh_data)

        # Initial data load
        self.refresh_data()

    def action_refresh(self) -> None:
        """Manual refresh action"""
        self.refresh_data()

    def action_toggle_dark(self) -> None:
        """Toggle dark mode"""
        self.dark = not self.dark

    def refresh_data(self) -> None:
        """Fetch fresh data from the server"""
        try:
            # Fetch nodes
            response = httpx.get(f"{self.server_url}/api/v1/nodes", timeout=5.0)
            if response.status_code == 200:
                nodes = response.json()
                self.query_one("#node-status", NodeStatus).update_nodes(nodes)

            # Fetch health/stats
            response = httpx.get(f"{self.server_url}/api/v1/health", timeout=5.0)
            if response.status_code == 200:
                health = response.json()
                stats = health.get('statistics', {})
                self.query_one("#stats", StatsWidget).update_stats(stats)

            # Fetch active alerts
            response = httpx.get(f"{self.server_url}/api/v1/alerts/events/active", timeout=5.0)
            if response.status_code == 200:
                alerts = response.json()
                self.query_one("#alerts", AlertsWidget).update_alerts(alerts)

        except httpx.RequestError as e:
            self.notify(f"Error connecting to server: {e}", severity="error")
        except Exception as e:
            self.notify(f"Error refreshing data: {e}", severity="error")


def main():
    """Main entry point"""
    # Get server URL from command line or environment
    import os

    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    else:
        server_url = os.environ.get('SENTINEL_SERVER_URL', 'http://localhost:8080')

    print(f"Connecting to Sentinel server at: {server_url}")

    app = SentinelDashboard(server_url)
    app.run()


if __name__ == "__main__":
    main()
