#!/usr/bin/env python3
"""Create sample data for testing the monitoring solution"""

import sqlite3
from datetime import datetime
import json

def create_sample_data():
    # Create sample database
    conn = sqlite3.connect('./data/workflow_metrics.db')
    cursor = conn.cursor()

    # Create tables
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
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insert sample data
    sample_workflows = [
        ('ml-training-pipeline', 'wf-123', 'argo', 'Succeeded', '2024-01-15 10:00:00', '2024-01-15 10:01:00', '2024-01-15 10:02:36', 96.5, 8),
        ('cv-inference-batch', 'wf-124', 'argo', 'Succeeded', '2024-01-15 11:00:00', '2024-01-15 11:01:00', '2024-01-15 11:02:15', 75.2, 6),
        ('data-validation', 'wf-125', 'argo', 'Failed', '2024-01-15 12:00:00', '2024-01-15 12:01:00', '2024-01-15 12:03:45', 165.8, 4),
        ('model-deployment', 'wf-126', 'argo', 'Succeeded', '2024-01-15 13:00:00', '2024-01-15 13:01:00', '2024-01-15 13:01:45', 45.0, 3),
        ('batch-processing', 'wf-127', 'argo', 'Running', '2024-01-15 14:00:00', '2024-01-15 14:01:00', None, None, 7)
    ]

    for wf in sample_workflows:
        try:
            cursor.execute('''
                INSERT INTO workflows (name, uid, namespace, status, created_at, started_at, finished_at, duration_seconds, task_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', wf)
        except sqlite3.IntegrityError:
            # Skip if already exists
            pass

    # Insert sample tasks
    sample_tasks = [
        ('wf-123', 'ml-training-pipeline', 'validate-inputs', 'task-1', 'Succeeded', 'validate', 'node-1', '2024-01-15 10:01:00', '2024-01-15 10:01:35', 35.0),
        ('wf-123', 'ml-training-pipeline', 'prepare-data', 'task-2', 'Succeeded', 'prepare', 'node-2', '2024-01-15 10:01:35', '2024-01-15 10:01:44', 9.0),
        ('wf-123', 'ml-training-pipeline', 'process-images', 'task-3', 'Succeeded', 'process', 'node-3', '2024-01-15 10:01:44', '2024-01-15 10:01:55', 11.0),
        ('wf-123', 'ml-training-pipeline', 'model-training', 'task-4', 'Succeeded', 'training', 'node-4', '2024-01-15 10:01:55', '2024-01-15 10:02:36', 41.0),
        ('wf-124', 'cv-inference-batch', 'load-model', 'task-5', 'Succeeded', 'load', 'node-1', '2024-01-15 11:01:00', '2024-01-15 11:01:25', 25.0),
        ('wf-124', 'cv-inference-batch', 'inference', 'task-6', 'Succeeded', 'inference', 'node-2', '2024-01-15 11:01:25', '2024-01-15 11:02:05', 40.0),
        ('wf-124', 'cv-inference-batch', 'postprocess', 'task-7', 'Succeeded', 'postprocess', 'node-3', '2024-01-15 11:02:05', '2024-01-15 11:02:15', 10.0),
        ('wf-125', 'data-validation', 'check-format', 'task-8', 'Failed', 'validate', 'node-1', '2024-01-15 12:01:00', '2024-01-15 12:03:45', 165.8),
        ('wf-126', 'model-deployment', 'deploy', 'task-9', 'Succeeded', 'deploy', 'node-2', '2024-01-15 13:01:00', '2024-01-15 13:01:45', 45.0)
    ]

    for task in sample_tasks:
        cursor.execute('''
            INSERT OR IGNORE INTO tasks (workflow_uid, workflow_name, task_name, task_id, phase, template_name, host_node, started_at, finished_at, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', task)

    conn.commit()
    conn.close()
    print('✅ Sample database created with test data')
    print('📊 5 workflows and 9 tasks created')
    print('🎯 Ready to test the monitoring dashboard')

if __name__ == "__main__":
    create_sample_data() 