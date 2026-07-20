# Sentinel

```
                         m      "                  ""#
   mmm    mmm   m mm   mm#mm  mmm    m rpm    mmm     #
  "   "  #"  #  #"  #    #      #    #"  #  #"  #    #
   """m  #""""  #   #    #      #    #   #  #""""    #
  "mmm"  "#mm"  #   #    "mm  mm#mm  #   #  "#mm"    "mm
```

**Sentinel** is a lightweight, distributed system monitoring solution designed for homelab environments. It collects metrics from multiple nodes, stores them centrally, and provides both terminal-based (TUI) and API access to the data.

## Features

- **Lightweight Agent**: Python agent with zero external dependencies (uses only stdlib)
- **Central Server**: FastAPI-based server with PostgreSQL storage
- **TUI Dashboard**: Beautiful terminal dashboard using Textual
- **Web Dashboard**: React-based browser UI with live node grid and alert status
- **Alert System**: Configurable threshold alerts with automatic resolution
- **RESTful API**: Complete API for custom integrations
- **Docker Support**: Easy deployment with docker-compose

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Node 1    │     │   Node 2    │     │   Node 3    │
│   (Agent)   │     │   (Agent)   │     │   (Agent)   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │    POST /api/v1/metrics              │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Central   │
                    │   Server    │
                    │  (FastAPI)  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ PostgreSQL  │
                    │  Database   │
                    └─────────────┘
```

## Quick Start

### 1. Deploy the Server (on your main host)

```bash
cd sentinel

# Create environment file
cp .env.example .env
# Edit .env and set a strong database password

# Start the server and database
docker-compose up -d

# Check logs
docker-compose logs -f server
```

The server will be available at `http://localhost:8080`

### 2. Install Agent on Nodes.

On each machine you want to monitor:

```bash
# Copy agent directory to the node
scp -r agent/ user@node:/tmp/

# SSH into the node
ssh user@node

# Edit the config
cd /tmp/agent
nano config.yaml
# Update: node_id, server_url

# Install the agent
sudo ./install.sh

# Check status
sudo systemctl status sentinel-agent
sudo journalctl -u sentinel-agent -f
```

### 3. Run the TUI Dashboard

On your workstation or main host:

```bash
cd tui
pip install -r requirements.txt

# Run the dashboard
python dashboard.py http://192.168.1.10:8080
```

Press `q` to quit, `r` to refresh manually.

## Project Structure

```
sentinel/
├── agent/                 # Lightweight monitoring agent
│   ├── collectors/        # Metric collectors (CPU, RAM, disk, etc.)
│   ├── agent.py          # Main agent script
│   ├── config.yaml       # Agent configuration
│   ├── install.sh        # Installation script
│   └── sentinel-agent.service  # Systemd service
├── server/               # Central API server
│   ├── routes/           # API route handlers
│   ├── app.py           # FastAPI application
│   ├── db.py            # Database models
│   ├── Dockerfile       # Container definition
│   └── requirements.txt # Python dependencies
├── tui/                 # Terminal dashboard
│   ├── dashboard.py     # Textual-based TUI
│   └── requirements.txt
├── web/                 # React web dashboard
│   ├── src/
│   │   ├── api.js       # Centralized API service layer
│   │   ├── App.jsx      # Router shell + nav
│   │   ├── components/  # NavBar, NodeCard, AlertsBanner
│   │   └── pages/       # HomePage, NodeDetailPage (stub), AlertsPage (stub)
│   ├── .env.example
│   └── package.json
└── docker-compose.yml   # Server deployment
```

## Agent Metrics Collected

The agent collects the following metrics using `/proc` filesystem (no external dependencies):

- **CPU**: Usage percentage, load averages (1m, 5m, 15m)
- **Memory**: Total, used, available, swap
- **Disk**: Usage per partition, I/O statistics
- **Network**: Bytes/packets in/out per interface, gateway latency
- **Services**: Systemd service status, listening ports
- **Containers**: Per-container CPU % and memory usage (via `docker stats`, when Docker is installed)

## API Reference

### Metrics

- `POST /api/v1/metrics` - Receive metrics from agents
- `GET /api/v1/metrics/latest/{node_id}` - Get latest metrics for a node
- `GET /api/v1/metrics/history/{node_id}` - Get historical metrics

### Nodes

- `GET /api/v1/nodes` - List all nodes
- `GET /api/v1/nodes/{node_id}` - Get node details
- `GET /api/v1/nodes/{node_id}/stats` - Get node statistics
- `DELETE /api/v1/nodes/{node_id}` - Delete a node

### Alerts

- `POST /api/v1/alerts` - Create alert rule
- `GET /api/v1/alerts` - List alert rules
- `GET /api/v1/alerts/{id}` - Get alert details
- `DELETE /api/v1/alerts/{id}` - Delete alert
- `GET /api/v1/alerts/events/active` - Get active alerts
- `GET /api/v1/alerts/events/history` - Get alert history

### Health

- `GET /api/v1/health` - Server health check

## Configuration

### Agent Configuration (`agent/config.yaml`)

```yaml
node_id: "my-node"
server_url: "http://192.168.1.10:8080"
report_interval: 10  # seconds
services:
  - sshd
  - docker
ports:
  - 22
  - 80
```

### Server Configuration (`.env`)

```env
POSTGRES_USER=sentinel
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=sentinel
PORT=8080
```

## Creating Alerts

Using the API:

```bash
curl -X POST http://localhost:8080/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "node-01",
    "name": "High CPU Usage",
    "metric": "cpu.usage_percent",
    "operator": "gt",
    "threshold": 80.0,
    "description": "Alert when CPU exceeds 80%"
  }'
```

## Webhook Notifications

Set the `WEBHOOK_URL` environment variable on the server to receive an HTTP POST every time an alert fires:

```env
WEBHOOK_URL=https://your-webhook-endpoint.example/sentinel
```

The POST body contains `alert_name`, `node_id`, `metric`, `value`, `threshold`, `operator`, and `timestamp`. Delivery is best-effort — a failed webhook is logged and never blocks metric ingestion. Leave `WEBHOOK_URL` unset to disable.

## Demo Mode

No homelab? Set `DEMO_MODE=true` on the server and it will simulate `DEMO_NODE_COUNT` (default 3) synthetic nodes with plausible, drifting CPU/memory/disk/network metrics — no real agents required. One node (`demo-01`) sweeps through a CPU sine wave that periodically crosses an auto-created 80% threshold alert, so you can watch the full trigger → resolve alert lifecycle in the TUI or web dashboard.

```bash
DEMO_MODE=true docker-compose up -d
```

Or when running the server locally:

```bash
DEMO_MODE=true DEMO_NODE_COUNT=5 python app.py
```

## Development

### Running Server Locally (without Docker)

```bash
cd server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set database URL
export DATABASE_URL="postgresql://user:pass@localhost:5432/sentinel"

# Run server
python app.py
```

### Running Agent Locally

```bash
cd agent
python3 agent.py config.yaml
```

## Troubleshooting

### Agent not reporting

```bash
# Check agent status
sudo systemctl status sentinel-agent

# View logs
sudo journalctl -u sentinel-agent -f

# Test network connectivity
curl http://your-server:8080/api/v1/health
```

### Server not starting

```bash
# Check docker logs
docker-compose logs server

# Check database connection
docker-compose logs db

# Verify database is healthy
docker-compose ps
```

### Database connection issues

```bash
# Check if PostgreSQL is accessible
docker exec -it sentinel-db psql -U sentinel -d sentinel

# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

## License

See LICENSE file for details.

## Contributing

This is a personal homelab project, but suggestions and improvements are welcome!

## Web Dashboard

The React web dashboard (`web/`) provides a browser-based view of the cluster.

### Running locally

```bash
cd web
cp .env.example .env.local
# Edit .env.local and set VITE_API_URL to your server address
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

**What's built:**
- Node grid home page — color-coded status cards with live CPU/MEM/DISK bars, auto-refreshes every 5 seconds
- Active alerts banner
- Persistent nav bar
- Node Detail page — CPU/memory/disk history charts (recharts) with a 1h/6h/24h toggle, plus service/port and container status
- Routing skeleton for the Alert Management page

**Still to come:**
- Alert Management page — create/toggle/delete rules, event history table

## Roadmap

- [x] Web dashboard — node grid home page
- [x] Web dashboard — node detail with historical charts
- [ ] Web dashboard — alert management page
- [x] Alert notifications (webhook)
- [x] Docker container monitoring
- [x] Demo mode with synthetic data
- [ ] Agent auto-discovery
- [ ] Metric aggregation and retention policies
- [ ] SSL/TLS support
- [ ] Multi-user authentication
