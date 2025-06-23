#!/usr/bin/env python3
"""
Argo Workflows Metrics Collector

This service queries the Argo API, extracts workflow and task timing data,
and sends it to Elasticsearch for visualization in Grafana.

Usage:
    python argo-metrics-collector.py --config config.yaml
"""

import json
import time
import logging
import argparse
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional
import yaml
from dataclasses import dataclass

# You'll need to install these in your requirements.txt:
# pip install elasticsearch pyyaml kubernetes
try:
    from elasticsearch import Elasticsearch
    from kubernetes import client, config
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Install with: pip install elasticsearch pyyaml kubernetes")
    exit(1)


@dataclass
class WorkflowMetrics:
    """Container for workflow performance metrics"""
    workflow_name: str
    workflow_uid: str
    namespace: str
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime] 
    duration_seconds: Optional[float]
    tasks: List[Dict]
    parameters: Dict
    labels: Dict


class ArgoMetricsCollector:
    """Collects metrics from Argo Workflows and sends to Elasticsearch"""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        self.es_client = self._init_elasticsearch()
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # Default configuration
            return {
                'elasticsearch': {
                    'hosts': ['localhost:9200'],
                    'index': 'argo-workflow-metrics'
                },
                'argo': {
                    'namespace': 'argo',
                    'cli_path': 'argo'
                },
                'collection': {
                    'interval_seconds': 60,
                    'max_workflows': 100
                }
            }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def _init_elasticsearch(self) -> Elasticsearch:
        """Initialize Elasticsearch client"""
        es_config = self.config['elasticsearch']
        return Elasticsearch(
            hosts=es_config['hosts'],
            # Add authentication if needed:
            # http_auth=('username', 'password'),
            # use_ssl=True,
            # verify_certs=True
        )
    
    def collect_workflow_list(self) -> List[str]:
        """Get list of workflows from Argo"""
        try:
            cmd = [
                self.config['argo']['cli_path'], 
                'list', 
                '-n', self.config['argo']['namespace'],
                '-o', 'json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            workflows_data = json.loads(result.stdout)
            
            workflow_names = []
            if workflows_data and 'items' in workflows_data:
                for wf in workflows_data['items']:
                    workflow_names.append(wf['metadata']['name'])
                    
            self.logger.info(f"Found {len(workflow_names)} workflows")
            return workflow_names
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to list workflows: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse workflow list JSON: {e}")
            return []
    
    def extract_workflow_metrics(self, workflow_name: str) -> Optional[WorkflowMetrics]:
        """Extract detailed metrics from a specific workflow"""
        try:
            cmd = [
                self.config['argo']['cli_path'],
                'get', workflow_name,
                '-n', self.config['argo']['namespace'],
                '-o', 'json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            workflow_data = json.loads(result.stdout)
            
            return self._parse_workflow_data(workflow_data)
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get workflow {workflow_name}: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse workflow JSON for {workflow_name}: {e}")
            return None
    
    def _parse_workflow_data(self, workflow_data: dict) -> WorkflowMetrics:
        """Parse workflow JSON data into structured metrics"""
        metadata = workflow_data.get('metadata', {})
        spec = workflow_data.get('spec', {})
        status = workflow_data.get('status', {})
        
        # Extract timing information
        created_at = self._parse_timestamp(metadata.get('creationTimestamp'))
        started_at = self._parse_timestamp(status.get('startedAt'))
        finished_at = self._parse_timestamp(status.get('finishedAt'))
        
        # Calculate duration
        duration_seconds = None
        if started_at and finished_at:
            duration_seconds = (finished_at - started_at).total_seconds()
        
        # Extract task information
        tasks = self._extract_task_metrics(status.get('nodes', {}))
        
        return WorkflowMetrics(
            workflow_name=metadata.get('name', ''),
            workflow_uid=metadata.get('uid', ''),
            namespace=metadata.get('namespace', ''),
            status=status.get('phase', 'Unknown'),
            created_at=created_at,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
            tasks=tasks,
            parameters=spec.get('arguments', {}).get('parameters', []),
            labels=metadata.get('labels', {})
        )
    
    def _extract_task_metrics(self, nodes: dict) -> List[Dict]:
        """Extract individual task metrics from workflow nodes"""
        tasks = []
        
        for node_id, node_data in nodes.items():
            if node_data.get('type') in ['Pod', 'Container']:  # Actual work tasks
                task_info = {
                    'task_name': node_data.get('displayName', node_data.get('name', '')),
                    'task_id': node_id,
                    'phase': node_data.get('phase', ''),
                    'started_at': self._parse_timestamp(node_data.get('startedAt')),
                    'finished_at': self._parse_timestamp(node_data.get('finishedAt')),
                    'duration_seconds': None,
                    'template_name': node_data.get('templateName', ''),
                    'host_node_name': node_data.get('hostNodeName', ''),
                }
                
                # Calculate task duration
                if task_info['started_at'] and task_info['finished_at']:
                    task_info['duration_seconds'] = (
                        task_info['finished_at'] - task_info['started_at']
                    ).total_seconds()
                
                tasks.append(task_info)
        
        return tasks
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO timestamp string to datetime object"""
        if not timestamp_str:
            return None
        try:
            # Handle RFC3339 format used by Kubernetes
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            self.logger.warning(f"Failed to parse timestamp: {timestamp_str}")
            return None
    
    def send_to_elasticsearch(self, metrics: WorkflowMetrics) -> bool:
        """Send workflow metrics to Elasticsearch"""
        try:
            # Create workflow-level document
            workflow_doc = {
                '@timestamp': metrics.finished_at or metrics.started_at or metrics.created_at,
                'workflow': {
                    'name': metrics.workflow_name,
                    'uid': metrics.workflow_uid,
                    'namespace': metrics.namespace,
                    'status': metrics.status,
                },
                'timing': {
                    'created_at': metrics.created_at,
                    'started_at': metrics.started_at,
                    'finished_at': metrics.finished_at,
                    'duration_seconds': metrics.duration_seconds,
                },
                'parameters': {param.get('name'): param.get('value') for param in metrics.parameters},
                'labels': metrics.labels,
                'task_count': len(metrics.tasks),
                'environment': {
                    'cluster': 'development',  # Adjust as needed
                    'collector_version': '1.0.0'
                }
            }
            
            # Index workflow document
            index_name = f"{self.config['elasticsearch']['index']}-{datetime.now().strftime('%Y-%m')}"
            
            result = self.es_client.index(
                index=index_name,
                id=f"workflow-{metrics.workflow_uid}",
                body=workflow_doc
            )
            
            # Index individual task documents
            for task in metrics.tasks:
                task_doc = {
                    '@timestamp': task['finished_at'] or task['started_at'],
                    'workflow': {
                        'name': metrics.workflow_name,
                        'uid': metrics.workflow_uid,
                    },
                    'task': {
                        'name': task['task_name'],
                        'id': task['task_id'],
                        'phase': task['phase'],
                        'template_name': task['template_name'],
                        'host_node': task['host_node_name'],
                    },
                    'timing': {
                        'started_at': task['started_at'],
                        'finished_at': task['finished_at'],
                        'duration_seconds': task['duration_seconds'],
                    },
                    'environment': {
                        'cluster': 'development',
                        'collector_version': '1.0.0'
                    }
                }
                
                if task['finished_at']:  # Only index completed tasks
                    self.es_client.index(
                        index=f"{index_name}-tasks",
                        id=f"task-{task['task_id']}",
                        body=task_doc
                    )
            
            self.logger.info(f"Successfully indexed workflow {metrics.workflow_name} with {len(metrics.tasks)} tasks")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send metrics to Elasticsearch: {e}")
            return False
    
    def run_collection_cycle(self):
        """Run a single collection cycle"""
        self.logger.info("Starting metrics collection cycle")
        
        # Get list of workflows
        workflow_names = self.collect_workflow_list()
        
        # Limit to recent workflows to avoid overwhelming ES
        max_workflows = self.config['collection']['max_workflows']
        if len(workflow_names) > max_workflows:
            workflow_names = workflow_names[:max_workflows]
            self.logger.info(f"Limited to {max_workflows} most recent workflows")
        
        # Process each workflow
        successful_collections = 0
        for workflow_name in workflow_names:
            metrics = self.extract_workflow_metrics(workflow_name)
            if metrics and metrics.finished_at:  # Only collect completed workflows
                if self.send_to_elasticsearch(metrics):
                    successful_collections += 1
                    
        self.logger.info(f"Collection cycle complete: {successful_collections}/{len(workflow_names)} workflows processed")
    
    def run_daemon(self):
        """Run collector as a daemon"""
        interval = self.config['collection']['interval_seconds']
        self.logger.info(f"Starting Argo metrics collector daemon (interval: {interval}s)")
        
        while True:
            try:
                self.run_collection_cycle()
                time.sleep(interval)
            except KeyboardInterrupt:
                self.logger.info("Shutting down collector daemon")
                break
            except Exception as e:
                self.logger.error(f"Error in collection cycle: {e}")
                time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description='Argo Workflows Metrics Collector')
    parser.add_argument('--config', default='collector-config.yaml', 
                       help='Configuration file path')
    parser.add_argument('--once', action='store_true',
                       help='Run once instead of as daemon')
    
    args = parser.parse_args()
    
    collector = ArgoMetricsCollector(args.config)
    
    if args.once:
        collector.run_collection_cycle()
    else:
        collector.run_daemon()


if __name__ == '__main__':
    main() 