#!/bin/bash
#
# GeneTrader Daemon Installer
#
# This script installs and configures the GeneTrader daemon as a systemd service.
#
# Usage:
#   sudo ./scripts/install_daemon.sh [options]
#
# Options:
#   --strategy NAME    Strategy name to monitor (default: GeneTrader)
#   --check-interval N Check interval in seconds (default: 300)
#   --optimize-interval N  Minimum hours between optimizations (default: 72)
#   --uninstall        Remove the daemon service
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
STRATEGY="GeneTrader"
CHECK_INTERVAL=300
OPTIMIZE_HOURS=72
UNINSTALL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --strategy)
            STRATEGY="$2"
            shift 2
            ;;
        --check-interval)
            CHECK_INTERVAL="$2"
            shift 2
            ;;
        --optimize-interval)
            OPTIMIZE_HOURS="$2"
            shift 2
            ;;
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_FILE="/etc/systemd/system/genetrader.service"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}GeneTrader Daemon Installer${NC}"
echo -e "${GREEN}========================================${NC}"

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

# Uninstall
if [ "$UNINSTALL" = true ]; then
    echo -e "${YELLOW}Uninstalling GeneTrader daemon...${NC}"

    systemctl stop genetrader 2>/dev/null || true
    systemctl disable genetrader 2>/dev/null || true
    rm -f "$SERVICE_FILE"
    systemctl daemon-reload

    echo -e "${GREEN}✅ GeneTrader daemon uninstalled${NC}"
    exit 0
fi

# Calculate optimize interval in seconds
OPTIMIZE_INTERVAL=$((OPTIMIZE_HOURS * 3600))

echo ""
echo -e "Configuration:"
echo -e "  Project Directory: ${GREEN}$PROJECT_DIR${NC}"
echo -e "  Strategy: ${GREEN}$STRATEGY${NC}"
echo -e "  Check Interval: ${GREEN}${CHECK_INTERVAL}s${NC}"
echo -e "  Optimize Interval: ${GREEN}${OPTIMIZE_HOURS}h${NC}"
echo ""

# Check config file
CONFIG_FILE="$PROJECT_DIR/ga.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Config file not found: $CONFIG_FILE${NC}"
    echo "Please create ga.json from ga.json.example"
    exit 1
fi

# Create service file
echo -e "${YELLOW}Creating systemd service...${NC}"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=GeneTrader Adaptive Optimization Daemon
Documentation=https://github.com/imsatoshi/GeneTrader
After=network.target

[Service]
Type=simple
User=$(logname)
Group=$(logname)
WorkingDirectory=$PROJECT_DIR
Environment="PYTHONPATH=$PROJECT_DIR"
Environment="GENETRADER_CONFIG=$CONFIG_FILE"

ExecStart=/usr/bin/python3 $PROJECT_DIR/scripts/genetrader_daemon.py \\
    --config $CONFIG_FILE \\
    --strategy $STRATEGY \\
    --check-interval $CHECK_INTERVAL \\
    --optimize-interval $OPTIMIZE_INTERVAL

Restart=always
RestartSec=30
StartLimitInterval=300
StartLimitBurst=5

StandardOutput=journal
StandardError=journal
SyslogIdentifier=genetrader

MemoryMax=2G
CPUQuota=80%

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ Service file created: $SERVICE_FILE${NC}"

# Reload systemd
systemctl daemon-reload

# Enable and start service
echo -e "${YELLOW}Enabling and starting service...${NC}"
systemctl enable genetrader
systemctl start genetrader

# Check status
sleep 2
if systemctl is-active --quiet genetrader; then
    echo -e "${GREEN}✅ GeneTrader daemon is running${NC}"
else
    echo -e "${RED}❌ Failed to start daemon${NC}"
    echo "Check logs with: journalctl -u genetrader -f"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Useful commands:"
echo "  Check status:    sudo systemctl status genetrader"
echo "  View logs:       journalctl -u genetrader -f"
echo "  Restart:         sudo systemctl restart genetrader"
echo "  Stop:            sudo systemctl stop genetrader"
echo "  Uninstall:       sudo $SCRIPT_DIR/install_daemon.sh --uninstall"
echo ""
