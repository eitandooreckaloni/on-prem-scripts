#!/usr/bin/env python3
"""
Simple Argo Workflows Monitor

A lightweight, portable monitoring solution that:
- Uses SQLite (no complex database setup)
- Built-in web dashboard (no Grafana needed)
- Easy to deploy online or on-prem
- Minimal dependencies
"""

import sqlite3
import json
import subprocess
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
import pandas as pd
import plotly.graph_objs as go
import plotly.utils
import uvicorn


class SimpleWorkflowMonitor:
    """Lightweight workflow monitoring with SQLite backend"""
    
    def __init__(self, db_path: str = "workflow_metrics.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with workflow and task tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Workflows table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                uid TEXT UNIQUE NOT NULL,
                namespace TEXT,
                status TEXT,
                created_at TIMESTAMP,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                duration_seconds REAL,
                task_count INTEGER,
                labels TEXT,
                environment TEXT DEFAULT 'development',
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_uid TEXT NOT NULL,
                workflow_name TEXT,
                task_name TEXT,
                task_id TEXT,
                phase TEXT,
                template_name TEXT,
                host_node TEXT,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                duration_seconds REAL,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workflow_uid) REFERENCES workflows (uid)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_workflows_created_at ON workflows(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_workflow_uid ON tasks(workflow_uid)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_task_name ON tasks(task_name)')
        
        conn.commit()
        conn.close()
    
    def collect_workflow_data(self, namespace: str = "argo") -> int:
        """Collect workflow data from Argo CLI and store in database"""
        try:
            # Get list of workflows
            result = subprocess.run([
                'argo', 'list', '-n', namespace, '-o', 'json'
            ], capture_output=True, text=True, check=True)
            
            workflows_data = json.loads(result.stdout)
            collected_count = 0
            
            if workflows_data and 'items' in workflows_data:
                for workflow in workflows_data['items']:
                    if self._store_workflow(workflow, namespace):
                        collected_count += 1
            
            return collected_count
            
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Error collecting workflow data: {e}")
            return 0
    
    def _store_workflow(self, workflow_data: dict, namespace: str) -> bool:
        """Store individual workflow data in database"""
        try:
            metadata = workflow_data.get('metadata', {})
            status = workflow_data.get('status', {})
            
            workflow_uid = metadata.get('uid')
            if not workflow_uid:
                return False
            
            # Check if workflow already exists
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM workflows WHERE uid = ?', (workflow_uid,))
            if cursor.fetchone():
                conn.close()
                return False  # Already exists
            
            # Parse timestamps
            created_at = self._parse_timestamp(metadata.get('creationTimestamp'))
            started_at = self._parse_timestamp(status.get('startedAt'))
            finished_at = self._parse_timestamp(status.get('finishedAt'))
            
            # Calculate duration
            duration_seconds = None
            if started_at and finished_at:
                duration_seconds = (finished_at - started_at).total_seconds()
            
            # Store workflow
            cursor.execute('''
                INSERT INTO workflows 
                (name, uid, namespace, status, created_at, started_at, finished_at, 
                 duration_seconds, task_count, labels, environment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metadata.get('name'),
                workflow_uid,
                namespace,
                status.get('phase'),
                created_at,
                started_at,
                finished_at,
                duration_seconds,
                len(status.get('nodes', {})),
                json.dumps(metadata.get('labels', {})),
                os.getenv('ENVIRONMENT', 'development')
            ))
            
            # Store tasks
            self._store_tasks(cursor, workflow_uid, metadata.get('name'), status.get('nodes', {}))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error storing workflow {workflow_data.get('metadata', {}).get('name', 'unknown')}: {e}")
            return False
    
    def _store_tasks(self, cursor, workflow_uid: str, workflow_name: str, nodes: dict):
        """Store task data for a workflow"""
        for node_id, node_data in nodes.items():
            if node_data.get('type') in ['Pod', 'Container']:
                started_at = self._parse_timestamp(node_data.get('startedAt'))
                finished_at = self._parse_timestamp(node_data.get('finishedAt'))
                
                duration_seconds = None
                if started_at and finished_at:
                    duration_seconds = (finished_at - started_at).total_seconds()
                
                cursor.execute('''
                    INSERT INTO tasks 
                    (workflow_uid, workflow_name, task_name, task_id, phase, 
                     template_name, host_node, started_at, finished_at, duration_seconds)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    workflow_uid,
                    workflow_name,
                    node_data.get('displayName', node_data.get('name')),
                    node_id,
                    node_data.get('phase'),
                    node_data.get('templateName'),
                    node_data.get('hostNodeName'),
                    started_at,
                    finished_at,
                    duration_seconds
                ))
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse Kubernetes timestamp to datetime"""
        if not timestamp_str:
            return None
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            return None
    
    def get_workflow_stats(self, days: int = 7) -> Dict:
        """Get workflow statistics for dashboard"""
        conn = sqlite3.connect(self.db_path)
        
        # Workflow counts by status
        status_query = '''
            SELECT status, COUNT(*) as count 
            FROM workflows 
            WHERE created_at >= datetime('now', '-{} days')
            GROUP BY status
        '''.format(days)
        
        status_df = pd.read_sql_query(status_query, conn)
        
        # Average durations by workflow name
        duration_query = '''
            SELECT name, AVG(duration_seconds) as avg_duration
            FROM workflows 
            WHERE duration_seconds IS NOT NULL 
            AND created_at >= datetime('now', '-{} days')
            GROUP BY name
            ORDER BY avg_duration DESC
        '''.format(days)
        
        duration_df = pd.read_sql_query(duration_query, conn)
        duration_df = duration_df.fillna(0)  # Replace NaN with 0
        
        # Task duration trends
        task_query = '''
            SELECT task_name, AVG(duration_seconds) as avg_duration, COUNT(*) as count
            FROM tasks 
            WHERE duration_seconds IS NOT NULL
            AND collected_at >= datetime('now', '-{} days')
            GROUP BY task_name
            ORDER BY avg_duration DESC
        '''.format(days)
        
        task_df = pd.read_sql_query(task_query, conn)
        task_df = task_df.fillna(0)  # Replace NaN with 0
        
        # Recent workflows
        recent_query = '''
            SELECT name, status, duration_seconds, created_at, task_count
            FROM workflows 
            ORDER BY created_at DESC 
            LIMIT 10
        '''
        
        recent_df = pd.read_sql_query(recent_query, conn)
        recent_df = recent_df.fillna(0)  # Replace NaN with 0
        
        conn.close()
        
        return {
            'status_counts': status_df.to_dict('records'),
            'workflow_durations': duration_df.to_dict('records'),
            'task_durations': task_df.to_dict('records'),
            'recent_workflows': recent_df.to_dict('records')
        }
    
    def get_workflow_timeline(self, days: int = 1) -> List[Dict]:
        """Get workflow execution timeline"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT name, started_at, finished_at, duration_seconds, status
            FROM workflows 
            WHERE started_at IS NOT NULL 
            AND started_at >= datetime('now', '-{} days')
            ORDER BY started_at DESC
        '''.format(days)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df.to_dict('records')

    def detect_anomalies(self, days: int = 7) -> Dict:
        """Detect performance anomalies in workflows and tasks"""
        conn = sqlite3.connect(self.db_path)
        
        # Get workflow duration statistics
        workflow_query = '''
            SELECT name, duration_seconds, 
                   AVG(duration_seconds) OVER (PARTITION BY name) as avg_duration,
                   created_at
            FROM workflows 
            WHERE duration_seconds IS NOT NULL 
            AND duration_seconds > 0
            AND created_at >= datetime('now', '-{} days')
        '''.format(days)
        
        workflow_df = pd.read_sql_query(workflow_query, conn)
        
        # Get task duration statistics  
        task_query = '''
            SELECT w.name as workflow_name, t.task_name, t.duration_seconds,
                   AVG(t.duration_seconds) OVER (PARTITION BY t.task_name) as avg_duration,
                   w.created_at
            FROM tasks t
            JOIN workflows w ON t.workflow_uid = w.uid
            WHERE t.duration_seconds IS NOT NULL 
            AND t.duration_seconds > 0
            AND w.created_at >= datetime('now', '-{} days')
        '''.format(days)
        
        task_df = pd.read_sql_query(task_query, conn)
        conn.close()
        
        workflow_anomalies = []
        task_anomalies = []
        
        # Detect workflow anomalies (duration > 2 * average)
        if not workflow_df.empty:
            workflow_df['is_anomaly'] = workflow_df['duration_seconds'] > (2 * workflow_df['avg_duration'])
            workflow_anomalies = workflow_df[workflow_df['is_anomaly']].to_dict('records')
        
        # Detect task anomalies
        if not task_df.empty:
            task_df['is_anomaly'] = task_df['duration_seconds'] > (2 * task_df['avg_duration'])
            task_anomalies = task_df[task_df['is_anomaly']].to_dict('records')
        
        return {
            'workflow_anomalies': workflow_anomalies,
            'task_anomalies': task_anomalies,
            'total_anomalies': len(workflow_anomalies) + len(task_anomalies)
        }

    def get_workflow_names(self) -> List[str]:
        """Get list of unique workflow names"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT DISTINCT name 
            FROM workflows 
            WHERE name IS NOT NULL 
            ORDER BY name
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df['name'].tolist()

    def get_task_names(self) -> List[str]:
        """Get list of unique task names"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT DISTINCT task_name 
            FROM tasks 
            WHERE task_name IS NOT NULL 
            ORDER BY task_name
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df['task_name'].tolist()

    def get_filtered_workflows(self, workflow_name: str = None, task_name: str = None, 
                             days: int = 7, limit: int = 200) -> Dict:
        """Get filtered workflow data"""
        conn = sqlite3.connect(self.db_path)
        
        # Build dynamic query
        conditions = []
        params = []
        
        if workflow_name:
            conditions.append("w.name = ?")
            params.append(workflow_name)
        
        if task_name:
            conditions.append("t.task_name = ?")
            params.append(task_name)
        
        conditions.append("w.created_at >= datetime('now', '-{} days')".format(days))
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        if task_name:
            # Query with task filter
            query = f'''
                SELECT DISTINCT w.name, w.status, w.duration_seconds, w.created_at, 
                       w.uid, COUNT(t.task_name) as task_count
                FROM workflows w
                JOIN tasks t ON w.uid = t.workflow_uid
                {where_clause}
                GROUP BY w.uid
                ORDER BY w.created_at DESC
                LIMIT ?
            '''
            params.append(limit)
        else:
            # Query without task filter
            query = f'''
                SELECT w.name, w.status, w.duration_seconds, w.created_at, 
                       w.uid, COUNT(t.task_name) as task_count
                FROM workflows w
                LEFT JOIN tasks t ON w.uid = t.workflow_uid
                {where_clause}
                GROUP BY w.uid
                ORDER BY w.created_at DESC
                LIMIT ?
            '''
            params.append(limit)
        
        workflows_df = pd.read_sql_query(query, conn, params=params)
        
        # Get associated tasks
        if not workflows_df.empty:
            workflow_uids = workflows_df['uid'].tolist()
            placeholders = ','.join(['?' for _ in workflow_uids])
            
            tasks_query = f'''
                SELECT t.*, w.name as workflow_name
                FROM tasks t
                JOIN workflows w ON t.workflow_uid = w.uid
                WHERE t.workflow_uid IN ({placeholders})
                ORDER BY t.started_at DESC
            '''
            
            tasks_df = pd.read_sql_query(tasks_query, conn, params=workflow_uids)
        else:
            tasks_df = pd.DataFrame()
        
        conn.close()
        
        return {
            'workflows': workflows_df.fillna(0).to_dict('records'),
            'tasks': tasks_df.fillna(0).to_dict('records'),
            'total_workflows': len(workflows_df),
            'total_tasks': len(tasks_df)
        }

    def get_performance_data(self, days: int = 7) -> Dict:
        """Get performance comparison data"""
        conn = sqlite3.connect(self.db_path)
        
        # Get workflow performance trends
        performance_query = '''
            SELECT name, 
                   AVG(duration_seconds) as avg_duration,
                   MIN(duration_seconds) as min_duration,
                   MAX(duration_seconds) as max_duration,
                   COUNT(*) as execution_count,
                   COUNT(CASE WHEN status = 'Succeeded' THEN 1 END) as success_count,
                   COUNT(CASE WHEN status = 'Failed' THEN 1 END) as failure_count
            FROM workflows 
            WHERE duration_seconds IS NOT NULL 
            AND duration_seconds > 0
            AND created_at >= datetime('now', '-{} days')
            GROUP BY name
            ORDER BY avg_duration DESC
        '''.format(days)
        
        performance_df = pd.read_sql_query(performance_query, conn)
        conn.close()
        
        # Calculate success rates
        if not performance_df.empty:
            performance_df['success_rate'] = (performance_df['success_count'] / performance_df['execution_count'] * 100).round(1)
        
        return {
            'workflow_performance': performance_df.fillna(0).to_dict('records')
        }

    def get_workflow_details(self, workflow_uid: str) -> Dict:
        """Get detailed information about a specific workflow including steps"""
        conn = sqlite3.connect(self.db_path)
        
        # Get workflow info
        workflow_query = '''
            SELECT * FROM workflows WHERE uid = ?
        '''
        workflow_df = pd.read_sql_query(workflow_query, conn, params=[workflow_uid])
        
        if workflow_df.empty:
            conn.close()
            return {'error': 'Workflow not found'}
        
        workflow = workflow_df.iloc[0].to_dict()
        
        # Get workflow steps/tasks
        tasks_query = '''
            SELECT * FROM tasks 
            WHERE workflow_uid = ?
            ORDER BY started_at ASC
        '''
        tasks_df = pd.read_sql_query(tasks_query, conn, params=[workflow_uid])
        
        # Get historical performance for this workflow name
        historical_query = '''
            SELECT AVG(duration_seconds) as avg_duration,
                   STDDEV(duration_seconds) as std_duration,
                   COUNT(*) as historical_count
            FROM workflows 
            WHERE name = ? 
            AND duration_seconds IS NOT NULL 
            AND duration_seconds > 0
            AND uid != ?
        '''
        historical_df = pd.read_sql_query(historical_query, conn, params=[workflow['name'], workflow_uid])
        
        # Get historical task performance
        task_historical_query = '''
            SELECT t.task_name,
                   AVG(t.duration_seconds) as avg_duration,
                   STDDEV(t.duration_seconds) as std_duration,
                   COUNT(*) as execution_count
            FROM tasks t
            JOIN workflows w ON t.workflow_uid = w.uid
            WHERE w.name = ?
            AND t.duration_seconds IS NOT NULL
            AND t.duration_seconds > 0
            GROUP BY t.task_name
        '''
        task_historical_df = pd.read_sql_query(task_historical_query, conn, params=[workflow['name']])
        
        conn.close()
        
        # Calculate performance metrics
        historical_avg = historical_df.iloc[0]['avg_duration'] if not historical_df.empty else None
        historical_std = historical_df.iloc[0]['std_duration'] if not historical_df.empty else None
        
        performance_comparison = None
        if historical_avg and workflow['duration_seconds']:
            deviation = workflow['duration_seconds'] - historical_avg
            performance_comparison = {
                'current_duration': workflow['duration_seconds'],
                'historical_avg': historical_avg,
                'historical_std': historical_std,
                'deviation_seconds': deviation,
                'deviation_percent': (deviation / historical_avg * 100) if historical_avg > 0 else 0,
                'performance_level': 'fast' if deviation < -historical_std else 'slow' if deviation > historical_std else 'normal'
            }
        
        # Add task performance comparisons
        tasks_with_comparison = []
        for _, task in tasks_df.iterrows():
            task_dict = task.to_dict()
            
            # Find historical data for this task
            historical_task = task_historical_df[task_historical_df['task_name'] == task['task_name']]
            if not historical_task.empty and task['duration_seconds']:
                hist_avg = historical_task.iloc[0]['avg_duration']
                hist_std = historical_task.iloc[0]['std_duration']
                if hist_avg:
                    task_deviation = task['duration_seconds'] - hist_avg
                    task_dict['performance_comparison'] = {
                        'historical_avg': hist_avg,
                        'historical_std': hist_std,
                        'deviation_seconds': task_deviation,
                        'deviation_percent': (task_deviation / hist_avg * 100) if hist_avg > 0 else 0,
                        'performance_level': 'fast' if task_deviation < -hist_std else 'slow' if task_deviation > hist_std else 'normal'
                    }
            
            tasks_with_comparison.append(task_dict)
        
        return {
            'workflow': workflow,
            'tasks': tasks_with_comparison,
            'performance_comparison': performance_comparison,
            'task_count': len(tasks_with_comparison),
            'historical_executions': historical_df.iloc[0]['historical_count'] if not historical_df.empty else 0
        }

    def get_workflow_trends(self, workflow_name: str, days: int = 30) -> Dict:
        """Get performance trends for a specific workflow"""
        conn = sqlite3.connect(self.db_path)
        
        # Get workflow execution history
        trend_query = '''
            SELECT uid, name, duration_seconds, created_at, status,
                   ROW_NUMBER() OVER (ORDER BY created_at) as execution_number
            FROM workflows 
            WHERE name = ?
            AND created_at >= datetime('now', '-{} days')
            ORDER BY created_at ASC
        '''.format(days)
        
        trend_df = pd.read_sql_query(trend_query, conn, params=[workflow_name])
        
        # Get rolling average (last 5 executions)
        if not trend_df.empty and len(trend_df) > 1:
            trend_df['rolling_avg'] = trend_df['duration_seconds'].rolling(window=min(5, len(trend_df)), min_periods=1).mean()
        
        conn.close()
        
        return {
            'workflow_name': workflow_name,
            'executions': trend_df.fillna(0).to_dict('records'),
            'total_executions': len(trend_df),
            'avg_duration': trend_df['duration_seconds'].mean() if not trend_df.empty else 0,
            'trend_direction': 'improving' if len(trend_df) > 5 and trend_df['duration_seconds'].tail(3).mean() < trend_df['duration_seconds'].head(3).mean() else 'stable'
        }


# Global monitor instance
# Ensure the /data directory exists
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, "data")
os.makedirs(data_dir, exist_ok=True)
db_path = os.path.join(data_dir, "workflow_metrics.db")

monitor = SimpleWorkflowMonitor(db_path=db_path)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    task = asyncio.create_task(background_collector())
    yield
    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

# FastAPI Application
app = FastAPI(title="Argo Workflows Monitor", version="1.0.0", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard"""
    stats = monitor.get_workflow_stats(days=7)
    
    # Create simple charts
    charts = create_dashboard_charts(stats)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "charts": charts
    })

@app.get("/api/stats")
async def get_stats(days: int = 7):
    """API endpoint for workflow statistics"""
    return monitor.get_workflow_stats(days)

@app.get("/api/timeline")
async def get_timeline(days: int = 1):
    """API endpoint for workflow timeline"""
    return monitor.get_workflow_timeline(days)

@app.post("/api/collect")
async def collect_data(background_tasks: BackgroundTasks, namespace: str = "argo"):
    """Trigger data collection"""
    background_tasks.add_task(monitor.collect_workflow_data, namespace)
    return {"message": "Collection started"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/anomalies")
async def get_anomalies(days: int = 7):
    """API endpoint for anomaly detection"""
    return monitor.detect_anomalies(days)

@app.get("/api/workflows/names")
async def get_workflow_names():
    """API endpoint for workflow names"""
    return monitor.get_workflow_names()

@app.get("/api/tasks/names")
async def get_task_names():
    """API endpoint for task names"""
    return monitor.get_task_names()

@app.get("/api/workflows/filtered")
async def get_filtered_workflows(
    workflow_name: str = None,
    task_name: str = None,
    days: int = 7,
    limit: int = 200
):
    """API endpoint for filtered workflows"""
    return monitor.get_filtered_workflows(workflow_name, task_name, days, limit)

@app.get("/api/performance")
async def get_performance_data(days: int = 7):
    """API endpoint for performance comparison data"""
    return monitor.get_performance_data(days)

@app.get("/api/workflow/{workflow_uid}")
async def get_workflow_detail(workflow_uid: str):
    """API endpoint for detailed workflow information"""
    return monitor.get_workflow_details(workflow_uid)

@app.get("/api/workflow/{workflow_name}/trends")
async def get_workflow_trend(workflow_name: str, days: int = 30):
    """API endpoint for workflow performance trends"""
    return monitor.get_workflow_trends(workflow_name, days)


def create_dashboard_charts(stats: Dict) -> Dict:
    """Create comprehensive Plotly charts for dashboard"""
    charts = {}
    
    # Workflow status pie chart
    if stats['status_counts']:
        status_data = stats['status_counts']
        fig = go.Figure(data=[go.Pie(
            labels=[item['status'] for item in status_data],
            values=[item['count'] for item in status_data],
            hole=0.3,
            marker_colors=['#28a745', '#dc3545', '#ffc107', '#17a2b8']
        )])
        fig.update_layout(
            title="Workflow Status Distribution",
            height=400,
            showlegend=True
        )
        charts['status_pie'] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Workflow duration bar chart
    if stats['workflow_durations']:
        duration_data = stats['workflow_durations']
        fig = go.Figure(data=[go.Bar(
            x=[item['name'] for item in duration_data],
            y=[item['avg_duration'] for item in duration_data],
            marker_color='#667eea',
            text=[f"{item['avg_duration']:.1f}s" for item in duration_data],
            textposition='auto'
        )])
        fig.update_layout(
            title="Average Workflow Duration",
            xaxis_title="Workflow Name",
            yaxis_title="Duration (seconds)",
            height=400
        )
        charts['duration_bar'] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Task duration breakdown chart
    if stats['task_durations']:
        task_data = stats['task_durations']
        fig = go.Figure(data=[go.Bar(
            x=[item['task_name'] for item in task_data],
            y=[item['avg_duration'] for item in task_data],
            marker_color=['#28a745' if item['avg_duration'] < 30 else 
                         '#ffc107' if item['avg_duration'] < 120 else '#dc3545' 
                         for item in task_data],
            text=[f"{item['avg_duration']:.1f}s" for item in task_data],
            textposition='auto'
        )])
        fig.update_layout(
            title="Task Performance Breakdown",
            xaxis_title="Task Name",
            yaxis_title="Average Duration (seconds)",
            height=400,
            xaxis_tickangle=-45
        )
        charts['task_breakdown'] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Workflow timeline/duration over time
    if stats['recent_workflows']:
        timeline_data = [wf for wf in stats['recent_workflows'] if wf['duration_seconds'] and wf['duration_seconds'] > 0]
        if timeline_data:
            fig = go.Figure()
            
            # Group by workflow name for different traces
            workflow_names = list(set([wf['name'] for wf in timeline_data]))
            colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe']
            
            for i, wf_name in enumerate(workflow_names):
                wf_data = [wf for wf in timeline_data if wf['name'] == wf_name]
                fig.add_trace(go.Scatter(
                    x=[wf['created_at'] for wf in wf_data],
                    y=[wf['duration_seconds'] for wf in wf_data],
                    mode='markers+lines',
                    name=wf_name,
                    marker=dict(size=10, color=colors[i % len(colors)]),
                    line=dict(width=2, color=colors[i % len(colors)])
                ))
            
            fig.update_layout(
                title="Workflow Duration Timeline",
                xaxis_title="Execution Time",
                yaxis_title="Duration (seconds)",
                height=400,
                hovermode='closest'
            )
            charts['timeline'] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return charts


async def background_collector():
    """Background task to collect workflow data periodically"""
    while True:
        try:
            collected = monitor.collect_workflow_data()
            print(f"Collected {collected} workflows at {datetime.now()}")
        except Exception as e:
            print(f"Collection error: {e}")
        
        await asyncio.sleep(60)  # Collect every minute


if __name__ == "__main__":
    # Run the app
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=int(os.getenv("PORT", 8000)),
        reload=False
    ) 