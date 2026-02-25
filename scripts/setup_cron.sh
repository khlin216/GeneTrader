#!/bin/bash
#
# GeneTrader Cron Setup
#
# Alternative to systemd - sets up cron jobs for periodic checks
#
# Usage:
#   ./scripts/setup_cron.sh [options]
#
# Options:
#   --strategy NAME    Strategy name (default: GeneTrader)
#   --check-interval N Minutes between checks (default: 5)
#   --uninstall        Remove cron jobs
#

set -e

# Default values
STRATEGY="GeneTrader"
CHECK_INTERVAL=5
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

# Get directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Cron job identifier
CRON_ID="# GeneTrader Auto"

# Uninstall
if [ "$UNINSTALL" = true ]; then
    echo "Removing GeneTrader cron jobs..."
    crontab -l 2>/dev/null | grep -v "$CRON_ID" | crontab -
    echo "✅ Cron jobs removed"
    exit 0
fi

echo "Setting up GeneTrader cron jobs..."
echo "  Strategy: $STRATEGY"
echo "  Check Interval: $CHECK_INTERVAL minutes"
echo ""

# Create the cron entry
CRON_ENTRY="*/$CHECK_INTERVAL * * * * cd $PROJECT_DIR && python3 run_adaptive.py --strategy $STRATEGY --check-only >> /var/log/genetrader.log 2>&1 $CRON_ID"

# Add to crontab (removing old entries first)
(crontab -l 2>/dev/null | grep -v "$CRON_ID"; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job installed"
echo ""
echo "Current cron jobs:"
crontab -l | grep GeneTrader
echo ""
echo "Log file: /var/log/genetrader.log"
echo ""
echo "To view logs: tail -f /var/log/genetrader.log"
echo "To uninstall: $SCRIPT_DIR/setup_cron.sh --uninstall"
