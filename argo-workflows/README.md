# 🚀 Argo Workflows Monitoring

## **TL;DR - What You Need** ⚡

**For simple, portable monitoring (RECOMMENDED):**
```bash
cd simple-monitoring/
docker-compose up -d
# Dashboard: http://localhost:8000
```

**That's it!** ✅ No Elasticsearch, no Grafana complexity.

## 📁 **Directory Structure**

```
argo-workflows/
├── simple-monitoring/     # ✅ USE THIS - Simple, portable solution
│   ├── workflow_monitor.py    # Main monitoring app
│   ├── templates/dashboard.html  # Web dashboard
│   ├── Dockerfile            # Easy deployment
│   ├── docker-compose.yml    # One-command setup
│   └── README.md            # Full deployment guide
├── archive/               # ❌ Old complex ELK stack approach
└── README.md             # This file
```

## 🎯 **Why Simple Monitoring?**

| Feature | Simple Solution | ELK Stack (archived) |
|---------|----------------|----------------------|
| **Setup Time** | 5 minutes | 2-3 hours |
| **Dependencies** | Python + SQLite | Elasticsearch + Grafana |
| **Resource Usage** | ~100MB RAM | ~2GB RAM |
| **Cloud → On-Prem** | Copy files | Reconfigure everything |
| **Maintenance** | Minimal | High |

## 🚀 **Quick Start**

### **Option 1: Docker (Recommended)**
```bash
cd simple-monitoring/
docker-compose up -d
```
**Dashboard:** http://localhost:8000

### **Option 2: Local Development**
```bash
cd simple-monitoring/
pip install -r requirements.txt
python create_sample_data.py  # Create test data
python workflow_monitor.py
```

## 📊 **What You Get**

- **Real-time dashboard** with workflow performance charts
- **Task duration analysis** for ML/CV pipeline optimization
- **SQLite database** (upgrade to PostgreSQL for production)
- **REST API** for integration with other tools
- **Docker deployment** ready for cloud or on-prem

## 🔄 **Migration Strategy**

1. **Deploy online** - Test with internet access
2. **Collect real data** - Run your ML/CV workflows
3. **Package & migrate** - Copy to secure on-prem environment
4. **Zero refactoring** - Same code, different environment

## 📈 **Performance Data Example**

From actual ML/CV pipeline execution:
- **validate-inputs**: 35s (bottleneck identified!)
- **process-images**: 11s (optimized)
- **model-training**: 41s (acceptable)
- **Total pipeline**: 96s (baseline established)

## 🔗 **Integration**

Works seamlessly with your existing:
- **S3Utils** for model artifact storage
- **Kubernetes** clusters (cloud or on-prem)
- **CI/CD** pipelines
- **Alerting** systems via REST API

---

**For the simple monitoring solution, see: [`simple-monitoring/README.md`](simple-monitoring/README.md)**

**Old complex approach archived in: [`archive/`](archive/)** 