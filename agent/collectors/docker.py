"""Docker container metric collector - shells out to `docker stats`"""
import logging
import re
import subprocess

logger = logging.getLogger(__name__)

# Bytes per unit, keyed by upper-cased suffix. Docker normally prints memory in
# binary units (MiB, GiB), but some versions use decimal ones (kB, MB, GB).
SIZE_UNIT_BYTES = {
    'B': 1,
    'KB': 1000, 'MB': 1000 ** 2, 'GB': 1000 ** 3, 'TB': 1000 ** 4, 'PB': 1000 ** 5,
    'KIB': 1024, 'MIB': 1024 ** 2, 'GIB': 1024 ** 3, 'TIB': 1024 ** 4, 'PIB': 1024 ** 5,
}

SIZE_PATTERN = re.compile(r'^([0-9]*\.?[0-9]+(?:[eE][+-]?[0-9]+)?)\s*([A-Za-z]+)$')


class DockerCollector:
    def __init__(self):
        # Whether the current run of `docker stats` failures has been logged yet
        self.failure_logged = False

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
                # Docker is installed but unusable, typically because this user is
                # not in the docker group. Say so once rather than every cycle.
                if not self.failure_logged:
                    stderr_lines = result.stderr.strip().splitlines()
                    reason = stderr_lines[0] if stderr_lines else f"exit code {result.returncode}"
                    logger.warning(f"docker stats failed, container metrics will be empty: {reason}")
                    self.failure_logged = True
                return containers

            self.failure_logged = False

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
        """Convert a docker-formatted size string (e.g. '512MiB', '1.9GiB', '10.5kB') to MB"""
        match = SIZE_PATTERN.match(size_str.strip())
        if not match:
            return 0.0

        number, unit = match.groups()
        unit_bytes = SIZE_UNIT_BYTES.get(unit.upper())
        if unit_bytes is None:
            return 0.0

        return round(float(number) * unit_bytes / (1024 ** 2), 2)
