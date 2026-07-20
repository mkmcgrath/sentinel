"""
Demo mode: generates synthetic metrics for fake nodes so the UI can be
explored without a real homelab. Enabled via the DEMO_MODE env var.
"""
import asyncio
import logging
import math
import os
import random
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from db import SessionLocal, Node, Alert, Metric
from routes.metrics import _evaluate_alerts

logger = logging.getLogger(__name__)

DEMO_NODE_COUNT = int(os.environ.get("DEMO_NODE_COUNT", "3"))
DEMO_INTERVAL_SECONDS = int(os.environ.get("DEMO_INTERVAL_SECONDS", "10"))

ALERT_NODE_ID = "demo-01"
ALERT_CYCLE_SECONDS = 90  # time for one full trigger -> resolve -> trigger sweep


class _NodeState:
    """Tracks slowly-drifting baseline values for one synthetic node"""

    def __init__(self, node_id):
        self.node_id = node_id
        self.cpu_percent = random.uniform(5, 40)
        self.mem_percent = random.uniform(30, 60)
        self.disk_percent = random.uniform(20, 70)
        self.bytes_in = random.randint(10_000_000, 500_000_000)
        self.bytes_out = random.randint(10_000_000, 500_000_000)

    @staticmethod
    def _walk(value, low, high, step=2.0):
        value += random.uniform(-step, step)
        return max(low, min(high, value))

    def next_metrics(self, elapsed_seconds):
        if self.node_id == ALERT_NODE_ID:
            # Sine wave sweeping through the alert threshold so the demo
            # shows a full trigger/resolve alert lifecycle on repeat.
            phase = (elapsed_seconds % ALERT_CYCLE_SECONDS) / ALERT_CYCLE_SECONDS
            self.cpu_percent = 45 + 50 * math.sin(phase * 2 * math.pi) ** 2
        else:
            self.cpu_percent = self._walk(self.cpu_percent, 1, 95)

        self.mem_percent = self._walk(self.mem_percent, 15, 90)
        self.disk_percent = self._walk(self.disk_percent, 10, 95, step=0.3)
        self.bytes_in += random.randint(1_000, 2_000_000)
        self.bytes_out += random.randint(1_000, 2_000_000)

        mem_total_mb = 8192
        disk_total_gb = 100

        return {
            "cpu": {
                "usage_percent": round(self.cpu_percent, 2),
                "load_1m": round(self.cpu_percent / 100 * 4, 2),
                "load_5m": round(self.cpu_percent / 100 * 3, 2),
                "load_15m": round(self.cpu_percent / 100 * 2, 2),
            },
            "memory": {
                "total_mb": mem_total_mb,
                "used_mb": round(mem_total_mb * self.mem_percent / 100, 2),
                "available_mb": round(mem_total_mb * (1 - self.mem_percent / 100), 2),
                "percent": round(self.mem_percent, 2),
                "swap_total_mb": 2048,
                "swap_used_mb": round(random.uniform(0, 200), 2),
            },
            "disk": {
                "partitions": [{
                    "mount": "/",
                    "device": "/dev/sda1",
                    "total_gb": disk_total_gb,
                    "used_gb": round(disk_total_gb * self.disk_percent / 100, 2),
                    "free_gb": round(disk_total_gb * (1 - self.disk_percent / 100), 2),
                    "percent": round(self.disk_percent, 2),
                }],
                "io": {},
            },
            "network": {
                "interfaces": {
                    "eth0": {
                        "bytes_in": self.bytes_in,
                        "bytes_out": self.bytes_out,
                        "packets_in": self.bytes_in // 512,
                        "packets_out": self.bytes_out // 512,
                        "errors_in": 0,
                        "errors_out": 0,
                        "drops_in": 0,
                        "drops_out": 0,
                    }
                },
                "gateway_latency_ms": round(random.uniform(0.3, 3.0), 2),
            },
            "services": [
                {"name": "sshd", "status": "active", "active": True},
                {"name": "docker", "status": "active", "active": True},
            ],
            "containers": [],
        }


class DemoDataGenerator:
    def __init__(self, node_count=DEMO_NODE_COUNT):
        self.node_ids = [f"demo-{i:02d}" for i in range(1, node_count + 1)]
        self.states = {node_id: _NodeState(node_id) for node_id in self.node_ids}
        self.start_time = time.monotonic()

    def ensure_nodes_and_alert(self, db: Session):
        for node_id in self.node_ids:
            node = db.query(Node).filter(Node.node_id == node_id).first()
            if not node:
                db.add(Node(node_id=node_id, hostname=node_id, status="online"))

        existing_alert = db.query(Alert).filter(
            Alert.node_id == ALERT_NODE_ID, Alert.name == "Demo High CPU"
        ).first()
        if not existing_alert:
            db.add(Alert(
                node_id=ALERT_NODE_ID,
                name="Demo High CPU",
                metric="cpu.usage_percent",
                operator="gt",
                threshold=80.0,
                active=True,
                description="Auto-created by demo mode to showcase the alert lifecycle",
            ))

        db.commit()

    def tick(self, db: Session):
        elapsed = time.monotonic() - self.start_time
        timestamp = datetime.now(timezone.utc)

        for node_id in self.node_ids:
            metrics = self.states[node_id].next_metrics(elapsed)

            node = db.query(Node).filter(Node.node_id == node_id).first()
            node.last_seen = timestamp

            for metric_type, metric_data in metrics.items():
                db.add(Metric(
                    node_id=node_id,
                    timestamp=timestamp,
                    metric_type=metric_type,
                    data=metric_data,
                ))

            _evaluate_alerts(db, node_id, metrics, timestamp)

        db.commit()


async def run_demo_loop():
    """Background task: periodically generates synthetic data for fake nodes."""
    generator = DemoDataGenerator()

    db = SessionLocal()
    try:
        generator.ensure_nodes_and_alert(db)
    finally:
        db.close()

    logger.info(
        f"Demo mode active: simulating {len(generator.node_ids)} nodes "
        f"every {DEMO_INTERVAL_SECONDS}s (alert lifecycle on {ALERT_NODE_ID})"
    )

    while True:
        db = SessionLocal()
        try:
            generator.tick(db)
        except Exception as e:
            logger.error(f"Demo mode tick failed: {e}")
            db.rollback()
        finally:
            db.close()

        await asyncio.sleep(DEMO_INTERVAL_SECONDS)
