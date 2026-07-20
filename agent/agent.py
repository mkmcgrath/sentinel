#!/usr/bin/env python3
"""
Sentinel Agent - Lightweight monitoring agent
Collects system metrics and reports to central server
"""
import sys
import time
import json
import socket
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

try:
    import yaml
except ImportError:
    print("PyYAML not found, falling back to minimal config")
    yaml = None

from collectors.cpu import CPUCollector
from collectors.memory import MemoryCollector
from collectors.disk import DiskCollector
from collectors.network import NetworkCollector
from collectors.services import ServicesCollector
from collectors.docker import DockerCollector


class SentinelAgent:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()

        # Initialize collectors
        self.cpu_collector = CPUCollector()
        self.memory_collector = MemoryCollector()
        self.disk_collector = DiskCollector()
        self.network_collector = NetworkCollector()
        self.services_collector = ServicesCollector(
            services_to_monitor=self.config.get('services', []),
            ports_to_monitor=self.config.get('ports', [])
        )
        self.docker_collector = DockerCollector()

        self.node_id = self.config.get('node_id', socket.gethostname())
        self.hostname = self.config.get('hostname') or socket.gethostname()

        self.logger.info(f"Sentinel Agent initialized for node: {self.node_id}")

    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        config_file = Path(config_path)

        # Default configuration
        default_config = {
            'node_id': socket.gethostname(),
            'hostname': socket.gethostname(),
            'server_url': 'http://localhost:8080',
            'api_version': 'v1',
            'report_interval': 10,
            'services': [],
            'ports': [],
            'max_retries': 3,
            'retry_delay': 5,
            'log_level': 'INFO',
            'log_file': None
        }

        if not config_file.exists():
            print(f"Config file not found: {config_path}, using defaults")
            return default_config

        if yaml is None:
            print("PyYAML not available, using default config")
            return default_config

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception as e:
            print(f"Error loading config: {e}, using defaults")
            return default_config

    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config.get('log_level', 'INFO'))
        log_file = self.config.get('log_file')

        handlers = [logging.StreamHandler(sys.stdout)]

        if log_file:
            try:
                handlers.append(logging.FileHandler(log_file))
            except (PermissionError, OSError) as e:
                print(f"Cannot write to log file {log_file}: {e}")

        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )

        self.logger = logging.getLogger('SentinelAgent')

    def collect_metrics(self):
        """Collect all metrics from all collectors"""
        try:
            metrics = {
                "cpu": self.cpu_collector.collect(),
                "memory": self.memory_collector.collect(),
                "disk": self.disk_collector.collect(),
                "network": self.network_collector.collect(),
                "services": self.services_collector.collect(),
                "containers": self.docker_collector.collect()
            }
            return metrics
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            return None

    def create_payload(self, metrics):
        """Create the JSON payload to send to server"""
        return {
            "node_id": self.node_id,
            "hostname": self.hostname,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics
        }

    def send_metrics(self, payload):
        """Send metrics to the central server"""
        api_version = self.config.get('api_version', 'v1')
        url = f"{self.config['server_url']}/api/{api_version}/metrics"

        try:
            data = json.dumps(payload).encode('utf-8')
            req = Request(
                url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )

            with urlopen(req, timeout=10) as response:
                if response.status == 200:
                    self.logger.debug(f"Metrics sent successfully to {url}")
                    return True
                else:
                    self.logger.warning(f"Server returned status {response.status}")
                    return False

        except HTTPError as e:
            self.logger.error(f"HTTP error sending metrics: {e.code} - {e.reason}")
            return False
        except URLError as e:
            self.logger.error(f"Network error sending metrics: {e.reason}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending metrics: {e}")
            return False

    def run(self):
        """Main agent loop"""
        self.logger.info("Starting Sentinel Agent...")

        # Do an initial collection to prime the CPU collector
        self.cpu_collector.collect()
        time.sleep(1)

        while True:
            try:
                # Collect metrics
                metrics = self.collect_metrics()

                if metrics is None:
                    self.logger.warning("Failed to collect metrics, skipping this cycle")
                    time.sleep(self.config['report_interval'])
                    continue

                # Create payload
                payload = self.create_payload(metrics)

                # Send to server with retry logic
                success = False
                for attempt in range(self.config['max_retries']):
                    if self.send_metrics(payload):
                        success = True
                        break
                    else:
                        if attempt < self.config['max_retries'] - 1:
                            self.logger.info(
                                f"Retrying in {self.config['retry_delay']} seconds... "
                                f"(attempt {attempt + 1}/{self.config['max_retries']})"
                            )
                            time.sleep(self.config['retry_delay'])

                if not success:
                    self.logger.error("Failed to send metrics after all retries")

                # Wait for next interval
                time.sleep(self.config['report_interval'])

            except KeyboardInterrupt:
                self.logger.info("Received shutdown signal, stopping agent...")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(self.config['report_interval'])


if __name__ == "__main__":
    # Allow config path to be specified as command line argument
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"

    agent = SentinelAgent(config_path)
    agent.run()
