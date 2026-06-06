#!/bin/bash
#
# Sentinel Agent Installation Script
# Installs the sentinel agent as a systemd service
#

set -e

# Configuration
INSTALL_DIR="/opt/sentinel-agent"
SERVICE_NAME="sentinel-agent"
SERVICE_FILE="sentinel-agent.service"
DEPLOY_USER="${DEPLOY_USER:-deploy}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "  Sentinel Agent Installation"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Please run: sudo ./install.sh"
    exit 1
fi

# Check if deploy user exists
if ! id "$DEPLOY_USER" &>/dev/null; then
    echo -e "${YELLOW}Warning: User '$DEPLOY_USER' does not exist${NC}"
    read -p "Create user $DEPLOY_USER? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        useradd -m -s /bin/bash "$DEPLOY_USER"
        echo -e "${GREEN}User $DEPLOY_USER created${NC}"
    else
        echo -e "${RED}Installation cancelled${NC}"
        exit 1
    fi
fi

# Create installation directory
echo "Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Copy agent files
echo "Copying agent files..."
cp -r collectors "$INSTALL_DIR/"
cp agent.py "$INSTALL_DIR/"
cp config.yaml "$INSTALL_DIR/config.yaml.example"

# If config.yaml doesn't exist in target, copy the example
if [ ! -f "$INSTALL_DIR/config.yaml" ]; then
    cp config.yaml "$INSTALL_DIR/config.yaml"
    echo -e "${GREEN}Created new config.yaml${NC}"
    echo -e "${YELLOW}Please edit $INSTALL_DIR/config.yaml before starting the service${NC}"
else
    echo -e "${YELLOW}Existing config.yaml found, not overwriting${NC}"
fi

# Set permissions
echo "Setting permissions..."
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/agent.py"

# Install systemd service
echo "Installing systemd service..."
cp "$SERVICE_FILE" "/etc/systemd/system/$SERVICE_NAME.service"

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Ask to enable and start service
echo ""
read -p "Enable and start the service now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    systemctl enable "$SERVICE_NAME"
    systemctl start "$SERVICE_NAME"
    echo -e "${GREEN}Service enabled and started${NC}"

    # Show status
    echo ""
    echo "Service status:"
    systemctl status "$SERVICE_NAME" --no-pager
else
    echo -e "${YELLOW}Service not started${NC}"
    echo "To enable and start later, run:"
    echo "  sudo systemctl enable $SERVICE_NAME"
    echo "  sudo systemctl start $SERVICE_NAME"
fi

echo ""
echo -e "${GREEN}======================================"
echo "  Installation Complete!"
echo "======================================${NC}"
echo ""
echo "Useful commands:"
echo "  View logs:      journalctl -u $SERVICE_NAME -f"
echo "  Check status:   systemctl status $SERVICE_NAME"
echo "  Stop service:   systemctl stop $SERVICE_NAME"
echo "  Restart:        systemctl restart $SERVICE_NAME"
echo "  Edit config:    nano $INSTALL_DIR/config.yaml"
echo ""
