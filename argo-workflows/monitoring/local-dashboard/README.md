# Clean Dashboards

This directory contains clean, minimal dashboards for monitoring:

1. **Argo Workflows Dashboard** - Direct connection to Argo workflows
2. **Kibana Dashboard** - Direct connection to Kibana (coming next)

## Argo Workflows Dashboard

### Features
- ✅ Connection testing to Argo workflows
- 📊 Basic workflow statistics
- 📋 Recent workflows table
- 🔄 Auto-refresh every 30 seconds
- 🎨 Clean, responsive UI

### Prerequisites
- Argo CLI installed and configured
- Python 3.8+
- Argo workflows running in Kubernetes

### Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the dashboard:**
   ```bash
   python argo-dashboard.py
   ```

3. **Open in browser:**
   - Dashboard: http://localhost:8001
   - API docs: http://localhost:8001/docs

### API Endpoints

- `GET /api/test-connection` - Test Argo connection
- `GET /api/workflows?limit=10` - Get recent workflows
- `GET /api/stats` - Get workflow statistics
- `GET /health` - Health check

### Connection Testing

The dashboard includes a prominent "Test Connection" button that will:
- Check if Argo CLI is available
- Verify connection to the specified namespace
- Display connection status and details

### Configuration

The dashboard uses the default Argo namespace (`argo`). To change this, modify the `ArgoConnection` initialization in `argo-dashboard.py`:

```python
argo_conn = ArgoConnection(namespace="your-namespace")
```

## Coming Next

- **Kibana Dashboard** - Clean connection to Kibana for log analysis
- **Combined Dashboard** - Option to view both data sources side by side 