#!/bin/bash

# 🌐 Open Kibana Dashboard
# Uses centralized version management from versions.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Source centralized versions
if [[ -f "../versions.sh" ]]; then
    source ../versions.sh
elif [[ -f "./versions.sh" ]]; then
    source ./versions.sh
else
    echo -e "${RED}❌ versions.sh not found. Please run from project root or elastic-setup directory${NC}"
    exit 1
fi

echo -e "${BLUE}🌐 Opening Kibana Dashboard${NC}"
echo "=========================="

# Check if Kibana is running
if ! curl -s http://localhost:${KIBANA_PORT}/api/status >/dev/null 2>&1; then
    echo -e "${RED}❌ Kibana is not running. Please start it first with ./start-elasticsearch.sh${NC}"
    exit 1
fi

KIBANA_URL="http://localhost:${KIBANA_PORT}"

echo -e "${GREEN}✅ Kibana is running at ${KIBANA_URL}${NC}"
echo ""
echo -e "${BLUE}🔐 Login credentials:${NC}"
if [[ -f ".env" ]]; then
    echo "Username: elastic"
    echo "Password: $(grep ELASTIC_PASSWORD .env | cut -d'=' -f2)"
else
    echo "Username: elastic"
    echo "Password: (check .env file)"
fi

echo ""
echo -e "${YELLOW}🚀 Opening Kibana in browser...${NC}"

# Open browser based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open "$KIBANA_URL"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v xdg-open &> /dev/null; then
        xdg-open "$KIBANA_URL"
    elif command -v gnome-open &> /dev/null; then
        gnome-open "$KIBANA_URL"
    else
        echo -e "${YELLOW}⚠️  Could not open browser automatically${NC}"
        echo "Please open: $KIBANA_URL"
    fi
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    start "$KIBANA_URL"
else
    echo -e "${YELLOW}⚠️  Could not detect OS to open browser${NC}"
    echo "Please open: $KIBANA_URL"
fi

echo ""
echo -e "${BLUE}💡 Kibana Getting Started:${NC}"
echo "1. Login with elastic user credentials"
echo "2. Go to 'Management' → 'Stack Management'"
echo "3. Create index patterns for your data"
echo "4. Use 'Discover' to explore your data"
echo "5. Create visualizations and dashboards"
echo ""
echo -e "${BLUE}🔗 Useful Kibana Features:${NC}"
echo "• Discover: Explore and search your data"
echo "• Visualize: Create charts and graphs"
echo "• Dashboard: Combine visualizations"
echo "• Dev Tools: Run Elasticsearch queries"
echo "• Stack Monitoring: Monitor Elasticsearch health" 