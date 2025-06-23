# ML Pipeline Dashboard Setup Guide

## Quick Dashboard Creation

1. **Save your current search first**:
   - In Discover with `kubernetes.pod.name:*ml-pipeline-cron*` filter
   - Click "Save" → Name: "ML Pipeline Cron Logs"

2. **Create Dashboard**:
   - Go to Analytics → Dashboard → Create dashboard
   - Click "Add panel" → "Add from library"
   - Select your saved search "ML Pipeline Cron Logs"

3. **Add Visualizations**:
   - **Timeline**: Add another panel → Lens → Line chart
     - X-axis: @timestamp (date histogram)
     - Y-axis: Count of records
     - Filter: kubernetes.pod.name:*ml-pipeline-cron*
   
   - **Task Breakdown**: Add panel → Lens → Pie chart
     - Slice by: kubernetes.pod.name (top values)
     - Size by: Count of records

4. **Save Dashboard**:
   - Name: "ML Pipeline Monitoring"
   - Set as default: Pin to top of Analytics menu

## Useful Dashboard Panels

### Panel 1: Recent ML Pipeline Logs
- Type: Saved search
- Filter: `kubernetes.pod.name:*ml-pipeline-cron*`
- Time range: Last 4 hours

### Panel 2: Pipeline Execution Timeline  
- Type: Line chart
- X-axis: @timestamp (1 minute intervals)
- Y-axis: Count
- Split series by: kubernetes.pod.name

### Panel 3: Workflow Status
- Type: Data table
- Columns: @timestamp, kubernetes.pod.name, message
- Filter: `message:*✅* OR message:*❌*`
- Rows: Top 10

### Panel 4: Error Detection
- Type: Metric
- Count of: `message:*error* OR message:*failed*`
- Color: Red if > 0

## Quick Access Setup

1. **Bookmark the dashboard URL**
2. **Pin dashboard** to Kibana navigation
3. **Set as landing page** in Kibana advanced settings 