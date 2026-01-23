#!/bin/bash
# Install and start the systemd service

echo "Installing systemd service..."

# Copy service file to systemd directory
sudo cp scripts/nlq-api.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable nlq-api

# Start the service
sudo systemctl start nlq-api

echo "✓ Service installed and started"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status nlq-api    # Check status"
echo "  sudo systemctl stop nlq-api      # Stop service"
echo "  sudo systemctl restart nlq-api   # Restart service"
echo "  sudo journalctl -u nlq-api -f    # View logs (live)"
echo "  sudo systemctl disable nlq-api   # Disable auto-start"
