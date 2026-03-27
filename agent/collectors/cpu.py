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

                # store for next calculation
                self.prev_idle = idle_time
                self.prev_total = total_time

                # calculate usage percentage
                if total_delta == 0:
                    return 0.0

                usage = 100.0 * (1.0 - idle_delta / total_delta)
                return max(0.0, min(100.0, usage)) 
        
        except (IOError, ValueError, IndexError) as e:
            print(f"error reading cpu stats: {e}")
            return 0.0 
    
    def _get_load_average(self):
        # read load averages from /proc/loadavg
        try: 
            with open('/proc/loadavg', 'r') as f:
                line = f.readline()
                fields = line.split()
                return (
                    float(fields[0]), # 1 min
                    float(fields[1]), # 5 min
                    float(fields[2]) # 15 min
                )
        except (IOError, ValueError, IndexError) as e:
            print(f"Error reading load average: {e}")
            return (0.0, 0.0, 0.0)



