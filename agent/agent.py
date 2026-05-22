#!/usr/bin/env python3
"""
Sentinel Agent - lightweight monitoring agent
collects system metrics and reports to central server
"""
import sys
import time
import json
import logging
import socket
from pathlib import Path
from datetime import datetime, timezone
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


class SentinelAgent:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()

        # initialize collectors
        # These modules use /proc and stdlib to keep the agent lightweight (Phase 3.2)
        self.cpu_collector = CPUCollector()
        self.memory_collector = MemoryCollector()
        self.disk_collector = DiskCollector()
        self.network_collector = NetworkCollector()
        self.services_collector = ServicesCollector(
            services_to_monitor=self.config.get('services', []),
            ports_to_monitor=self.config.get('ports', [])
        )

        self.node_id = self.config.get('node_id', socket.gethostname())
        self.hostname = self.config.get('hostname') or socket.gethostname()

        self.logger.info(f"Sentinel Agent initialized for node: {self.node_id}")

    def _load_config(self, config_path):
        """load configuration from YAML file"""
        config_file = Path(config_path)

        # default configuration
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
                # merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception as e:
            print(f"Error loading config: {e}, using defaults")
            return default_config

    def _setup_logging(self):
        """setup logging configuration"""
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
        """collect all metrics from all collectors"""
        try:
            # Aggregate data from specialized collectors (Phase 3.3)
            metrics = {
                "cpu": self.cpu_collector.collect(),
                "memory": self.memory_collector.collect(),
                "disk": self.disk_collector.collect(),
                "network": self.network_collector.collect(),
                "services": self.services_collector.collect()
            }
            return metrics
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            return None

    def send_metrics(self, payload):
        """send metrics to the central server"""
        api_version = self.config.get('api_version', 'v1')
        url = f"{self.config['server_url']}/api/{api_version}/metrics"

        try:
            data = json.dumps(payload).encode('utf-8')
            req = Request(
                url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )

            # Use stdlib urllib to avoid external dependencies like 'requests'
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
        """main agent loop"""
        self.logger.info(f"Starting Sentinel Agent loop (interval: {self.config['report_interval']}s)...")
        
        while True:
            try:
                # 1. Collect
                metrics = self.collect_metrics()
                
                if metrics:
                    # 2. Prepare Payload (Phase 3.3)
                    payload = {
                        "node_id": self.node_id,
                        "hostname": self.hostname,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "metrics": metrics
                    }
                    
                    # 3. report
                    self.send_metrics(payload)
                
                # 4. Wait
                time.sleep(self.config['report_interval'])
                
            except KeyboardInterrupt:
                self.logger.info("Agent stopping...")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(self.config['retry_delay'])

if __name__ == "__main__":
    agent = SentinelAgent()
    agent.run()
