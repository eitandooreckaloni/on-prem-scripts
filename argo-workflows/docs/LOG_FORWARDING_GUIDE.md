# Argo Workflows → Kibana Log Forwarding Guide

This guide explains how to link your `ml-pipeline-cron` Argo workflow logs to Kibana for monitoring and analysis.

## 🎯 Overview

Your ML pipeline generates rich logs with emojis and structured data that we'll forward to Elasticsearch and visualize in Kibana. The solution uses **Filebeat** as a log shipper running as a DaemonSet in your Kubernetes cluster.

## 📋 Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────┐
│ Argo Workflows  │    │   Filebeat   │    │ Elasticsearch│    │   Kibana    │
│   (K8s Pods)    │───▶│ (DaemonSet)  │───▶│  (Docker)    │───▶│  (Docker)   │
│                 │    │              │    │              │    │             │
└─────────────────┘    └──────────────┘    └──────────────┘    └─────────────┘
      Pod logs              Log parsing        Log storage       Visualization
```

## 🚀 Quick Setup

1. **Start Elasticsearch & Kibana** (if not already running):
   ```bash
   cd ../elastic-setup
   docker-compose up -d
   ```

2. **Deploy log forwarding**:
   ```bash
   chmod +x setup-log-forwarding.sh
   ./setup-log-forwarding.sh
   ```

3. **Access Kibana**: http://localhost:5601
   - Username: `elastic`  
   - Password: `password`

## 📊 What Gets Forwarded

Your ML pipeline logs are automatically parsed and enriched:

### Original Log Format
```
🔍 Validating data source: cv-dataset-cron-2024-12-30T13:39:27Z
✅ Data validation complete: Records found: 1050, Validation score: 0.923
📅 CRON TIMING RECORD: {"@timestamp": "2024-12-30T13:42:15Z", ...}
```

### Enriched Elasticsearch Documents
```json
{
  "@timestamp": "2024-12-30T13:42:15Z",
  "message": "✅ Data validation complete: Records found: 1050",
  "log_type": "completion",
  "task_name": "validation",
  "workflow_type": "cron",
  "pipeline": "ml-pipeline",
  "kubernetes": {
    "namespace": "argo",
    "pod": {"name": "ml-pipeline-cron-abc123"},
    "container": {"name": "main"}
  },
  "argo": {
    "cluster": "kind-argo-dev",
    "environment": "on-prem",
    "log_source": "argo-workflows"
  }
}
```

## 🎨 Log Types & Parsing

Filebeat automatically categorizes your logs:

| Emoji Pattern | Log Type | Description |
|---------------|----------|-------------|
| `📅 CRON TIMING RECORD` | `timing` | Pipeline start/end markers |
| `✅` | `completion` | Task completion logs |
| `❌` or `ERROR` | `error` | Error conditions |
| `🔍📅🔧🎨🤖📊💾` | `progress` | Task progress updates |

## 📈 Kibana Dashboards

The setup includes a pre-configured dashboard with:

1. **Pipeline Executions Timeline** - Workflow run frequency over time
2. **Task Status Breakdown** - Pie chart of log types (completion/error/timing)
3. **Pipeline Logs Table** - Searchable log entries with metadata
4. **Error Logs Count** - Monitor failed tasks
5. **Pipeline Duration Metrics** - Performance tracking

### Import Dashboard
1. Open Kibana: http://localhost:5601
2. Go to **Management > Saved Objects**
3. Click **Import** and select `kibana-dashboard-config.json`

### Manual Index Pattern Setup
If auto-import fails:
1. Go to **Management > Index Patterns**
2. Create pattern: `argo-workflows-*`
3. Set time field: `@timestamp`

## 🔍 Useful Kibana Queries

### Basic Searches
```kql
# All ML pipeline logs
pipeline:"ml-pipeline"

# Only your cron workflow
pipeline:"ml-pipeline" AND workflow_type:"cron"

# Error logs only
pipeline:"ml-pipeline" AND log_type:"error"

# Task completion logs
pipeline:"ml-pipeline" AND log_type:"completion"

# Specific time range
pipeline:"ml-pipeline" AND @timestamp:[now-1h TO now]
```

### Advanced Queries
```kql
# Failed workflows (find patterns)
log_type:"error" AND kubernetes.pod.name:*ml-pipeline*

# Long-running tasks (timing analysis)
log_type:"timing" AND message:*duration*

# Data validation issues
task_name:"validation" AND message:*score* AND message:<0.8
```

## 🔧 Configuration Details

### Filebeat Configuration Highlights

- **Log Paths**: Automatically discovers container logs matching:
  - `/var/log/containers/*argo*.log`
  - `/var/log/containers/*workflow*.log` 
  - `/var/log/containers/*ml-pipeline*.log`

- **Processing**: 
  - Kubernetes metadata enrichment
  - JSON field decoding
  - Custom log parsing with JavaScript
  - Timestamp normalization

- **Output**: 
  - Target: `host.docker.internal:9200` (your Elasticsearch)
  - Index pattern: `argo-workflows-YYYY.MM.DD`
  - Authentication: `elastic:password`

### Index Template
```json
{
  "index_patterns": ["argo-workflows-*"],
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "refresh_interval": "5s"
  },
  "mappings": {
    "properties": {
      "@timestamp": {"type": "date"},
      "log_type": {"type": "keyword"},
      "task_name": {"type": "keyword"},
      "pipeline": {"type": "keyword"},
      "workflow_type": {"type": "keyword"},
      "message": {"type": "text", "analyzer": "standard"}
    }
  }
}
```

## 🐛 Troubleshooting

### Check Filebeat Status
```bash
kubectl get pods -n argo -l k8s-app=filebeat
kubectl logs -n argo -l k8s-app=filebeat
```

### Verify Elasticsearch Connection
```bash
# Check if logs are being indexed
curl -u elastic:password "http://localhost:9200/argo-workflows-*/_search?size=5&sort=@timestamp:desc"

# List all indices
curl -u elastic:password "http://localhost:9200/_cat/indices?v"
```

### Common Issues

1. **No logs in Kibana**:
   - Ensure Filebeat is running: `kubectl get pods -n argo`
   - Check Elasticsearch connectivity from cluster
   - Verify workflow pods are generating logs

2. **Elasticsearch connection failed**:
   - Update `hosts` in `filebeat-argo-logs.yaml` if needed
   - For Docker Desktop: use `host.docker.internal:9200`
   - For external ES: update to proper hostname/IP

3. **Index pattern not found**:
   - Wait for logs to be generated first
   - Manually create index pattern in Kibana
   - Check index exists: `curl localhost:9200/_cat/indices | grep argo`

## 📝 Monitoring Best Practices

### Set up Alerts
Create Kibana Watcher alerts for:
- Pipeline failures (log_type:error)
- Long-running pipelines (duration > threshold)
- Data validation failures (validation_score < 0.8)

### Performance Monitoring
Track these metrics over time:
- Pipeline execution frequency
- Average task duration
- Error rate percentage
- Resource utilization correlation

### Log Retention
Configure index lifecycle management:
- Keep daily indices for 30 days
- Archive monthly for 1 year
- Automated cleanup of old logs

## 🎉 Next Steps

1. **Run the setup**: `./setup-log-forwarding.sh`
2. **Generate test logs**: Wait for cron or run manual workflow
3. **Explore Kibana**: Create custom visualizations
4. **Set up alerts**: Monitor for anomalies
5. **Optimize**: Adjust retention and performance settings

Your ML pipeline logs are now flowing to Kibana! 📊✨ 