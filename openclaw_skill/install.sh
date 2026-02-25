#!/bin/bash
# Install GeneTrader skill for OpenClaw
#
# Usage:
#   ./install.sh                 # Install to default location
#   ./install.sh /custom/path    # Install to custom location

set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENETRADER_PATH="$(dirname "$SCRIPT_DIR")"

# Default OpenClaw skills directory
OPENCLAW_SKILLS="${1:-$HOME/.openclaw/skills}"

# Create the skill directory
SKILL_DIR="$OPENCLAW_SKILLS/genetrader"
mkdir -p "$SKILL_DIR"

# Copy files
cp "$SCRIPT_DIR/SKILL.md" "$SKILL_DIR/"
cp "$SCRIPT_DIR/genetrader" "$SKILL_DIR/"
chmod +x "$SKILL_DIR/genetrader"

echo "✅ GeneTrader skill installed to: $SKILL_DIR"
echo ""
echo "📝 Configure environment variables:"
echo ""
echo "   export GENETRADER_PATH=\"$GENETRADER_PATH\""
echo "   export GENETRADER_STRATEGY=\"GeneTrader\""
echo "   export GENETRADER_API_KEY=\"your-api-key\""
echo "   export GENETRADER_API_URL=\"http://localhost:8090\""
echo ""
echo "🚀 Usage in OpenClaw:"
echo ""
echo "   /genetrader check          # Check strategy performance"
echo "   /genetrader status         # Get system status"
echo "   /genetrader optimize       # Trigger re-optimization"
echo "   /genetrader approvals      # List pending approvals"
echo "   /genetrader approve <id>   # Approve deployment"
echo ""
echo "📖 See SKILL.md for full documentation"
