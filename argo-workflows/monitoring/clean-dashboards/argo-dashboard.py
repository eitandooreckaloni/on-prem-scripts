#!/usr/bin/env python3
"""
Clean Argo Workflows Dashboard

A minimal dashboard focused on testing Argo workflows connection
and displaying basic workflow metrics.
"""

import json
import subprocess
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

app = FastAPI(title="Clean Argo Dashboard")
templates = Jinja2Templates(directory="templates")

class ArgoConnection:
    """Simple Argo workflows connection handler"""
    
    def __init__(self, namespace: str = "argo"):
        self.namespace = namespace
        self.db_path = "argo_clean.db"
        self.init_database()
    
    def init_database(self):
        """Initialize simple SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def test_connection(self) -> Dict:
        """Test connection to Argo workflows"""
        try:
            result = subprocess.run([
                'argo', 'list', '-n', self.namespace
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "message": "Successfully connected to Argo workflows",
                    "namespace": self.namespace,
                    "output": result.stdout[:500]  # First 500 chars
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to connect: {result.stderr}",
                    "namespace": self.namespace
                }
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": "Connection timeout after 10 seconds",
                "namespace": self.namespace
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Connection error: {str(e)}",
                "namespace": self.namespace
            }
    
    def get_workflows(self, limit: int = 10) -> List[Dict]:
        """Get workflows from both live Argo and database history"""
        # First get live workflows from Argo
        live_workflows = self._get_live_workflows()
        
        # Store/update live workflows in database
        self._store_workflows(live_workflows)
        
        # Get all workflows from database (includes deleted ones)
        return self._get_workflows_with_history(limit)
    
    def _get_live_workflows(self) -> List[Dict]:
        """Get current workflows from Argo CLI"""
        try:
            result = subprocess.run([
                'argo', 'list', '-n', self.namespace, '-o', 'json'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return []
            
            workflows_data = json.loads(result.stdout)
            workflows = []
            
            # Handle both array format (CLI returns this) and object with 'items' format
            if isinstance(workflows_data, list):
                items = workflows_data
            elif workflows_data and 'items' in workflows_data:
                items = workflows_data['items']
            else:
                items = []
                
            if items:
                for wf in items:
                    metadata = wf.get('metadata', {})
                    status = wf.get('status', {})
                    
                    # Parse timestamps
                    created_at = self._parse_timestamp(metadata.get('creationTimestamp'))
                    started_at = self._parse_timestamp(status.get('startedAt'))
                    finished_at = self._parse_timestamp(status.get('finishedAt'))
                    
                    # Calculate duration
                    duration = None
                    if started_at and finished_at:
                        duration = (finished_at - started_at).total_seconds()
                    
                    workflows.append({
                        'name': metadata.get('name', 'Unknown'),
                        'uid': metadata.get('uid', ''),
                        'status': status.get('phase', 'Unknown'),
                        'created_at': created_at.isoformat() if created_at else None,
                        'started_at': started_at.isoformat() if started_at else None,
                        'finished_at': finished_at.isoformat() if finished_at else None,
                        'duration_seconds': duration,
                        'namespace': self.namespace
                    })
            
            return workflows
            
        except Exception as e:
            print(f"Error getting live workflows: {e}")
            return []
    
    def _store_workflows(self, workflows: List[Dict]):
        """Store workflows in database"""
        if not workflows:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for wf in workflows:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO workflows 
                    (name, uid, namespace, status, created_at, started_at, finished_at, duration_seconds, collected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    wf['name'], wf['uid'], wf['namespace'], wf['status'],
                    wf['created_at'], wf['started_at'], wf['finished_at'], wf['duration_seconds']
                ))
            except Exception as e:
                print(f"Error storing workflow {wf['name']}: {e}")
        
        conn.commit()
        conn.close()
    
    def _get_workflows_with_history(self, limit: int) -> List[Dict]:
        """Get workflows from database with deleted status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current live workflow UIDs
        live_workflows = self._get_live_workflows()
        live_uids = {wf['uid'] for wf in live_workflows}
        
        # Get all workflows from database, ordered by creation time
        cursor.execute('''
            SELECT name, uid, namespace, status, created_at, started_at, finished_at, duration_seconds, collected_at
            FROM workflows 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit * 2,))  # Get more to account for deleted ones
        
        workflows = []
        for row in cursor.fetchall():
            name, uid, namespace, status, created_at, started_at, finished_at, duration_seconds, collected_at = row
            
            # Determine if workflow is deleted (not in live workflows)
            is_deleted = uid not in live_uids
            display_status = f"Deleted ({status})" if is_deleted else status
            
            workflows.append({
                'name': name,
                'uid': uid,
                'status': display_status,
                'created_at': created_at,
                'started_at': started_at,
                'finished_at': finished_at,
                'duration_seconds': duration_seconds,
                'namespace': namespace,
                'is_deleted': is_deleted,
                'last_seen': collected_at
            })
        
        conn.close()
        return workflows[:limit]
    
    def get_tasks_data(self, limit: int = 50) -> Dict:
        """Get detailed task information from workflows"""
        try:
            # Get live workflows with full JSON data
            result = subprocess.run([
                'argo', 'list', '-n', self.namespace, '-o', 'json'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return {"workflows": [], "tasks": []}
            
            workflows_data = json.loads(result.stdout)
            
            # Handle both array format and object with 'items' format
            if isinstance(workflows_data, list):
                items = workflows_data
            elif workflows_data and 'items' in workflows_data:
                items = workflows_data['items']
            else:
                items = []
            
            # Get stored workflows for deleted detection
            stored_workflows = self._get_workflows_with_history(limit * 2)
            live_uids = {wf.get('uid') for wf in self._get_live_workflows()}
            
            workflows_summary = []
            all_tasks = []
            
            # Process live workflows
            for wf in items:
                metadata = wf.get('metadata', {})
                status_info = wf.get('status', {})
                
                workflow_name = metadata.get('name', 'Unknown')
                workflow_uid = metadata.get('uid', '')
                workflow_status = status_info.get('phase', 'Unknown')
                
                # Parse workflow timestamps
                created_at = self._parse_timestamp(metadata.get('creationTimestamp'))
                started_at = self._parse_timestamp(status_info.get('startedAt'))
                finished_at = self._parse_timestamp(status_info.get('finishedAt'))
                
                # Calculate workflow duration
                workflow_duration = None
                if started_at and finished_at:
                    workflow_duration = (finished_at - started_at).total_seconds()
                
                # Extract workflow type (remove timestamp suffix)
                workflow_type = '-'.join(workflow_name.split('-')[:-1]) if '-' in workflow_name else workflow_name
                
                workflow_summary = {
                    'type': 'workflow',
                    'name': workflow_name,
                    'uid': workflow_uid,
                    'workflow_type': workflow_type,
                    'status': workflow_status,
                    'created_at': created_at.isoformat() if created_at else None,
                    'started_at': started_at.isoformat() if started_at else None,
                    'finished_at': finished_at.isoformat() if finished_at else None,
                    'duration_seconds': workflow_duration,
                    'is_deleted': False,
                    'namespace': self.namespace
                }
                workflows_summary.append(workflow_summary)
                
                # Extract individual tasks/nodes
                nodes = status_info.get('nodes', {})
                for node_id, node in nodes.items():
                    if node.get('type') == 'Pod':  # Only process actual task pods
                        task_name = node.get('displayName', node.get('name', 'Unknown'))
                        template_name = node.get('templateName', 'Unknown')
                        task_phase = node.get('phase', 'Unknown')
                        
                        # Parse task timestamps
                        task_started = self._parse_timestamp(node.get('startedAt'))
                        task_finished = self._parse_timestamp(node.get('finishedAt'))
                        
                        # Calculate task duration
                        task_duration = None
                        if task_started and task_finished:
                            task_duration = (task_finished - task_started).total_seconds()
                        
                        task_info = {
                            'type': 'task',
                            'name': task_name,
                            'template_name': template_name,
                            'task_type': template_name,  # For filtering
                            'workflow_name': workflow_name,
                            'workflow_type': workflow_type,
                            'workflow_uid': workflow_uid,
                            'status': task_phase,
                            'started_at': task_started.isoformat() if task_started else None,
                            'finished_at': task_finished.isoformat() if task_finished else None,
                            'duration_seconds': task_duration,
                            'is_deleted': False,
                            'namespace': self.namespace
                        }
                        all_tasks.append(task_info)
            
            # Add deleted workflows from database
            for stored_wf in stored_workflows:
                if stored_wf.get('uid') not in live_uids:
                    # This is a deleted workflow
                    workflow_type = '-'.join(stored_wf['name'].split('-')[:-1]) if '-' in stored_wf['name'] else stored_wf['name']
                    
                    deleted_workflow = {
                        'type': 'workflow',
                        'name': stored_wf['name'],
                        'uid': stored_wf['uid'],
                        'workflow_type': workflow_type,
                        'status': f"Deleted ({stored_wf['status']})",
                        'created_at': stored_wf['created_at'],
                        'started_at': stored_wf['started_at'],
                        'finished_at': stored_wf['finished_at'],
                        'duration_seconds': stored_wf['duration_seconds'],
                        'is_deleted': True,
                        'namespace': stored_wf['namespace']
                    }
                    workflows_summary.append(deleted_workflow)
            
            # Sort by start time
            workflows_summary.sort(key=lambda x: x['started_at'] or '', reverse=True)
            all_tasks.sort(key=lambda x: x['started_at'] or '', reverse=True)
            
            return {
                "workflows": workflows_summary[:limit],
                "tasks": all_tasks[:limit * 5],  # More tasks since there are many per workflow
                "summary": {
                    "total_workflows": len(workflows_summary),
                    "total_tasks": len(all_tasks),
                    "workflow_types": list(set(w['workflow_type'] for w in workflows_summary)),
                    "task_types": list(set(t['task_type'] for t in all_tasks))
                }
            }
            
        except Exception as e:
            print(f"Error getting tasks data: {e}")
            return {"workflows": [], "tasks": [], "summary": {}}
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO timestamp string to datetime"""
        if not timestamp_str:
            return None
        try:
            # Handle different timestamp formats
            if timestamp_str.endswith('Z'):
                return datetime.fromisoformat(timestamp_str[:-1] + '+00:00')
            else:
                return datetime.fromisoformat(timestamp_str)
        except:
            return None
    
    def get_stats(self) -> Dict:
        """Get workflow statistics including deleted workflows"""
        workflows = self.get_workflows(100)  # Get more for stats
        
        if not workflows:
            return {
                "total": 0,
                "succeeded": 0,
                "failed": 0,
                "running": 0,
                "deleted": 0,
                "avg_duration": 0
            }
        
        total = len(workflows)
        succeeded = sum(1 for wf in workflows if wf['status'] == 'Succeeded')
        failed = sum(1 for wf in workflows if wf['status'] == 'Failed')  
        running = sum(1 for wf in workflows if wf['status'] == 'Running')
        deleted = sum(1 for wf in workflows if wf.get('is_deleted', False))
        
        # Calculate average duration for completed workflows (excluding deleted)
        completed_durations = [
            wf['duration_seconds'] for wf in workflows 
            if wf['duration_seconds'] is not None and not wf.get('is_deleted', False)
        ]
        avg_duration = sum(completed_durations) / len(completed_durations) if completed_durations else 0
        
        return {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "running": running,
            "deleted": deleted,
            "avg_duration": round(avg_duration, 2)
        }

# Initialize Argo connection
argo_conn = ArgoConnection()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("argo_dashboard.html", {"request": request})

@app.get("/api/test-connection")
async def test_connection():
    """Test Argo connection"""
    return argo_conn.test_connection()

@app.get("/api/workflows")
async def get_workflows(limit: int = 10):
    """Get workflows from Argo"""
    return argo_conn.get_workflows(limit)

@app.get("/api/stats")
async def get_stats():
    """Get workflow statistics"""
    return argo_conn.get_stats()

@app.get("/api/chart-data")
async def get_chart_data(limit: int = 50):
    """Get workflow data for charts"""
    workflows = argo_conn.get_workflows(limit)
    
    chart_data = []
    for wf in workflows:
        if wf.get('started_at') and wf.get('duration_seconds') is not None:
            chart_data.append({
                'name': wf['name'],
                'started_at': wf['started_at'],
                'duration': wf['duration_seconds'],
                'status': wf['status'],
                'is_deleted': wf.get('is_deleted', False)
            })
    
    # Sort by start time
    chart_data.sort(key=lambda x: x['started_at'])
    
    return chart_data

@app.get("/api/tasks-data")
async def get_tasks_data(limit: int = 50):
    """Get detailed task data for workflows and individual tasks"""
    return argo_conn.get_tasks_data(limit)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

def find_available_port(start_port: int = 8001, max_attempts: int = 5) -> int:
    """Find an available port starting from start_port, trying up to max_attempts ports"""
    import socket
    
    for attempt in range(max_attempts):
        test_port = start_port + attempt
        try:
            # Test if port is available
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', test_port))
                return test_port
        except OSError:
            print(f"⚠️  Port {test_port} is already in use, trying next port...")
            continue
    
    raise RuntimeError(f"Unable to find available port after {max_attempts} attempts (tried ports {start_port}-{start_port + max_attempts - 1})")

if __name__ == "__main__":
    print("🚀 Starting Clean Argo Dashboard...")
    
    try:
        port = find_available_port(8001, 5)
        print(f"📊 Dashboard: http://localhost:{port}")
        print(f"🔍 API docs: http://localhost:{port}/docs")
        uvicorn.run(app, host="0.0.0.0", port=port)
    except RuntimeError as e:
        print(f"❌ Failed to start dashboard: {e}")
        exit(1) 