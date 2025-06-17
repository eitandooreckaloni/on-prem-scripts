# Argo Workflows Performance Monitoring Strategy

## 🎯 Goal
Track pod/task durations and visualize performance trends over time for ML/CV workflows, especially cron jobs.

## 🛠️ Available Infrastructure
- ✅ Grafana (visualization)
- ✅ Elasticsearch (data storage/search)
- ❌ Argo → Prometheus metrics (limited/missing)

## 📊 Monitoring Approaches

### Option 1: Custom Workflow Reporter (Recommended)
**Pros:** Lightweight, workflow-embedded, immediate data
**Implementation:** Modify workflows to self-report timing data to Elasticsearch

```python
# Each workflow task reports:
{
  "workflow_name": "ml-pipeline-dag",
  "task_name": "process-images", 
  "start_time": "2024-06-17T11:32:20Z",
  "end_time": "2024-06-17T11:34:15Z",
  "duration_seconds": 115,
  "status": "succeeded",
  "dataset_name": "cv-dataset-v1",
  "resource_usage": {...}
}
```

### Option 2: Argo API Scraper Service
**Pros:** Centralized, historical data, no workflow modification
**Implementation:** Background service that queries Argo API and pushes to Elasticsearch

```python
# Service queries:
- argo list --completed
- argo get <workflow> -o json
# Extracts timing data and indexes to Elasticsearch
```

### Option 3: Log Parser + Elasticsearch
**Pros:** Uses existing logs, captures everything
**Implementation:** Parse Argo controller logs and workflow pod logs

### Option 4: Hybrid Database Approach
**Pros:** Structured data, easy querying, Grafana-friendly
**Implementation:** Custom collector → PostgreSQL/InfluxDB → Grafana

## 🚀 Recommended Implementation: Option 1 + Option 2

### Phase 1: Workflow Self-Reporting
- Embed timing collection in workflow templates
- Direct Elasticsearch integration
- Real-time performance tracking

### Phase 2: Centralized API Scraper  
- Historical data backfill
- Comprehensive workflow metadata
- Cron job performance trends

## 📈 Grafana Dashboard Goals

### Workflow Performance Dashboard
- Task duration trends over time
- Workflow success/failure rates  
- Resource utilization patterns
- Cron job performance consistency

### Alerting Thresholds
- Workflow duration exceeding baseline
- Task failure rate increases
- Resource usage anomalies
- Cron job scheduling delays

## 🔧 Technical Implementation Plan

1. **Workflow Template Enhancement**
   - Add timing collection to each task
   - Elasticsearch client integration
   - Structured logging format

2. **Elasticsearch Index Design**
   ```json
   {
     "mappings": {
       "properties": {
         "timestamp": {"type": "date"},
         "workflow_name": {"type": "keyword"},
         "task_name": {"type": "keyword"},
         "duration_ms": {"type": "long"},
         "status": {"type": "keyword"},
         "resource_requests": {"type": "object"},
         "node_name": {"type": "keyword"}
       }
     }
   }
   ```

3. **Grafana Visualization Strategy**
   - Time series: Task duration trends
   - Heatmaps: Performance patterns by time
   - Tables: Recent workflow executions
   - Alerts: Performance degradation detection 