#!/bin/bash

# Setup Log Forwarding from Argo Workflows to Kibana
# This script configures Filebeat to collect Argo workflow logs and forward them to Elasticsearch

set -e

echo "🚀 Setting up log forwarding from Argo Workflows to Kibana..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        print_error "docker is not installed"
        exit 1
    fi
    
    # Check if Argo namespace exists
    if ! kubectl get namespace argo &> /dev/null; then
        print_error "Argo namespace does not exist. Please install Argo Workflows first."
        exit 1
    fi
    
    # Check if Elasticsearch is running
    if ! curl -s http://localhost:9200/_cluster/health &> /dev/null; then
        print_warning "Elasticsearch doesn't seem to be running on localhost:9200"
        print_warning "Make sure to start your Elasticsearch stack first:"
        print_warning "cd ../elastic-setup && docker-compose up -d"
        read -p "Do you want to continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    print_status "Prerequisites check completed ✓"
}

# Deploy Filebeat configuration
deploy_filebeat() {
    print_status "Deploying Filebeat for log collection..."
    
    # Apply the Filebeat configuration
    kubectl apply -f filebeat-argo-logs.yaml
    
    # Wait for Filebeat to be ready
    print_status "Waiting for Filebeat to start..."
    kubectl rollout status daemonset/filebeat -n argo --timeout=300s
    
    print_status "Filebeat deployed successfully ✓"
}

# Verify Elasticsearch connection
verify_elasticsearch_connection() {
    print_status "Verifying Elasticsearch connection..."
    
    # Wait a bit for Filebeat to start sending logs
    sleep 30
    
    # Check if index pattern exists
    if curl -s -u elastic:password "http://localhost:9200/argo-workflows-*/_search" | grep -q "hits"; then
        print_status "Elasticsearch receiving logs ✓"
    else
        print_warning "No logs found in Elasticsearch yet. This might take a few minutes."
        print_warning "Run some Argo workflows to generate logs."
    fi
}

# Configure Kibana dashboards
setup_kibana_dashboards() {
    print_status "Setting up Kibana dashboards..."
    
    # Wait for Kibana to be ready
    print_status "Waiting for Kibana to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:5601/api/status | grep -q "available"; then
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Kibana is not responding. Please check if it's running."
            exit 1
        fi
        sleep 10
    done
    
    # Import dashboards (this would require curl with authentication)
    print_status "To import the Kibana dashboard, follow these steps:"
    echo "1. Open Kibana at http://localhost:5601"
    echo "2. Go to Management > Saved Objects"
    echo "3. Click 'Import' and select: kibana-dashboard-config.json"
    echo "4. Or create index pattern manually: 'argo-workflows-*' with time field '@timestamp'"
    
    print_status "Kibana setup instructions provided ✓"
}

# Start a test workflow to generate logs
start_test_workflow() {
    print_status "Starting a test ML pipeline workflow..."
    
    # Check if the cron workflow already exists
    if kubectl get cronworkflow ml-pipeline-cron -n argo &> /dev/null; then
        print_status "ML pipeline cron workflow already exists"
        
        # Trigger it manually to generate immediate logs
        kubectl create -n argo -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: ml-pipeline-test-
  namespace: argo
  labels:
    monitoring: "enabled"
    pipeline-type: "ml-cv"
    schedule-type: "manual-test"
spec:
  entrypoint: cron-ml-pipeline
  arguments:
    parameters:
    - name: dataset-name
      value: "cv-dataset-test-$(date +%s)"
    - name: batch-size
      value: "500"
  templates:
  - name: cron-ml-pipeline
    container:
      image: python:3.9-slim
      command: [python, -c]
      args:
      - |
        import json
        from datetime import datetime, timezone
        import time
        
        # Generate test log messages with emojis like the real workflow
        messages = [
            "📅 CRON TIMING RECORD: Pipeline started",
            "🔍 Validating data source: cv-dataset-test",
            "✅ Data validation complete: 950 records found", 
            "📅 Checking data freshness...",
            "✅ Data freshness check complete: 2.5 hours old",
            "🔧 Extracting features from dataset...",
            "✅ Feature extraction complete: 1250 features",
            "🎨 Augmenting data with 5 techniques...",
            "✅ Data augmentation complete: 850 samples",
            "🤖 Training model on dataset...",
            "✅ Model training complete: 0.847 accuracy",
            "📊 Evaluating model performance...",
            "✅ Model evaluation complete: F1-Score 0.832",
            "💾 Storing results and artifacts...",
            "✅ Results storage complete",
            "📅 CRON TIMING RECORD: Pipeline completed"
        ]
        
        for i, msg in enumerate(messages):
            print(f"Step {i+1}: {msg}")
            time.sleep(2)  # 2 second delay between steps
        
        print("🎉 Test ML pipeline completed successfully!")
EOF
        
        print_status "Test workflow started! Check Argo UI for progress."
    else
        print_status "Deploying ML pipeline cron workflow first..."
        kubectl apply -f cron-ml-pipeline.yaml
        print_status "Cron workflow deployed. It will run every 10 minutes."
    fi
}

# Display helpful information
display_helpful_info() {
    print_status "🎉 Log forwarding setup completed!"
    echo
    echo "📊 Access your monitoring tools:"
    echo "   • Argo UI: http://localhost:2746"
    echo "   • Kibana: http://localhost:5601"
    echo "   • Elasticsearch: http://localhost:9200"
    echo
    echo "🔍 Useful Kibana searches for your ML pipeline:"
    echo "   • All ML pipeline logs: pipeline:\"ml-pipeline\""
    echo "   • Only errors: pipeline:\"ml-pipeline\" AND log_type:\"error\""
    echo "   • Timing records: pipeline:\"ml-pipeline\" AND log_type:\"timing\""
    echo "   • Task completions: pipeline:\"ml-pipeline\" AND log_type:\"completion\""
    echo
    echo "📝 Log forwarding details:"
    echo "   • Index pattern: argo-workflows-*"
    echo "   • Logs are parsed and enriched with metadata"
    echo "   • Filebeat runs as DaemonSet in argo namespace"
    echo
    echo "🐛 Troubleshooting:"
    echo "   • Check Filebeat status: kubectl get pods -n argo -l k8s-app=filebeat"
    echo "   • View Filebeat logs: kubectl logs -n argo -l k8s-app=filebeat"
    echo "   • Check Elasticsearch indices: curl http://localhost:9200/_cat/indices"
}

# Main execution
main() {
    echo "=========================================="
    echo "  Argo Workflows → Kibana Log Forwarding"
    echo "=========================================="
    echo
    
    check_prerequisites
    deploy_filebeat
    verify_elasticsearch_connection
    setup_kibana_dashboards
    start_test_workflow
    display_helpful_info
}

# Run main function
main "$@" 