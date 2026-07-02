# Sentinel Quick Start Guide

This guide will get you up and running quickly with Sentinel.

## Prerequisites

- Docker and docker-compose installed on your main host (hq)
- Python 3.7+ on all nodes
- SSH access to all nodes
- Network connectivity between all machines

## Step 1: Start the Server (5 minutes)

On your main host (192.168.1.10 - hq):

```bash
cd sentinel

# Create environment file
cp .env.example .env

# IMPORTANT: Edit .env and change the default password!
nano .env

# Start the server
docker-compose up -d

# Verify it's running
curl http://localhost:8080/api/v1/health
```

Expected output:
```json
{"status":"healthy","database":"connected","statistics":{...}}
```

## Step 2: Deploy Agents (10 minutes per node)

### On pi (192.168.1.12)

From your workstation:
```bash
cd sentinel
scp -r agent/ deploy@192.168.1.12:/tmp/
```

On pi:
```bash
cd /tmp/agent

# Edit config
nano config.yaml
# Change:
#   node_id: "pi"
#   server_url: "http://192.168.1.10:8080"

# Install
sudo ./install.sh

# Verify
sudo systemctl status sentinel-agent
sudo journalctl -u sentinel-agent -f
```

### On tp (192.168.1.11)

Repeat the same process:
```bash
# From workstation
scp -r agent/ deploy@192.168.1.11:/tmp/

# On tp
cd /tmp/agent
nano config.yaml  # Change node_id to "tp"
sudo ./install.sh
```

### On hq (192.168.1.10) - Optional

You can also monitor your main host:
```bash
cd agent
nano config.yaml  # Change node_id to "hq"
sudo ./install.sh
```

## Step 3: View the Dashboard (2 minutes)

### Option A — Terminal (TUI)

```bash
cd sentinel/tui

# Install dependencies (first time only)
pip3 install -r requirements.txt

# Launch dashboard
python3 dashboard.py http://192.168.1.10:8080
```

You should see:
- All your nodes listed with their status
- Real-time CPU, Memory, Disk usage
- Any active alerts

**Keyboard shortcuts:**
- `q` - Quit
- `r` - Manual refresh
- `d` - Toggle dark mode

### Option B — Web Dashboard

```bash
cd sentinel/web

# First time only
npm install
cp .env.example .env.local
# Edit .env.local: set VITE_API_URL=http://192.168.1.10:8080

npm run dev
```

Open `http://localhost:5173` in your browser. The node grid auto-refreshes every 5 seconds.

## Step 4: Test the System

### Create a test alert

```bash
curl -X POST http://192.168.1.10:8080/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "pi",
    "name": "High CPU Alert",
    "metric": "cpu.usage_percent",
    "operator": "gt",
    "threshold": 80.0,
    "description": "Alert when CPU exceeds 80%"
  }'
```

### View all nodes

```bash
curl http://192.168.1.10:8080/api/v1/nodes | jq
```

### Get latest metrics for a node

```bash
curl http://192.168.1.10:8080/api/v1/metrics/latest/pi | jq
```

## Troubleshooting

### Agent not connecting

```bash
# On the node
sudo journalctl -u sentinel-agent -f

# Test connectivity
curl http://192.168.1.10:8080/api/v1/health
ping 192.168.1.10
```

### Server issues

```bash
# Check containers
docker-compose ps

# View logs
docker-compose logs -f server
docker-compose logs -f db

# Restart
docker-compose restart
```

### Firewall issues

On the server (hq):
```bash
sudo ufw allow 8080/tcp
sudo ufw status
```

## Next Steps

1. **Configure services monitoring**: Edit `config.yaml` on each agent to add services you want to monitor
2. **Set up alerts**: Create alert rules for CPU, memory, disk thresholds
3. **Customize intervals**: Adjust `report_interval` in `config.yaml` if needed
4. **Add more nodes**: Repeat Step 2 for additional machines
5. **Secure the setup**: Set up firewall rules, use strong passwords, consider adding SSL/TLS

## Architecture Summary

```
pi (192.168.1.12)          tp (192.168.1.11)          hq (192.168.1.10)
- Pi-hole                  - Jellyfin                 - Photoprism
- Traefik                  - Agent                    - Nextcloud
- Radicale                                            - Server
- Vikunja                                             - Agent (optional)
- Agent

         All agents report to ──────────────────────> hq:8080 (Server)
```

## Configuration for Your Setup

Based on your plan:

**pi (192.168.1.12)**:
```yaml
node_id: "pi"
server_url: "http://192.168.1.10:8080"
services:
  - sshd
  - docker
  - pihole-FTL
  - traefik
ports:
  - 22
  - 53
  - 80
  - 443
```

**tp (192.168.1.11)**:
```yaml
node_id: "tp"
server_url: "http://192.168.1.10:8080"
services:
  - sshd
  - docker
  - jellyfin
ports:
  - 22
  - 8096
```

**hq (192.168.1.10)**:
```yaml
node_id: "hq"
server_url: "http://192.168.1.10:8080"
services:
  - sshd
  - docker
  - sentinel-server
ports:
  - 22
  - 8080
```

Happy monitoring!
