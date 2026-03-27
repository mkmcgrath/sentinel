"""CPU metric collector, reads /proc/stat and /proc/loadavg"""
import time

class CPUCollector:
    def __init__(self):
        self.prev_idle = 0
        self.prev_total = 0

    def collect(self):
        # collect CPU metrics
        usage = self._get_cpu_usage()
        load_avg = self._get_load_average()

        return {
            "usage_percent": round(usage, 2),
            "load_1m": load_avg[0],
            "load_5m": load_avg[1],
            "load_15m": load_avg[2]
        }

    def _get_cpu_usage(self):
        # calculate cpu usage percentage from /proc/stat
        try:
            with open('/proc/stat', 'r') as f:
                # first line has aggregate cpu stats
                line = f.readline()
                fields = line.split()

                # cpu fields: user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice
                user = int(fields[1])
                nice = int(fields[2])
                system = int(fields[3])
                idle = int(fields[4])
                iowait = int(fields[5])
                irq = int(fields[6])
                softirq = int(fields[7])

                # calculate total and idle time
                idle_time = idle + iowait
                total_time = user + nice + system + idle + iowait + irq + softirq

                # calculate delta (time) since last measurement
                idle_delta = idle_time - self.prev_idle
                total_delta = total_time - self.prev_total



