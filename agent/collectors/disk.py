"""Disk metric collector - uses os.statvfs() and /proc/diskstats"""
import logging
import os

logger = logging.getLogger(__name__)

# hi! if im qualified to copy this.. then what does it mean?? lets explain it:
#
#

# Filesystem types that are not real storage. squashfs and iso9660 are read-only
# images that always report 100% used (Ubuntu mounts one squashfs per snap), which
# would pin the node's disk figure at 100%.
SKIP_FS_TYPES = frozenset([
    'proc', 'sysfs', 'devpts', 'tmpfs', 'devtmpfs',
    'cgroup', 'cgroup2', 'pstore', 'bpf', 'tracefs',
    'debugfs', 'hugetlbfs', 'mqueue', 'configfs',
    'fusectl', 'securityfs',
    'squashfs', 'iso9660', 'overlay', 'nsfs', 'ramfs', 'efivarfs',
])


def _is_real_partition(device, fs_type):
    """True if a /proc/mounts entry is disk-backed storage worth reporting"""
    if fs_type in SKIP_FS_TYPES:
        return False

    # Real partitions are backed by a device path (/dev/...)
    return device.startswith('/')


SYS_BLOCK = '/sys/block'

# Block devices that are not storage worth reporting I/O for
SKIP_IO_DEVICE_PREFIXES = ('loop', 'ram', 'zram')


def _is_whole_disk(device):
    """True if a /proc/diskstats entry is a whole disk rather than a partition"""
    if device.startswith(SKIP_IO_DEVICE_PREFIXES):
        return False

    # Whole disks (sda, nvme0n1, mmcblk0, md0, dm-0) have their own entry in
    # /sys/block; partitions (sda1, nvme0n1p1, mmcblk0p1) only exist beneath
    # their parent disk. Going by name instead would drop SD cards, RAID and LVM.
    return os.path.exists(os.path.join(SYS_BLOCK, device))


# we start by defining a python class called DiskCollector
#
class DiskCollector:
    def __init__(self):   # the class inits itself? or meaning, when the class is instantiated, it instatntiates itself as 
        self.prev_stats = {} # a version of the prev.stats  method>? or however u say it??

    def collect(self):
        """Collect disk metrics"""
        partitions = self._get_disk_usage()
        io_stats = self._get_disk_io()

        return {
            "partitions": partitions,
            "io": io_stats
        }

    def _get_disk_usage(self):
        """Get disk usage for all mounted partitions"""
        partitions = []

        try:
            # Read mount points from /proc/mounts
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 2:
                        continue

                    device = parts[0]
                    mount_point = parts[1]
                    fs_type = parts[2] if len(parts) > 2 else ''

                    # Skip virtual filesystems and read-only images
                    if not _is_real_partition(device, fs_type):
                        continue

                    try:
                        stat = os.statvfs(mount_point)
                        total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
                        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
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
                        # Skip mounts we can't access
                        continue

        except IOError as e:
            logger.warning(f"Error reading disk info: {e}")

        return partitions

    def _get_disk_io(self):
        """Read disk I/O statistics from /proc/diskstats"""
        io_stats = {}

        try:
            with open('/proc/diskstats', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 14:
                        continue

                    device = parts[2]

                    # Only look at whole disks, not their partitions
                    if not _is_whole_disk(device):
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
                        "read_kb": sectors_read * 512 / 1024,  # sectors are 512 bytes
                        "write_kb": sectors_written * 512 / 1024
                    }

        except (IOError, ValueError, IndexError) as e:
            logger.warning(f"Error reading disk I/O stats: {e}")

        return io_stats
