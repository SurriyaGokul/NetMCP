#!/bin/bash
# Setup script for configuring passwordless sudo for MCP Network Optimizer
# This allows the MCP server to execute network configuration commands with elevated privileges

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== MCP Network Optimizer - Sudo Setup ===${NC}\n"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}ERROR: Please do NOT run this script as root.${NC}"
    echo "Run it as your normal user: ./setup_sudo.sh"
    exit 1
fi

# Get current username
CURRENT_USER=$(whoami)
echo -e "Setting up passwordless sudo for user: ${GREEN}$CURRENT_USER${NC}\n"

# Check if sudo is available
if ! command -v sudo &> /dev/null; then
    echo -e "${RED}ERROR: sudo is not installed${NC}"
    echo "Please install sudo first: apt-get install sudo"
    exit 1
fi

# Create sudoers configuration file
SUDOERS_FILE="/etc/sudoers.d/mcp-net-optimizer"
TEMP_FILE=$(mktemp)

echo "# MCP Network Optimizer - Passwordless sudo configuration" > "$TEMP_FILE"
echo "# Created on $(date)" >> "$TEMP_FILE"
echo "# User: $CURRENT_USER" >> "$TEMP_FILE"
echo "" >> "$TEMP_FILE"

# Network configuration commands
cat >> "$TEMP_FILE" << EOF
# Allow passwordless execution of network configuration commands
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/sbin/sysctl
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/sysctl
$CURRENT_USER ALL=(ALL) NOPASSWD: /sbin/sysctl

# Traffic control
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/sbin/tc
$CURRENT_USER ALL=(ALL) NOPASSWD: /sbin/tc

# nftables
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/sbin/nft
$CURRENT_USER ALL=(ALL) NOPASSWD: /sbin/nft

# ethtool
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/sbin/ethtool
$CURRENT_USER ALL=(ALL) NOPASSWD: /sbin/ethtool

# ip command
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/sbin/ip
$CURRENT_USER ALL=(ALL) NOPASSWD: /sbin/ip

# iptables (legacy support)
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/sbin/iptables
$CURRENT_USER ALL=(ALL) NOPASSWD: /sbin/iptables
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/sbin/iptables-save
$CURRENT_USER ALL=(ALL) NOPASSWD: /sbin/iptables-save
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/sbin/iptables-restore
$CURRENT_USER ALL=(ALL) NOPASSWD: /sbin/iptables-restore

# ip6tables
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/sbin/ip6tables
$CURRENT_USER ALL=(ALL) NOPASSWD: /sbin/ip6tables
EOF

echo -e "${YELLOW}Generated sudoers configuration:${NC}"
echo "-----------------------------------"
cat "$TEMP_FILE"
echo "-----------------------------------"
echo ""

# Validate sudoers syntax
echo -e "${YELLOW}Validating sudoers syntax...${NC}"
if ! sudo visudo -c -f "$TEMP_FILE" &> /dev/null; then
    echo -e "${RED}ERROR: Invalid sudoers syntax!${NC}"
    rm "$TEMP_FILE"
    exit 1
fi
echo -e "${GREEN}✓ Syntax valid${NC}\n"

# Ask for confirmation
echo -e "${YELLOW}This will allow user '$CURRENT_USER' to run network commands without password.${NC}"
read -p "Do you want to proceed? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo "Setup cancelled."
    rm "$TEMP_FILE"
    exit 0
fi

# Install sudoers file
echo -e "${YELLOW}Installing sudoers configuration...${NC}"
echo "You will be prompted for your password to complete the installation."
echo ""

if sudo cp "$TEMP_FILE" "$SUDOERS_FILE"; then
    sudo chmod 0440 "$SUDOERS_FILE"
    echo -e "${GREEN}✓ Sudoers file installed successfully${NC}"
else
    echo -e "${RED}ERROR: Failed to install sudoers file${NC}"
    rm "$TEMP_FILE"
    exit 1
fi

rm "$TEMP_FILE"

# Test the configuration
echo -e "\n${YELLOW}Testing sudo configuration...${NC}"

TEST_COMMANDS=(
    "sysctl -a"
    "ip link show"
    "tc qdisc show"
)

ALL_TESTS_PASSED=true

for cmd in "${TEST_COMMANDS[@]}"; do
    CMD_ARRAY=($cmd)
    if sudo -n ${CMD_ARRAY[@]} &> /dev/null; then
        echo -e "${GREEN}✓${NC} $cmd"
    else
        echo -e "${RED}✗${NC} $cmd"
        ALL_TESTS_PASSED=false
    fi
done

echo ""

if $ALL_TESTS_PASSED; then
    echo -e "${GREEN}=== Setup Complete! ===${NC}"
    echo ""
    echo "The MCP Network Optimizer can now execute network commands with elevated privileges."
    echo ""
    echo "Commands configured for passwordless sudo:"
    echo "  • sysctl (kernel parameters)"
    echo "  • tc (traffic control)"
    echo "  • nft (nftables)"
    echo "  • ethtool (network interface settings)"
    echo "  • ip (network configuration)"
    echo ""
    echo -e "${YELLOW}Security Note:${NC}"
    echo "  These commands can modify network configuration. Only use this"
    echo "  on systems where you trust the MCP server and its configuration."
    echo ""
    echo "To remove these permissions, run:"
    echo "  sudo rm $SUDOERS_FILE"
else
    echo -e "${YELLOW}=== Setup Complete with Warnings ===${NC}"
    echo ""
    echo "Some test commands failed. This might be normal if certain"
    echo "tools are not installed (e.g., nft, tc)."
    echo ""
    echo "The sudoers file has been installed. Commands will work when needed."
fi

echo ""
echo -e "${GREEN}You can now run the MCP server and apply network optimizations!${NC}"
