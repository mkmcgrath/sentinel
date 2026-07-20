"""Docker container metric collector - shells out to `docker stats`"""
import subprocess


class DockerCollector:
    def collect(self):
        """Collect per-container CPU and memory usage, if Docker is available"""
        return self._get_container_stats()

    def _get_container_stats(self):
        containers = []

        try:
            result = subprocess.run(
                [
                    'docker', 'stats', '--no-stream', '--no-trunc',
                    '--format', '{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}'
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return containers

            for line in result.stdout.strip().splitlines():
                parts = line.split('|')
                if len(parts) != 4:
                    continue

                name, cpu_perc, mem_usage, mem_perc = parts
                mem_used_mb, mem_limit_mb = self._parse_mem_usage(mem_usage)

                containers.append({
                    "name": name,
                    "cpu_percent": self._parse_percent(cpu_perc),
                    "mem_used_mb": mem_used_mb,
                    "mem_limit_mb": mem_limit_mb,
                    "mem_percent": self._parse_percent(mem_perc)
                })

        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.SubprocessError):
            # Docker not installed or daemon not reachable - not an error, just no data
            pass

        return containers

    @staticmethod
    def _parse_percent(value):
        """Parse a string like '12.34%' into a float"""
        try:
            return round(float(value.strip().rstrip('%')), 2)
        except (ValueError, AttributeError):
            return 0.0

    @staticmethod
    def _parse_mem_usage(value):
        """Parse a string like '123.4MiB / 1.9GiB' into (used_mb, limit_mb)"""
        try:
            used_str, limit_str = [v.strip() for v in value.split('/')]
            return DockerCollector._to_mb(used_str), DockerCollector._to_mb(limit_str)
        except (ValueError, AttributeError):
            return 0.0, 0.0

    @staticmethod
    def _to_mb(size_str):
        """Convert a docker-formatted size string (e.g. '512MiB', '1.9GiB') to MB"""
        units = {
            'GiB': 1024,
            'MiB': 1,
            'KiB': 1 / 1024,
            'B': 1 / (1024 ** 2),
        }
        for unit, factor in units.items():
            if size_str.endswith(unit):
                number = size_str[:-len(unit)]
                return round(float(number) * factor, 2)
        return 0.0
