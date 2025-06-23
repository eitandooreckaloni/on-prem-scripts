# 🚀 Argo Workflows → Kibana Duration Analytics Guide

This guide shows you how to use the new **duration-focused Kibana integration** to understand and optimize your workflow and task performance.

## 🎯 What You Get

Your workflow monitoring is now enhanced with:

- **📊 Real-time duration tracking** for workflows and individual tasks
- **📈 Performance trend analysis** with historical data visualization
- **🔥 Duration heatmaps** showing performance patterns by time of day/week
- **🐌 Bottleneck identification** - longest running workflows and tasks
- **⚡ Efficiency analysis** - duration vs task count correlation
- **📋 Comprehensive dashboards** in both your existing monitor and Kibana

## 🚀 Quick Start

### 1. Setup the Integration
```bash
cd argo-workflows
chmod +x setup-kibana-integration.sh
./setup-kibana-integration.sh
```

This will:
- ✅ Start Elasticsearch & Kibana
- ✅ Install Python dependencies
- ✅ Setup Kibana dashboard
- ✅ Start enhanced workflow monitor

### 2. Access Your Dashboards

**Enhanced Workflow Monitor**: http://localhost:8000
- Same familiar interface + new Kibana sync capabilities

**Kibana Duration Analytics**: http://localhost:5601 
- Username: `elastic`
- Password: `password`
- Navigate to: **Dashboard → 🚀 Argo Workflows - Duration Analytics Dashboard**

## 📊 Understanding Your Duration Data

### Key Visualizations

#### 📈 Workflow Duration Trend
- **What**: Shows avg/max workflow duration over time
- **Use**: Identify performance degradation or improvements
- **Look for**: Upward trends (performance issues) or spikes

#### ⚡ Task Duration Trend by Task Name  
- **What**: Individual task performance over time
- **Use**: Find which tasks are getting slower
- **Look for**: Tasks with increasing duration trends

#### 🔥 Duration Heatmap (Hour vs Day)
- **What**: Performance patterns by time
- **Use**: Identify when workflows run slower/faster
- **Look for**: Red areas = slow periods, optimize scheduling

#### 🐌 Longest Running Workflows/Tasks
- **What**: Tables showing highest duration workflows and tasks
- **Use**: Focus optimization efforts on biggest bottlenecks
- **Action**: Investigate why these are slow

#### ⚡ Workflow Efficiency (Duration vs Task Count)
- **What**: Scatter plot showing if more tasks = longer duration
- **Use**: Understand workflow complexity impact
- **Look for**: Outliers (workflows with few tasks but long duration)

## 🛠️ Daily Usage Workflows

### Collect & Sync Data
```bash
# Collect new workflow data from Argo
curl -X POST http://localhost:8000/api/collect

# Send duration metrics to Kibana
curl -X POST http://localhost:8000/api/kibana/sync

# Check sync status
curl http://localhost:8000/api/kibana/status
```

### Get Duration Insights
```bash
# Get duration summary for last 7 days
curl http://localhost:8000/api/kibana/summary?days=7

# Get performance data for specific workflow
curl http://localhost:8000/api/workflow/ml-pipeline-cron/trends?days=30
```

### Monitor Health
```bash
# Check if everything is working
curl http://localhost:8000/health
curl http://localhost:8000/api/kibana/status
```

## 📈 Advanced Kibana Queries

### Finding Performance Issues

**Find slow workflows in last 24h**:
```kql
metric_type:"workflow_duration" AND duration_minutes:>10 AND @timestamp:[now-24h TO now]
```

**Identify tasks taking >5 minutes**:
```kql
metric_type:"task_duration" AND duration_minutes:>5
```

**Find workflows with many failures**:
```kql
metric_type:"workflow_duration" AND status:"Failed"
```

**Compare performance by environment**:
```kql
metric_type:"workflow_duration" AND environment:("development" OR "production")
```

### Creating Custom Visualizations

1. **Go to Visualize** in Kibana
2. **Select your index**: `argo-metrics-workflows-*` or `argo-metrics-tasks-*`
3. **Choose visualization type**: Line chart, Bar chart, etc.
4. **Configure aggregations**:
   - Metrics: `avg` or `max` of `duration_minutes`
   - Buckets: `terms` on `workflow_name` or `task_name`

## 🔧 Customization & Troubleshooting

### Adjust Collection Frequency

Edit the background collector in `workflow_monitor.py`:
```python
await asyncio.sleep(60)  # Collect every minute (change as needed)
```

### Custom Dashboard Import

If you want to modify the dashboard:
1. Edit `kibana-duration-dashboard.json`
2. Import in Kibana: **Management → Saved Objects → Import**

### Log Analysis

Monitor the integration:
```bash
# Monitor workflow monitor logs
tail -f simple-monitoring/monitor.log

# Check Elasticsearch logs
docker logs elastic-setup-elasticsearch-1

# Check Kibana logs  
docker logs elastic-setup-kibana-1
```

### Common Issues

**"Kibana integration not available"**:
```bash
cd simple-monitoring
pip install elasticsearch==8.11.1
```

**Connection refused to Elasticsearch**:
```bash
cd ../elastic-setup
docker compose up -d elasticsearch
# Wait 30 seconds then retry
```

**No data in Kibana**:
```bash
# Collect some workflow data first
curl -X POST http://localhost:8000/api/collect
curl -X POST http://localhost:8000/api/kibana/sync
```

## 📊 Dashboard Panels Explained

### **📈 Workflow Duration Trend**
Tracks your workflow performance over time. Look for:
- **Rising trends**: Performance degradation
- **Spikes**: Investigate specific time periods
- **Patterns**: Regular slow periods

### **⚡ Task Duration Trend** 
Shows which individual tasks are slow. Use to:
- **Identify bottlenecks**: Tasks with consistently high duration
- **Track improvements**: After optimization efforts
- **Compare templates**: Different task types performance

### **🔥 Duration Heatmap**
Reveals performance patterns by time. Useful for:
- **Scheduling optimization**: Avoid slow periods
- **Resource planning**: High-performance time slots
- **Capacity planning**: When system is under stress

### **📊 Longest Running Items**
Tables showing your biggest performance issues:
- **Focus optimization**: Start with highest impact items
- **Resource allocation**: Understand which workflows need more resources
- **Architecture decisions**: Consider breaking up long workflows

## 🎯 Performance Optimization Tips

### Based on Dashboard Insights

1. **Long workflows → Break into smaller pieces**
   - Look at "Longest Running Workflows"
   - Consider parallel execution

2. **Slow tasks → Optimize or scale**  
   - Check "Longest Running Tasks"
   - Add more CPU/memory or optimize code

3. **Time patterns → Adjust scheduling**
   - Use heatmap to avoid slow periods
   - Schedule heavy workflows during fast periods

4. **Efficiency issues → Review architecture**
   - Use efficiency scatter plot
   - Workflows with few tasks but long duration need investigation

### Setting Up Alerts

Create Kibana alerts for:
- Workflow duration exceeding thresholds
- Task duration anomalies
- Performance degradation trends

## 🌟 Next Steps

1. **Run for a week** to gather baseline data
2. **Identify your top 3 bottlenecks** using the dashboard
3. **Set up alerts** for performance regressions
4. **Create custom dashboards** for specific workflows
5. **Schedule regular reviews** of performance trends

---

**Need help?** Check the logs, ensure services are running, and verify your Argo workflows are executing and being collected by the monitor.

**🎉 Happy optimizing!** Your workflow performance insights are now just a dashboard away. 