#!/bin/bash

# 🚀 Argo Workflows → Kibana Duration Analytics Setup
# This script sets up comprehensive duration monitoring linking your 
# existing workflow monitor to Kibana with duration-focused dashboards

set -e

echo "🚀 Setting up Argo Workflows → Kibana Duration Analytics Integration..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [[ ! -d "simple-monitoring" ]]; then
    echo -e "${RED}❌ Please run this script from the argo-workflows directory${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Step 1: Starting Elasticsearch & Kibana...${NC}"

# Start Elasticsearch and Kibana if not running
cd ../elastic-setup
if ! docker compose ps | grep -q "elasticsearch.*Up"; then
    echo -e "${YELLOW}⚡ Starting Elasticsearch...${NC}"
    docker compose up -d elasticsearch
    echo -e "${GREEN}✅ Elasticsearch started${NC}"
else
    echo -e "${GREEN}✅ Elasticsearch already running${NC}"
fi

if ! docker compose ps | grep -q "kibana.*Up"; then
    echo -e "${YELLOW}⚡ Starting Kibana...${NC}"
    docker compose up -d kibana
    echo -e "${GREEN}✅ Kibana started${NC}"
else
    echo -e "${GREEN}✅ Kibana already running${NC}"
fi

cd ../argo-workflows

echo -e "${BLUE}📋 Step 2: Installing Python dependencies...${NC}"

# Install dependencies
cd simple-monitoring
pip install -r requirements.txt
echo -e "${GREEN}✅ Dependencies installed${NC}"

echo -e "${BLUE}📋 Step 3: Testing Elasticsearch connection...${NC}"

# Wait for Elasticsearch to be ready
echo -e "${YELLOW}⏳ Waiting for Elasticsearch to be ready...${NC}"
timeout=60
while ! curl -s -u elastic:password http://localhost:9200/_cluster/health > /dev/null; do
    sleep 2
    timeout=$((timeout - 2))
    if [[ $timeout -le 0 ]]; then
        echo -e "${RED}❌ Elasticsearch not ready after 60 seconds${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ Elasticsearch is ready${NC}"

echo -e "${BLUE}📋 Step 4: Testing Kibana integration...${NC}"

# Test the Kibana integration
python3 -c "
from kibana_integration import KibanaIntegration
try:
    integration = KibanaIntegration()
    health = integration.health_check()
    print('✅ Kibana integration test successful')
    print(f'📊 Connection status: {health[\"connection_status\"]}')
except Exception as e:
    print(f'❌ Kibana integration test failed: {e}')
    exit(1)
"

echo -e "${GREEN}✅ Kibana integration working${NC}"

echo -e "${BLUE}📋 Step 5: Setting up Kibana dashboards...${NC}"

# Wait for Kibana to be ready
echo -e "${YELLOW}⏳ Waiting for Kibana to be ready...${NC}"
timeout=120
while ! curl -s -u elastic:password http://localhost:5601/api/status > /dev/null; do
    sleep 3
    timeout=$((timeout - 3))
    if [[ $timeout -le 0 ]]; then
        echo -e "${RED}❌ Kibana not ready after 120 seconds${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ Kibana is ready${NC}"

# Import the duration dashboard
echo -e "${YELLOW}📊 Importing duration analytics dashboard...${NC}"
cd ..

curl -X POST "http://localhost:5601/api/saved_objects/_import" \
     -H "kbn-xsrf: true" \
     -H "Content-Type: application/json" \
     -u elastic:password \
     --data @kibana-duration-dashboard.json

echo -e "${GREEN}✅ Duration dashboard imported to Kibana${NC}"

echo -e "${BLUE}📋 Step 6: Starting the enhanced workflow monitor...${NC}"

cd simple-monitoring

# Create a systemd service or docker-compose setup (optional)
cat > docker-compose.yml << EOF
version: '3.8'
services:
  workflow-monitor:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ELASTICSEARCH_HOST=host.docker.internal:9200
      - ELASTICSEARCH_USER=elastic
      - ELASTICSEARCH_PASSWORD=password
      - ENVIRONMENT=on-prem
    volumes:
      - ./workflow_metrics.db:/app/workflow_metrics.db
    depends_on:
      - elasticsearch
      - kibana
    networks:
      - default
      
networks:
  default:
    external:
      name: elastic-setup_default
EOF

# Create Dockerfile for the monitor
cat > Dockerfile << EOF
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "workflow_monitor.py"]
EOF

echo -e "${GREEN}✅ Docker setup created${NC}"

echo -e "${BLUE}📋 Step 7: Starting workflow monitor with Kibana integration...${NC}"

# Start the monitor in background
nohup python3 workflow_monitor.py > monitor.log 2>&1 &
MONITOR_PID=$!
echo $MONITOR_PID > monitor.pid

sleep 3

# Check if monitor started successfully
if ps -p $MONITOR_PID > /dev/null; then
    echo -e "${GREEN}✅ Workflow monitor started (PID: $MONITOR_PID)${NC}"
else
    echo -e "${RED}❌ Failed to start workflow monitor${NC}"
    cat monitor.log
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Setup Complete! Here's what you can do now:${NC}"
echo ""
echo -e "${BLUE}📊 Access Points:${NC}"
echo -e "  • Workflow Monitor Dashboard: ${YELLOW}http://localhost:8000${NC}"
echo -e "  • Kibana Duration Analytics: ${YELLOW}http://localhost:5601${NC}"
echo -e "    - Username: ${YELLOW}elastic${NC}"
echo -e "    - Password: ${YELLOW}password${NC}"
echo ""
echo -e "${BLUE}🔗 Key Features:${NC}"
echo -e "  • ${GREEN}Real-time duration tracking${NC} for workflows and tasks"
echo -e "  • ${GREEN}Performance trend analysis${NC} with historical data"
echo -e "  • ${GREEN}Duration heatmaps${NC} showing patterns by time"
echo -e "  • ${GREEN}Longest running workflow/task identification${NC}"
echo -e "  • ${GREEN}Workflow efficiency analysis${NC} (duration vs task count)"
echo ""
echo -e "${BLUE}🛠️  Usage:${NC}"
echo "1. Collect workflow data:"
echo -e "   ${YELLOW}curl -X POST http://localhost:8000/api/collect${NC}"
echo ""
echo "2. Sync to Kibana:"
echo -e "   ${YELLOW}curl -X POST http://localhost:8000/api/kibana/sync${NC}"
echo ""
echo "3. Check Kibana status:"
echo -e "   ${YELLOW}curl http://localhost:8000/api/kibana/status${NC}"
echo ""
echo "4. Get duration summary:"
echo -e "   ${YELLOW}curl http://localhost:8000/api/kibana/summary${NC}"
echo ""
echo -e "${BLUE}📈 In Kibana:${NC}"
echo "  • Go to ${YELLOW}Dashboard → Argo Workflows - Duration Analytics Dashboard${NC}"
echo "  • Create custom queries on ${YELLOW}argo-metrics-workflows-*${NC} and ${YELLOW}argo-metrics-tasks-*${NC} indices"
echo ""
echo -e "${BLUE}🔧 Advanced:${NC}"
echo "  • Edit dashboard: Import ${YELLOW}kibana-duration-dashboard.json${NC} in Kibana"
echo "  • Custom metrics: Use ${YELLOW}kibana_integration.py${NC} directly"
echo "  • Monitor logs: ${YELLOW}tail -f simple-monitoring/monitor.log${NC}"
echo ""
echo -e "${GREEN}✨ Your workflow duration analytics are now fully integrated with Kibana!${NC}" 