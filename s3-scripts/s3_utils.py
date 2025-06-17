#!/usr/bin/env python3
"""
S3 Utilities Module

Shared functionality for S3 operations in the on-premises environment.
Provides base classes and utilities for S3 operations including:
- Connection management
- Common file operations
- Date/size parsing utilities
- Error handling and logging
"""

import boto3
import csv
import os
import logging
import warnings
from datetime import datetime, timedelta
from dateutil import parser as dtparser
import humanfriendly
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Generator, Tuple, Any

# Suppress urllib3 warnings for MinIO compatibility
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Suppress verbose AWS SDK and urllib3 logs for cleaner output
logging.getLogger("urllib3.connection").setLevel(logging.ERROR)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class S3Utils:
    """Base S3 utilities class for common operations"""
    
    def __init__(self, bucket: str, endpoint_url: str = None, 
                 access_key: str = None, secret_key: str = None,
                 region: str = 'us-east-1', prefix: str = None):
        """
        Initialize S3 client with connection parameters
        
        Args:
            bucket: S3 bucket name
            endpoint_url: S3 endpoint URL (for MinIO/on-prem)
            access_key: AWS access key ID
            secret_key: AWS secret access key
            region: AWS region
            prefix: Default prefix for operations
        """
        self.bucket = bucket
        self.prefix = prefix
        self.endpoint_url = endpoint_url
        
        # Set up logging
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize S3 client
        self.s3_client = self._create_s3_client(
            endpoint_url, access_key, secret_key, region
        )
        
        # Verify connection
        self._verify_connection()
    
    def _create_s3_client(self, endpoint_url: str, access_key: str, 
                         secret_key: str, region: str) -> boto3.client:
        """Create and configure S3 client"""
        client_config = {
            'service_name': 's3',
            'region_name': region
        }
        
        if endpoint_url:
            client_config['endpoint_url'] = endpoint_url
            
        if access_key and secret_key:
            client_config['aws_access_key_id'] = access_key
            client_config['aws_secret_access_key'] = secret_key
        
        return boto3.client(**client_config)
    
    def _verify_connection(self) -> None:
        """Verify S3 connection is working"""
        try:
            # Just test the connection by listing service info, not requiring bucket to exist
            self.s3_client.list_buckets()
            self.logger.info(f"Successfully connected to S3 service")
        except Exception as e:
            self.logger.error(f"Failed to connect to S3 service: {e}")
            raise
    
    def ensure_bucket_exists(self) -> bool:
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
            self.logger.info(f"Bucket '{self.bucket}' already exists")
            return True
        except:
            try:
                self.s3_client.create_bucket(Bucket=self.bucket)
                self.logger.info(f"Created bucket '{self.bucket}'")
                return True
            except Exception as e:
                self.logger.error(f"Error creating bucket: {e}")
                return False
    
    def list_objects(self, prefix: str = None, max_keys: int = None) -> Generator[Dict, None, None]:
        """
        List objects in bucket with optional prefix filtering
        
        Args:
            prefix: Object key prefix to filter by
            max_keys: Maximum number of keys to return
            
        Yields:
            Dict: Object metadata
        """
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        operation_parameters = {'Bucket': self.bucket}
        
        # Use provided prefix or instance default
        use_prefix = prefix or self.prefix
        if use_prefix:
            operation_parameters['Prefix'] = use_prefix
            
        if max_keys:
            operation_parameters['MaxKeys'] = max_keys
        
        try:
            for page in paginator.paginate(**operation_parameters):
                for obj in page.get('Contents', []):
                    yield obj
        except Exception as e:
            self.logger.error(f"Error listing objects: {e}")
            raise
    
    def upload_object(self, key: str, content: bytes, 
                     metadata: Dict[str, str] = None) -> bool:
        """
        Upload object to S3
        
        Args:
            key: Object key
            content: Object content as bytes
            metadata: Optional metadata dict
            
        Returns:
            bool: Success status
        """
        try:
            put_args = {
                'Bucket': self.bucket,
                'Key': key,
                'Body': content
            }
            
            if metadata:
                put_args['Metadata'] = metadata
            
            self.s3_client.put_object(**put_args)
            self.logger.debug(f"Uploaded: {key} ({len(content)} bytes)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload {key}: {e}")
            return False
    
    def delete_object(self, key: str) -> bool:
        """
        Delete single object
        
        Args:
            key: Object key to delete
            
        Returns:
            bool: Success status
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=key)
            self.logger.debug(f"Deleted: {key}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete {key}: {e}")
            return False
    
    def delete_objects_batch(self, keys: List[str], max_workers: int = 4) -> Tuple[int, int]:
        """
        Delete multiple objects concurrently
        
        Args:
            keys: List of object keys to delete
            max_workers: Number of concurrent workers
            
        Returns:
            Tuple[int, int]: (successful_deletes, failed_deletes)
        """
        if not keys:
            return 0, 0
        
        successful = 0
        failed = 0
        
        # Use batch delete for efficiency (up to 1000 objects at a time)
        batch_size = 1000
        
        for i in range(0, len(keys), batch_size):
            batch_keys = keys[i:i + batch_size]
            
            try:
                delete_objects = [{'Key': key} for key in batch_keys]
                response = self.s3_client.delete_objects(
                    Bucket=self.bucket,
                    Delete={'Objects': delete_objects}
                )
                
                successful += len(response.get('Deleted', []))
                failed += len(response.get('Errors', []))
                
                # Log any errors
                for error in response.get('Errors', []):
                    self.logger.error(f"Delete error for {error['Key']}: {error['Message']}")
                    
            except Exception as e:
                self.logger.error(f"Batch delete error: {e}")
                failed += len(batch_keys)
        
        return successful, failed
    
    def get_bucket_summary(self) -> Dict[str, Any]:
        """Get summary statistics for bucket"""
        objects = list(self.list_objects())
        
        if not objects:
            return {'total_files': 0, 'total_size': 0, 'prefixes': {}}
        
        total_size = sum(obj['Size'] for obj in objects)
        total_files = len(objects)
        
        # Group by prefix
        prefixes = {}
        for obj in objects:
            prefix = obj['Key'].split('/')[0] if '/' in obj['Key'] else 'root'
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
        
        return {
            'total_files': total_files,
            'total_size': total_size,
            'total_size_mb': total_size / 1024 / 1024,
            'prefixes': prefixes,
            'objects': objects
        }
    
    def export_to_csv(self, objects: List[Dict], filepath: str, 
                     additional_fields: List[str] = None) -> bool:
        """
        Export object list to CSV
        
        Args:
            objects: List of object dictionaries
            filepath: Output CSV file path
            additional_fields: Additional fields to include
            
        Returns:
            bool: Success status
        """
        try:
            with open(filepath, 'w', newline='') as csvfile:
                # Base fields
                fieldnames = ['Key', 'LastModified', 'Size', 'SizeHuman']
                
                # Add additional fields if provided
                if additional_fields:
                    fieldnames.extend(additional_fields)
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for obj in objects:
                    row = {
                        'Key': obj['Key'],
                        'LastModified': obj['LastModified'],
                        'Size': obj['Size'],
                        'SizeHuman': humanfriendly.format_size(obj['Size'])
                    }
                    
                    # Add additional fields if they exist in the object
                    if additional_fields:
                        for field in additional_fields:
                            row[field] = obj.get(field, '')
                    
                    writer.writerow(row)
            
            self.logger.info(f"Exported {len(objects)} objects to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export CSV: {e}")
            return False


class S3FilterUtils:
    """Utility functions for filtering S3 objects"""
    
    @staticmethod
    def parse_time_filter(older_than: str = None, since: str = None) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Parse time filter arguments
        
        Args:
            older_than: String like '7d', '12h', '30m'
            since: Date string or relative time
            
        Returns:
            Tuple[Optional[datetime], Optional[datetime]]: (min_date, max_date)
        """
        now = datetime.now(datetime.utcnow().astimezone().tzinfo)
        min_date, max_date = None, None
        
        if older_than:
            unit = older_than[-1].lower()
            try:
                value = int(older_than[:-1])
                delta_map = {
                    'd': timedelta(days=value),
                    'h': timedelta(hours=value),
                    'm': timedelta(minutes=value),
                    'w': timedelta(weeks=value)
                }
                
                if unit not in delta_map:
                    raise ValueError(f"Invalid time unit '{unit}'. Use 'd', 'h', 'm', or 'w'")
                
                max_date = now - delta_map[unit]
                
            except ValueError as e:
                raise ValueError(f"Invalid time format '{older_than}': {e}")
        
        if since:
            try:
                min_date = dtparser.parse(since)
            except Exception as e:
                raise ValueError(f"Invalid date format '{since}': {e}")
        
        return min_date, max_date
    
    @staticmethod
    def parse_size_filter(min_size: str = None, max_size: str = None) -> Tuple[Optional[int], Optional[int]]:
        """
        Parse size filter arguments
        
        Args:
            min_size: Size string like '1MB', '500KB'
            max_size: Size string like '1GB', '100MB'
            
        Returns:
            Tuple[Optional[int], Optional[int]]: (min_bytes, max_bytes)
        """
        min_bytes = humanfriendly.parse_size(min_size) if min_size else None
        max_bytes = humanfriendly.parse_size(max_size) if max_size else None
        
        return min_bytes, max_bytes
    
    @staticmethod
    def filter_objects(objects: List[Dict], 
                      min_date: datetime = None, max_date: datetime = None,
                      exclude_patterns: List[str] = None, 
                      include_patterns: List[str] = None,
                      suffix: str = None, prefix: str = None,
                      min_size: int = None, max_size: int = None) -> Generator[Dict, None, None]:
        """
        Filter objects based on various criteria
        
        Args:
            objects: List of S3 object dictionaries
            min_date: Minimum last modified date
            max_date: Maximum last modified date
            exclude_patterns: Patterns to exclude (if any match, exclude)
            include_patterns: Patterns to include (if none match, exclude)
            suffix: Required file suffix
            prefix: Required key prefix
            min_size: Minimum file size in bytes
            max_size: Maximum file size in bytes
            
        Yields:
            Dict: Filtered object
        """
        for obj in objects:
            key = obj['Key']
            last_modified = obj['LastModified']
            size = obj['Size']
            
            # Time filters
            if min_date and last_modified < min_date:
                continue
            if max_date and last_modified > max_date:
                continue
            
            # Size filters
            if min_size and size < min_size:
                continue
            if max_size and size > max_size:
                continue
            
            # Pattern filters
            if exclude_patterns and any(pattern in key for pattern in exclude_patterns):
                continue
            
            if include_patterns and not any(pattern in key for pattern in include_patterns):
                continue
            
            # Suffix filter
            if suffix and not key.endswith(suffix):
                continue
            
            # Prefix filter
            if prefix and not key.startswith(prefix):
                continue
            
            yield obj


# Convenience function for setting up logging
def setup_logging(level: str = 'INFO', format_string: str = None) -> None:
    """Set up logging configuration with clean output"""
    if not format_string:
        # Cleaner format without timestamp for better readability
        format_string = '%(levelname)s: %(message)s'
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Ensure AWS SDK logs stay quiet even if user sets DEBUG
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING) 