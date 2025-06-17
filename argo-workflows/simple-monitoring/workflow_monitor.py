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


# Global monitor instance
monitor = SimpleWorkflowMonitor(db_path="./data/workflow_metrics.db")

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


def create_dashboard_charts(stats: Dict) -> Dict:
    """Create simple Plotly charts for dashboard"""
    charts = {}
    
    # Workflow status pie chart
    if stats['status_counts']:
        status_data = stats['status_counts']
        fig = go.Figure(data=[go.Pie(
            labels=[item['status'] for item in status_data],
            values=[item['count'] for item in status_data],
            hole=0.3
        )])
        fig.update_layout(title="Workflow Status Distribution")
        charts['status_pie'] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Workflow duration bar chart
    if stats['workflow_durations']:
        duration_data = stats['workflow_durations']
        fig = go.Figure(data=[go.Bar(
            x=[item['name'] for item in duration_data],
            y=[item['avg_duration'] for item in duration_data]
        )])
        fig.update_layout(title="Average Workflow Duration (seconds)")
        charts['duration_bar'] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
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