""" disk metric collector, uses os.statvfs() and /prog/diskstats"""
import os


class DiskCollector:
    def __init__(self):
        self.prev_stats = {}

    def collect(self):
        """collect disk metrics"""
        partitions = self._get_disk_usage()
        io_stats = self._get_disk_io()

        return {
            "partitions": partitions,
            "io": io_stats
        }

    def _get_disk_usage(self):
        """get disk usage for all mounted partitions"""
        partitions = []

        try:
            # read mount points from /proc/mounts
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 2:
                        continue

                    device = parts[0]
                    mount_point = parts[1]
                    fs_type = parts[2] if len(parts) > 2 else ''

                    # skip virtual filesystems
                    if fs_type in ['proc', 'sysfs', 'devpts', 'tmpfs', 'devtmpfs',
                                   'cgroup', 'cgroup', 'pstore', 'bpf', 'tracefs',
                                   'debugfs', 'hugetlbfs', 'mqueue', 'configfs',
                                   'fusectl', 'securityfs']:
                        continue

                    # skip if device doesnt start with /
                    if not device.startswith('/'):
                        continue

                    try:
                        stat = os.statvfs(mount_point)
                        total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
                        free_gb = (stat.f_bavail * stat.f_frsize) / ( 1024**3)
                        used_gb = total_gb - free_gb
                        percent = (used_gb / total_gb * 100) if total_gb > 0 else 0

                        partitions.append({
                            "mount": mount_point,
                            "device": device,
                            "total_gb": round(total_gb, 2),
                            "used_gb": round(used_gb, 2),
                            "free_gb": round(free_gb, 2),
                            "percent": round(percent, 2)
                        })
                    except (OSError, ZeroDivisionError):
                        # skip mounts that we cant access
                        continue
        except IOError as e:
            print(f"Error reading disk info: {e}")

        return partitions

    def _get_disk_io(self):
        """read disk I/O statistics from /proc/diskstats"""
        io_stats = {}

        try:
            with open('/proc/diskstats', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 14:
                        continue

                    device = parts[2]

                    # skip partition numbers, onle look at whole disks
                    # (sda, nvmeon1, etc, not sda1, nvme0n1p1)
                    if any(device.endswith(str(i)) for i in range(10)):
                        if not ('nvme' in device and 'n' in device[-3:]):
                            continue

                        reads_completed = int(parts[3])
                        reads_merged = int(parts[4])
                        sectors_read = int(parts[5])
                        read_time_ms = int(parts[6])

                        writes_completed = int(parts[7])
                        writes_merged = int(parts[8])
                        sectors_written = int(parts[9])
                        write_time_ms = int(parts[10])

                        io_stats[device] = {
                            "reads": reads_completed,
                            "writes": writes_completed,
                            "read_kb": sectors_read * 512 / 1024
                            "write_kb": sectors_written * 512 / 1024
                        }

            except (IOError, ValueError, IndexError) as e:
                print(f"Error reading disk I/O stats: {e}")

            return io_stats  



