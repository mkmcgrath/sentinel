#!/bin/bash
# Sentinel Agent Installation Script (Phase 3.4)
# This script automates the deployment of the agent to a target node.

set -e

INSTALL_DIR="/opt/sentinel-agent"
SERVICE_FILE="sentinel-agent.service"

echo "Installing Sentinel Agent to $INSTALL_DIR..."

# Create directory
sudo mkdir -p $INSTALL_DIR
sudo mkdir -p $INSTALL_DIR/collectors

# copy files
# we copy the collectors separately to maintain the structure
sudo cp agent.py config.yaml $INSTALL_DIR/
sudo cp collectors/*.py $INSTALL_DIR/collectors/

# set up systemd service
echo "Setting up systemd service..."
sudo cp $SERVICE_FILE /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sentinel-agent
sudo systemctl restart sentinel-agent

echo "Sentinel Agent installed and started!"
