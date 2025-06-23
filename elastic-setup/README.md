# 🔍 Elasticsearch Setup

Complete Elasticsearch and Kibana setup using centralized version management.

## 📋 Overview

This directory contains scripts to set up Elasticsearch **version 8.17.0** (from centralized `versions.sh`) with Kibana for your on-premises infrastructure.

## 🚀 Quick Start

1. **Install Elasticsearch**:
   ```bash
   ./install-elasticsearch.sh
   ```

2. **Configure passwords** in `.env` file:
   ```bash
   # Edit .env file and update passwords
   nano .env
   ```

3. **Start services**:
   ```bash
   ./start-elasticsearch.sh
   ```

4. **Setup users and roles**:
   ```bash
   ./setup-users.sh
   ```

5. **Open Kibana**:
   ```bash
   ./open-kibana.sh
   ```

## 📁 Files

| Script | Description |
|--------|-------------|
| `install-elasticsearch.sh` | Initial setup and configuration |
| `start-elasticsearch.sh` | Start Elasticsearch and Kibana |
| `stop-elasticsearch.sh` | Stop all services |
| `setup-users.sh` | Configure users and roles |
| `open-kibana.sh` | Open Kibana in browser |
| `check-elastic-status.sh` | Check system status |
| `docker-compose.yml` | Docker composition (generated) |
| `.env` | Environment variables (generated) |

## 🔧 Configuration

### Generated Files

- **`docker-compose.yml`**: Docker services configuration
- **`.env`**: Environment variables and passwords
- **`config/elasticsearch.yml`**: Elasticsearch configuration
- **`config/kibana/kibana.yml`**: Kibana configuration
- **`data/`**: Elasticsearch data directory
- **`logs/`**: Elasticsearch logs directory

### Version Management

All versions are managed centrally via `../versions.sh`:
- Elasticsearch: **8.17.0**
- Kibana: **8.17.0**
- Ports: 9200 (Elasticsearch), 5601 (Kibana)

## 👥 Users and Roles

### Default Users Created

| Username | Role | Purpose |
|----------|------|---------|
| `elastic` | superuser | Administrative access |
| `kibana_system` | kibana_system | Kibana service account |
| `monitoring_user` | monitoring_user | System monitoring |
| `workflow_app` | editor | Application integration |
| `readonly_user` | viewer | Read-only access |
| `argo_workflows` | argo_workflows_role | Argo Workflows integration |

### Security Notes

- 🔐 Change default passwords in production
- 🔑 Use API keys for service-to-service authentication
- 🔄 Regularly rotate passwords
- 📊 Monitor user access patterns

## 🌐 Access URLs

- **Elasticsearch**: http://localhost:9200
- **Kibana**: http://localhost:5601

## 📊 Management Commands

### Check Status
```bash
./check-elastic-status.sh
```

### View Logs
```bash
docker-compose logs -f elasticsearch
docker-compose logs -f kibana
```

### Restart Services
```bash
docker-compose restart
```

### Update Configuration
```bash
# Edit configuration files
nano config/elasticsearch.yml
nano config/kibana/kibana.yml

# Restart to apply changes
docker-compose restart
```

## 🔗 Integration Examples

### Argo Workflows Integration

Use the `argo_workflows` user for logging integration:

```yaml
# In your workflow template
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: elasticsearch-logger
spec:
  templates:
  - name: log-to-elastic
    container:
      image: curlimages/curl
      command: [sh, -c]
      args:
        - |
          curl -X POST "http://elasticsearch:9200/workflow-logs/_doc" \
            -u "argo_workflows:argo_workflows_password_123" \
            -H "Content-Type: application/json" \
            -d '{"timestamp":"$(date -Iseconds)","workflow":"{{workflow.name}}","status":"completed"}'
```

### Application Logging

Use the `workflow_app` user for application logs:

```python
import requests
from datetime import datetime

# Log to Elasticsearch
def log_to_elastic(message, level="INFO"):
    doc = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "message": message,
        "application": "my-app"
    }
    
    response = requests.post(
        "http://localhost:9200/app-logs/_doc",
        auth=("workflow_app", "workflow_app_password_123"),
        json=doc
    )
    return response.status_code == 201
```

## 🛠️ Troubleshooting

### Common Issues

#### Elasticsearch won't start
```bash
# Check disk space
df -h

# Check Docker resources
docker system df

# View detailed logs
docker-compose logs elasticsearch
```

#### Permission errors
```bash
# Fix data directory permissions
sudo chown -R 1000:1000 data logs
```

#### Memory issues
Edit `docker-compose.yml` and adjust JVM settings:
```yml
environment:
  - "ES_JAVA_OPTS=-Xms512m -Xmx512m"  # Reduce memory
```

#### Port conflicts
```bash
# Check what's using port 9200
lsof -i :9200

# Or change port in .env file
echo "ELASTICSEARCH_PORT=9201" >> .env
```

### Health Checks

#### Cluster Health
```bash
curl -u elastic:your-password http://localhost:9200/_cluster/health?pretty
```

#### Node Stats
```bash
curl -u elastic:your-password http://localhost:9200/_nodes/stats?pretty
```

#### Index Information
```bash
curl -u elastic:your-password http://localhost:9200/_cat/indices?v
```

## 🔄 Backup and Recovery

### Create Snapshot Repository
```bash
curl -X PUT "localhost:9200/_snapshot/backup_repo" \
  -u "elastic:your-password" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "fs",
    "settings": {
      "location": "/usr/share/elasticsearch/backup"
    }
  }'
```

### Create Snapshot
```bash
curl -X PUT "localhost:9200/_snapshot/backup_repo/snapshot_$(date +%Y%m%d_%H%M%S)" \
  -u "elastic:your-password"
```

## 🔧 Performance Tuning

### Index Templates
Create optimized templates for your data:

```bash
curl -X PUT "localhost:9200/_index_template/logs_template" \
  -u "elastic:your-password" \
  -H "Content-Type: application/json" \
  -d '{
    "index_patterns": ["logs-*", "workflow-*"],
    "template": {
      "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "refresh_interval": "30s"
      }
    }
  }'
```

### Index Lifecycle Management
Set up ILM policies for automatic index management:

```bash
curl -X PUT "localhost:9200/_ilm/policy/logs_policy" \
  -u "elastic:your-password" \
  -H "Content-Type: application/json" \
  -d '{
    "policy": {
      "phases": {
        "hot": {
          "actions": {
            "rollover": {
              "max_size": "1GB",
              "max_age": "1d"
            }
          }
        },
        "delete": {
          "min_age": "30d"
        }
      }
    }
  }'
```

## 📚 Additional Resources

- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/8.17/index.html)
- [Kibana Documentation](https://www.elastic.co/guide/en/kibana/8.17/index.html)
- [Docker Configuration](https://www.elastic.co/guide/en/elasticsearch/reference/8.17/docker.html)
- [Security Configuration](https://www.elastic.co/guide/en/elasticsearch/reference/8.17/security-settings.html)

## 🤝 Integration with Other Tools

This Elasticsearch setup is designed to work with:
- **Argo Workflows**: For workflow execution logging
- **Grafana**: For monitoring dashboards
- **Your applications**: For centralized logging

See `../argo-workflows/` for workflow integration examples. 