#!/usr/bin/env python3
"""
Kibana Integration for Argo Workflows Monitor

This module extends the simple workflow monitor to send structured
performance metrics directly to Elasticsearch/Kibana, focusing on
task and pipeline durations for comprehensive monitoring.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import sqlite3
from elasticsearch import Elasticsearch
from dataclasses import dataclass, asdict
import os


@dataclass
class WorkflowDurationMetric:
    """Structured metric for workflow duration tracking"""
    timestamp: str
    workflow_name: str
    workflow_uid: str
    namespace: str
    status: str
    duration_seconds: float
    duration_minutes: float
    task_count: int
    environment: str
    cluster: str = "on-prem"
    metric_type: str = "workflow_duration"


@dataclass
class TaskDurationMetric:
    """Structured metric for individual task duration tracking"""
    timestamp: str
    workflow_name: str
    workflow_uid: str
    task_name: str
    task_id: str
    phase: str
    template_name: str
    duration_seconds: float
    duration_minutes: float
    host_node: str
    environment: str
    cluster: str = "on-prem"
    metric_type: str = "task_duration"


class KibanaIntegration:
    """
    Integrates workflow monitoring with Kibana/Elasticsearch
    
    Focuses on duration metrics and performance tracking
    """
    
    def __init__(self, 
                 elasticsearch_host: str = "localhost:9200",
                 elasticsearch_user: str = "elastic",
                 elasticsearch_password: str = "password",
                 index_prefix: str = "argo-metrics"):
        
        self.es_client = Elasticsearch(
            hosts=[f"http://{elasticsearch_host}"],
            basic_auth=(elasticsearch_user, elasticsearch_password),
            verify_certs=False
        )
        self.index_prefix = index_prefix
        self.logger = logging.getLogger(__name__)
        
        # Initialize Elasticsearch indices
        self._setup_elasticsearch_indices()
    
    def _setup_elasticsearch_indices(self):
        """Setup Elasticsearch index templates for metrics"""
        
        # Workflow duration metrics template
        workflow_template = {
            "index_patterns": [f"{self.index_prefix}-workflows-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "refresh_interval": "5s"
                },
                "mappings": {
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "workflow_name": {"type": "keyword"},
                        "workflow_uid": {"type": "keyword"},
                        "namespace": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "duration_seconds": {"type": "float"},
                        "duration_minutes": {"type": "float"},
                        "task_count": {"type": "integer"},
                        "environment": {"type": "keyword"},
                        "cluster": {"type": "keyword"},
                        "metric_type": {"type": "keyword"}
                    }
                }
            }
        }
        
        # Task duration metrics template
        task_template = {
            "index_patterns": [f"{self.index_prefix}-tasks-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "refresh_interval": "5s"
                },
                "mappings": {
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "workflow_name": {"type": "keyword"},
                        "workflow_uid": {"type": "keyword"},
                        "task_name": {"type": "keyword"},
                        "task_id": {"type": "keyword"},
                        "phase": {"type": "keyword"},
                        "template_name": {"type": "keyword"},
                        "duration_seconds": {"type": "float"},
                        "duration_minutes": {"type": "float"},
                        "host_node": {"type": "keyword"},
                        "environment": {"type": "keyword"},
                        "cluster": {"type": "keyword"},
                        "metric_type": {"type": "keyword"}
                    }
                }
            }
        }
        
        try:
            # Create index templates
            self.es_client.indices.put_index_template(
                name=f"{self.index_prefix}-workflows-template",
                body=workflow_template
            )
            
            self.es_client.indices.put_index_template(
                name=f"{self.index_prefix}-tasks-template", 
                body=task_template
            )
            
            self.logger.info("Elasticsearch index templates created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to create Elasticsearch index templates: {e}")
    
    def send_workflow_metrics(self, db_path: str = "workflow_metrics.db", days: int = 1):
        """
        Extract workflow duration metrics from SQLite and send to Elasticsearch
        
        Args:
            db_path: Path to SQLite database
            days: Number of days to look back for metrics
        """
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Query completed workflows from the last N days
        query = """
        SELECT name, uid, namespace, status, created_at, started_at, finished_at,
               duration_seconds, task_count, environment
        FROM workflows 
        WHERE finished_at IS NOT NULL 
        AND finished_at >= datetime('now', '-{} days')
        AND duration_seconds IS NOT NULL
        ORDER BY finished_at DESC
        """.format(days)
        
        cursor = conn.execute(query)
        workflows = cursor.fetchall()
        
        metrics_sent = 0
        
        for workflow in workflows:
            try:
                # Create workflow duration metric
                metric = WorkflowDurationMetric(
                    timestamp=workflow['finished_at'],
                    workflow_name=workflow['name'],
                    workflow_uid=workflow['uid'],
                    namespace=workflow['namespace'] or 'argo',
                    status=workflow['status'] or 'unknown',
                    duration_seconds=float(workflow['duration_seconds']),
                    duration_minutes=float(workflow['duration_seconds']) / 60.0,
                    task_count=workflow['task_count'] or 0,
                    environment=workflow['environment'] or 'development'
                )
                
                # Send to Elasticsearch
                index_name = f"{self.index_prefix}-workflows-{datetime.now().strftime('%Y.%m.%d')}"
                
                doc = asdict(metric)
                doc['@timestamp'] = metric.timestamp
                
                self.es_client.index(
                    index=index_name,
                    body=doc
                )
                
                metrics_sent += 1
                
            except Exception as e:
                self.logger.error(f"Failed to send workflow metric for {workflow['name']}: {e}")
        
        conn.close()
        self.logger.info(f"Sent {metrics_sent} workflow duration metrics to Elasticsearch")
        return metrics_sent
    
    def send_task_metrics(self, db_path: str = "workflow_metrics.db", days: int = 1):
        """
        Extract task duration metrics from SQLite and send to Elasticsearch
        
        Args:
            db_path: Path to SQLite database  
            days: Number of days to look back for metrics
        """
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Query completed tasks from the last N days
        query = """
        SELECT workflow_uid, workflow_name, task_name, task_id, phase,
               template_name, host_node, started_at, finished_at, duration_seconds
        FROM tasks 
        WHERE finished_at IS NOT NULL 
        AND finished_at >= datetime('now', '-{} days')
        AND duration_seconds IS NOT NULL
        ORDER BY finished_at DESC
        """.format(days)
        
        cursor = conn.execute(query)
        tasks = cursor.fetchall()
        
        metrics_sent = 0
        
        for task in tasks:
            try:
                # Create task duration metric
                metric = TaskDurationMetric(
                    timestamp=task['finished_at'],
                    workflow_name=task['workflow_name'] or 'unknown',
                    workflow_uid=task['workflow_uid'],
                    task_name=task['task_name'] or 'unknown',
                    task_id=task['task_id'],
                    phase=task['phase'] or 'unknown',
                    template_name=task['template_name'] or 'unknown',
                    duration_seconds=float(task['duration_seconds']),
                    duration_minutes=float(task['duration_seconds']) / 60.0,
                    host_node=task['host_node'] or 'unknown',
                    environment=os.getenv('ENVIRONMENT', 'development')
                )
                
                # Send to Elasticsearch
                index_name = f"{self.index_prefix}-tasks-{datetime.now().strftime('%Y.%m.%d')}"
                
                doc = asdict(metric)
                doc['@timestamp'] = metric.timestamp
                
                self.es_client.index(
                    index=index_name,
                    body=doc
                )
                
                metrics_sent += 1
                
            except Exception as e:
                self.logger.error(f"Failed to send task metric for {task['task_name']}: {e}")
        
        conn.close()
        self.logger.info(f"Sent {metrics_sent} task duration metrics to Elasticsearch")
        return metrics_sent
    
    def create_duration_summary(self, days: int = 7) -> Dict:
        """
        Create a summary of duration metrics for the dashboard
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with duration statistics
        """
        
        try:
            # Query workflow duration stats
            workflow_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"metric_type": "workflow_duration"}},
                            {"range": {"@timestamp": {"gte": f"now-{days}d"}}}
                        ]
                    }
                },
                "aggs": {
                    "avg_duration": {"avg": {"field": "duration_minutes"}},
                    "max_duration": {"max": {"field": "duration_minutes"}},
                    "min_duration": {"min": {"field": "duration_minutes"}},
                    "workflow_names": {
                        "terms": {"field": "workflow_name", "size": 10}
                    }
                }
            }
            
            # Query task duration stats
            task_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"metric_type": "task_duration"}},
                            {"range": {"@timestamp": {"gte": f"now-{days}d"}}}
                        ]
                    }
                },
                "aggs": {
                    "avg_duration": {"avg": {"field": "duration_minutes"}},
                    "max_duration": {"max": {"field": "duration_minutes"}},
                    "min_duration": {"min": {"field": "duration_minutes"}},
                    "task_names": {
                        "terms": {"field": "task_name", "size": 10}
                    }
                }
            }
            
            workflow_results = self.es_client.search(
                index=f"{self.index_prefix}-workflows-*",
                body=workflow_query,
                size=0
            )
            
            task_results = self.es_client.search(
                index=f"{self.index_prefix}-tasks-*", 
                body=task_query,
                size=0
            )
            
            return {
                "workflows": {
                    "total_count": workflow_results['hits']['total']['value'],
                    "avg_duration_minutes": workflow_results['aggregations']['avg_duration']['value'] or 0,
                    "max_duration_minutes": workflow_results['aggregations']['max_duration']['value'] or 0,
                    "min_duration_minutes": workflow_results['aggregations']['min_duration']['value'] or 0,
                    "top_workflows": [
                        {"name": bucket['key'], "count": bucket['doc_count']}
                        for bucket in workflow_results['aggregations']['workflow_names']['buckets']
                    ]
                },
                "tasks": {
                    "total_count": task_results['hits']['total']['value'],
                    "avg_duration_minutes": task_results['aggregations']['avg_duration']['value'] or 0,
                    "max_duration_minutes": task_results['aggregations']['max_duration']['value'] or 0,
                    "min_duration_minutes": task_results['aggregations']['min_duration']['value'] or 0,
                    "top_tasks": [
                        {"name": bucket['key'], "count": bucket['doc_count']}
                        for bucket in task_results['aggregations']['task_names']['buckets']
                    ]
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create duration summary: {e}")
            return {"error": str(e)}
    
    def health_check(self) -> Dict:
        """Check Elasticsearch connectivity and index status"""
        
        try:
            # Check Elasticsearch health
            es_health = self.es_client.cluster.health()
            
            # Check if our indices exist
            workflow_indices = self.es_client.indices.get(
                index=f"{self.index_prefix}-workflows-*",
                ignore=[404]
            )
            
            task_indices = self.es_client.indices.get(
                index=f"{self.index_prefix}-tasks-*", 
                ignore=[404]
            )
            
            return {
                "elasticsearch_status": es_health['status'],
                "workflow_indices_count": len(workflow_indices) if workflow_indices else 0,
                "task_indices_count": len(task_indices) if task_indices else 0,
                "connection_status": "healthy"
            }
            
        except Exception as e:
            return {
                "connection_status": "failed",
                "error": str(e)
            }


def main():
    """CLI interface for Kibana integration"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Send workflow metrics to Kibana")
    parser.add_argument("--db-path", default="workflow_metrics.db", help="SQLite database path")
    parser.add_argument("--days", type=int, default=1, help="Days to look back")
    parser.add_argument("--es-host", default="localhost:9200", help="Elasticsearch host")
    parser.add_argument("--es-user", default="elastic", help="Elasticsearch username")
    parser.add_argument("--es-password", default="password", help="Elasticsearch password")
    parser.add_argument("--action", choices=["send", "summary", "health"], default="send", 
                       help="Action to perform")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create integration instance
    integration = KibanaIntegration(
        elasticsearch_host=args.es_host,
        elasticsearch_user=args.es_user,
        elasticsearch_password=args.es_password
    )
    
    if args.action == "send":
        # Send metrics to Elasticsearch
        workflow_count = integration.send_workflow_metrics(args.db_path, args.days)
        task_count = integration.send_task_metrics(args.db_path, args.days)
        print(f"✅ Sent {workflow_count} workflow metrics and {task_count} task metrics to Kibana")
        
    elif args.action == "summary":
        # Display duration summary
        summary = integration.create_duration_summary(args.days)
        print(json.dumps(summary, indent=2))
        
    elif args.action == "health":
        # Check health status
        status = integration.health_check()
        print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main() 