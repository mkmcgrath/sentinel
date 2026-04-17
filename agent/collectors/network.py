"""network metric collector - reads /proc/net/dev and measures latency"""

import subprocess
import re

class NetworkCollector:
    def __init__(self):
        self.prev_stats = {}

    def collect(self):
        """Collect network metrics"""
        interfaces = self._get_network_stats()
        latency = self._measure_latency()

        return {
            "interfaces": interfaces,
            "gateway_latency_ms": latency
        }

    def _get_network_stats(self):
        """read network interface statistics from /proc/net/dev"""
        interfaces = {}

        try:
            with open('/proc/net/dev', 'r') as f:
                # skip header lines
                f.readline()
                f.readline()

                for line in f:
                    parts = line.split(':')
                    if len(parts) != 2:
                        continue

                    interface = parts[0].strip()
                    stats = parts[1].split()

                    if len(stats) < 16:
                        continue

                    # skip loopback
                    if interface == 'lo':
                        continue

                    bytes_in = int(stats[0])
                    packets_in = int(stats[1])
                    errors_in = int(stats[2])
                    drops_in = int(stats[3])

                    bytes_out = int(stats[8])
                    packets_out = int(stats[9])
                    errors_out = int(stats[10])
                    drops_out = int(stats[11])

                    interfaces[interface] = {
                        "bytes_in": bytes_in,
                        "bytes_out": bytes_out,
                        "packets_in": packets_in,
                        "packets_out": packets_out,
                        "errors_in": errors_in,
                        "errors_out": errors_out,
                        "drops_in": drops_in,
                        "drops_out": drops_out
                    }

        except (IOError, ValueError, IndexError) as e:
            print(f"Error reading network stats: {e}")

        return interfaces

    def _measure_latency(self):
        """Ping the default gateway to measure network latency"""
        try:
            # get default gateway
            with open('/proc/net/route', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3 and parts[1] == '00000000':
                        # gateway is in hex, convert to IP
                        gateway_hex = parts[2]
                        gateway_ip = '.'.join([
                            str(int(gateway_hex[i:i+2], 16))
                            for i in range(6, -1, -2)
                        ])

                        # ping the gateway once
                        result = subprocess.run(
                            ['ping', '-c', '1', '-W', '1', gateway_ip],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )

                        if result.returncode == 0:
                            # extract time from ping output
                            match = re.search(r'time=(\d+\.?\d*)', result.stdout)
                            if match:
                                return round(float(match.group(1)), 2)

                        break

        except (IOError, ValueError, subprocess.TimeoutExpired) as e:
            print(f"Error measuring latency: {e}")

        return None




