"""service status collector - checks systemd services and listening ports"""
import subprocess
import socket


class ServicesCollector:
    def __init__(self, services_to_monitor=None, ports_to_monitor=None):
        """
        initialize the services collector

        args:
            services_to_monitor: List of systemd service names to check
            ports_to_monitor: List of ports to check if they're listening
        """
        self.services_to_monitor = services_to_monitor or []
        self.ports_to_monitor = ports_to_monitor or []

    def collect(self):
        """collect service status metrics"""
        service_statuses = self._check_services()
        port_statuses = self._check_ports()

        return {
            "services": service_statuses,
            "ports": port_statuses
        }

    def _check_services(self):
        """check status of configured systemd services"""
        statuses = []

        for service in self.services_to_monitor:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', service],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                status = result.stdout.strip()

                statuses.append({
                    "name": service,
                    "status": status,
                    "active": status == "active"
                })

            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                print(f"error checking service {service}: {e}")
                statuses.append({
                    "name": service,
                    "status": "unknown",
                    "active": False
                })

        return statuses

    def _check_ports(self):
        """check if configured ports are listening"""
        statuses = []

        for port in self.ports_to_monitor:
            listening = self._is_port_listening(port)

            statuses.append({
                "port": port,
                "listening": listening
            })

        return statuses

    def _is_port_listening(self, port):
        """check if a port is listening on localhost"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                return result == 0
        except (socket.error, OSError) as e:
            print(f"error checking port {port}: {e}")
            return False
