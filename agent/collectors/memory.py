"""Memory metric collector - reads /proc/meminfo"""


class MemoryCollector:
    def collect(self):
        """Collect memory metrics"""
        mem_info = self._get_memory_info()

        return {
            "total_mb": mem_info['total'],
            "used_mb": mem_info['used'],
            "available_mb": mem_info['available'],
            "percent": mem_info['percent'],
            "swap_total_mb": mem_info['swap_total'],
            "swap_used_mb": mem_info['swap_used']
        }

    def _get_memory_info(self):
        """Read memory information from /proc/meminfo"""
        try:
            meminfo = {}
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        # Remove 'kB' and convert to int
                        value = int(parts[1].strip().split()[0])
                        meminfo[key] = value

            # Convert from KB to MB
            total = meminfo.get('MemTotal', 0) / 1024
            available = meminfo.get('MemAvailable', 0) / 1024
            free = meminfo.get('MemFree', 0) / 1024
            buffers = meminfo.get('Buffers', 0) / 1024
            cached = meminfo.get('Cached', 0) / 1024

            # Calculate used memory
            used = total - available

            # Calculate percentage
            percent = (used / total * 100) if total > 0 else 0

            # Swap information
            swap_total = meminfo.get('SwapTotal', 0) / 1024
            swap_free = meminfo.get('SwapFree', 0) / 1024
            swap_used = swap_total - swap_free

            return {
                'total': round(total, 2),
                'used': round(used, 2),
                'available': round(available, 2),
                'percent': round(percent, 2),
                'swap_total': round(swap_total, 2),
                'swap_used': round(swap_used, 2)
            }

        except (IOError, ValueError, KeyError) as e:
            print(f"Error reading memory info: {e}")
            return {
                'total': 0, 'used': 0, 'available': 0,
                'percent': 0, 'swap_total': 0, 'swap_used': 0
            }
