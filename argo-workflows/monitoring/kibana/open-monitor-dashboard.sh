#!/bin/bash

# 📊 Argo Workflows Monitor Dashboard Launcher
# Starts the monitoring dashboard for Argo Workflows

set -e

# Source centralized versions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../../versions.sh"

# Configuration
MONITOR_DIR="${SCRIPT_DIR}/simple-monitoring"
MONITOR_PORT="8000"
MONITOR_URL="http://localhost:${MONITOR_PORT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📊 Argo Workflows Monitor Dashboard${NC}"
echo "===================================="

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up...${NC}"
    cd "${MONITOR_DIR}"
    docker-compose down 2>/dev/null || true
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Set trap for cleanup on script exit
trap cleanup EXIT INT TERM

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo -e "${RED}❌ Docker Compose not found. Please install Docker Compose first.${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is available and running${NC}"

# Navigate to monitoring directory
cd "${MONITOR_DIR}"

# Check if data directory exists
if [[ ! -d "data" ]]; then
    echo -e "${BLUE}📁 Creating data directory...${NC}"
    mkdir -p data
fi

# Check if env file exists
if [[ ! -f ".env" ]]; then
    echo -e "${BLUE}⚙️  Creating environment configuration...${NC}"
    cp env.example .env
    echo -e "${GREEN}✅ Environment file created${NC}"
fi

# Create sample data if database doesn't exist
if [[ ! -f "data/workflow_metrics.db" ]]; then
    echo -e "${BLUE}📊 Creating sample monitoring data...${NC}"
    
    # Check if Python is available for sample data creation
    if command -v python3 &> /dev/null; then
        # Install requirements if needed
        if [[ ! -d "venv" ]]; then
            python3 -m venv venv
            source venv/bin/activate
            pip install -r requirements.txt
        else
            source venv/bin/activate
        fi
        
        # Create sample data
        python create_sample_data.py
        deactivate
        echo -e "${GREEN}✅ Sample data created${NC}"
    else
        echo -e "${YELLOW}⚠️  Python not found - sample data will be created when container starts${NC}"
    fi
fi

# Stop any existing containers
echo -e "${BLUE}🧹 Stopping any existing monitoring containers...${NC}"
docker-compose down 2>/dev/null || true

# Start the monitoring dashboard
echo -e "${BLUE}🚀 Starting Argo Workflows Monitor Dashboard...${NC}"
docker-compose up -d

# Wait for the service to start
echo -e "${BLUE}⏳ Waiting for dashboard to be ready...${NC}"
sleep 10

# Check if the service is running
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Monitor dashboard is running${NC}"
else
    echo -e "${RED}❌ Failed to start monitor dashboard${NC}"
    echo -e "${YELLOW}💡 Check logs with: docker-compose logs${NC}"
    exit 1
fi

# Test connectivity
echo -e "${BLUE}🌐 Testing dashboard connectivity...${NC}"
if curl -s ${MONITOR_URL} > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Dashboard is accessible${NC}"
else
    echo -e "${YELLOW}⚠️  Dashboard may still be starting up${NC}"
fi

# Open browser
echo -e "${BLUE}🌐 Opening Monitor Dashboard in browser...${NC}"
echo -e "${YELLOW}📍 URL: ${MONITOR_URL}${NC}"

# Open browser (works on macOS, Linux, and Windows with WSL)
if command -v open &> /dev/null; then
    # macOS
    open "${MONITOR_URL}"
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open "${MONITOR_URL}"
elif command -v cmd.exe &> /dev/null; then
    # Windows WSL
    cmd.exe /c start "${MONITOR_URL}"
else
    echo -e "${YELLOW}⚠️  Could not auto-open browser. Please manually open: ${MONITOR_URL}${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Argo Workflows Monitor Dashboard is running!${NC}"
echo ""
echo -e "${BLUE}📋 Dashboard Features:${NC}"
echo "   • Real-time workflow performance charts"
echo "   • Task duration analysis"
echo "   • Workflow success/failure rates"
echo "   • Historical trends and metrics"
echo ""
echo -e "${BLUE}🔗 Useful URLs:${NC}"
echo "   • Dashboard: ${MONITOR_URL}"
echo "   • API Stats: ${MONITOR_URL}/api/stats"
echo "   • Timeline: ${MONITOR_URL}/api/timeline"
echo ""
echo -e "${BLUE}💡 Management Commands:${NC}"
echo "   • View logs: docker-compose logs -f"
echo "   • Stop dashboard: docker-compose down"
echo "   • Restart: docker-compose restart"
echo ""
echo -e "${BLUE}ℹ️  Press Ctrl+C to stop the dashboard${NC}"

# Keep script running to maintain the dashboard
echo -e "${BLUE}⏳ Dashboard running... (Press Ctrl+C to stop)${NC}"
while true; do
    sleep 5
    if ! docker-compose ps | grep -q "Up"; then
        echo -e "${RED}❌ Dashboard stopped unexpectedly${NC}"
        break
    fi
done 