#!/usr/bin/env python3
"""
MinIO Populator - Test Data Generator

Creates test files with various dates, sizes, and patterns to simulate 
a real on-premises bucket for testing S3 cleanup tools.
"""

import argparse
import random
import string
import os
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any

from s3_utils import S3Utils, setup_logging


class MinIOPopulator(S3Utils):
    """MinIO populator class that extends S3Utils with test data generation"""
    
    def __init__(self, bucket: str, endpoint_url: str = None, 
                 access_key: str = None, secret_key: str = None):
        """Initialize MinIO populator"""
        super().__init__(bucket, endpoint_url, access_key, secret_key)
        
        # Define file patterns for ML/CV environment simulation
        self.file_patterns = [
            # Model artifacts (common in ML environments)
            ("models/experiments/exp_{}/model.pkl", [1024*100, 1024*500]),
            ("models/experiments/exp_{}/logs.txt", [1024, 1024*10]),
            ("models/experiments/exp_{}/config.yaml", [512, 2048]),
            
            # Training data
            ("data/training/batch_{}/images.tar.gz", [1024*1024, 1024*1024*10]),
            ("data/training/batch_{}/labels.json", [1024*50, 1024*200]),
            
            # Evaluation results
            ("results/eval_{}/metrics.json", [1024, 1024*5]),
            ("results/eval_{}/confusion_matrix.png", [1024*100, 1024*300]),
            
            # Logs and temporary files
            ("logs/training_{}.log", [1024*10, 1024*100]),
            ("temp/temp_{}.tmp", [1024, 1024*50]),
            ("cache/cache_{}.dat", [1024*10, 1024*200]),
            
            # Documentation and configs
            ("docs/report_{}.pdf", [1024*500, 1024*2000]),
            ("configs/config_{}.json", [512, 4096]),
            
            # Different file extensions for testing suffix filters
            ("misc/file_{}.txt", [1024, 1024*10]),
            ("misc/file_{}.log", [1024*5, 1024*50]),
            ("misc/file_{}.bak", [1024*100, 1024*1000]),
        ]
        
        # Define date ranges for testing time filters
        now = datetime.now()
        self.date_ranges = [
            ("very_old", now - timedelta(days=365), now - timedelta(days=180)),    # 6-12 months old
            ("old", now - timedelta(days=90), now - timedelta(days=30)),           # 1-3 months old  
            ("recent", now - timedelta(days=14), now - timedelta(days=1)),         # 1-2 weeks old
            ("very_recent", now - timedelta(hours=48), now),                       # Last 2 days
        ]
    
    def generate_content(self, size_bytes: int) -> bytes:
        """Generate random content of specified size"""
        if size_bytes == 0:
            return b''
        elif size_bytes < 1024:  # Small files - text content
            content = ''.join(random.choices(string.ascii_letters + string.digits + '\n ', k=size_bytes))
            return content.encode('utf-8')
        else:  # Larger files - binary content
            return os.urandom(size_bytes)
    
    def upload_test_file(self, key: str, size: int, metadata: Dict[str, str] = None) -> bool:
        """Upload a test file with specified size"""
        content = self.generate_content(size)
        success = self.upload_object(key, content, metadata)
        
        if success:
            print(f"✓ Uploaded: {key} ({size:,} bytes)")
        else:
            print(f"✗ Failed: {key}")
            
        return success
    
    def create_test_files(self, num_files: int = 50) -> int:
        """
        Create a variety of test files
        
        Args:
            num_files: Target number of files to create
            
        Returns:
            int: Number of files actually created
        """
        files_created = 0
        
        for pattern, size_range in self.file_patterns:
            for date_category, start_date, end_date in self.date_ranges:
                # Create 2-4 files per pattern per date category
                files_in_category = random.randint(2, 4)
                
                for i in range(files_in_category):
                    if files_created >= num_files:
                        return files_created
                        
                    # Generate file key
                    if '{}' in pattern:
                        key = pattern.format(f"{date_category}_{i:03d}")
                    else:
                        key = f"{date_category}_{i:03d}_{pattern}"
                    
                    # Generate file size
                    size = random.randint(size_range[0], size_range[1])
                    
                    # Add date category as metadata for reference
                    metadata = {
                        'date_category': date_category,
                        'pattern_type': pattern.split('/')[0],  # models, data, etc.
                        'created_by': 'MinIOPopulator'
                    }
                    
                    # Upload file
                    if self.upload_test_file(key, size, metadata):
                        files_created += 1
        
        return files_created
    
    def create_special_test_cases(self) -> int:
        """Create specific files for testing edge cases"""
        special_files = [
            # Files with specific patterns for exclude testing
            ("EXCLUDE_ME/important.txt", 1024),
            ("keep/EXCLUDE_ME.log", 2048),
            ("temp/backup_EXCLUDE_ME.bak", 4096),
            
            # Very large files
            ("large_files/huge_model.bin", 1024*1024*50),  # 50MB
            ("large_files/dataset.tar", 1024*1024*100),    # 100MB
            
            # Very small files
            ("tiny/empty.txt", 0),
            ("tiny/small.log", 10),
            
            # Files with special characters
            ("special/file with spaces.txt", 1024),
            ("special/file-with-dashes.log", 2048),
            ("special/file_with_underscores.dat", 1024),
            
            # Date-specific test files
            ("test_dates/today.txt", 1024),
            ("test_dates/yesterday.log", 2048),
        ]
        
        print("\nCreating special test cases...")
        files_created = 0
        
        for key, size in special_files:
            metadata = {
                'file_type': 'special_test_case',
                'created_by': 'MinIOPopulator'
            }
            
            if self.upload_test_file(key, size, metadata):
                files_created += 1
        
        return files_created
    
    def clean_bucket(self) -> Tuple[int, int]:
        """Delete all objects in bucket"""
        print("🧹 Cleaning bucket...")
        
        try:
            objects = list(self.list_objects())
            
            if not objects:
                print("   Bucket was already empty")
                return 0, 0
            
            keys = [obj['Key'] for obj in objects]
            successful, failed = self.delete_objects_batch(keys)
            
            print(f"   Deleted {successful} objects, {failed} failed")
            return successful, failed
            
        except Exception as e:
            self.logger.error(f"Error cleaning bucket: {e}")
            return 0, 1
    
    def show_bucket_summary(self) -> None:
        """Show comprehensive summary of bucket contents"""
        summary = self.get_bucket_summary()
        
        if summary['total_files'] == 0:
            print("📊 Bucket is empty")
            return
        
        print(f"\n📊 Bucket Summary:")
        print(f"   Total files: {summary['total_files']:,}")
        print(f"   Total size: {summary['total_size']:,} bytes ({summary['total_size_mb']:.1f} MB)")
        
        print(f"   Files by prefix:")
        for prefix, count in sorted(summary['prefixes'].items()):
            print(f"     {prefix}/: {count} files")
        
        # Show date distribution
        objects = summary['objects']
        if objects:
            dates = [obj['LastModified'] for obj in objects]
            oldest = min(dates)
            newest = max(dates)
            print(f"   Date range: {oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}")
        
        # Show size distribution
        sizes = [obj['Size'] for obj in objects]
        if sizes:
            print(f"   Size range: {min(sizes):,} to {max(sizes):,} bytes")
            avg_size = sum(sizes) / len(sizes)
            print(f"   Average size: {avg_size:,.0f} bytes")
    
    def generate_example_commands(self, bucket_name: str) -> List[str]:
        """Generate example s3_cleaner commands for testing"""
        examples = [
            f"# Dry run - files older than 7 days:",
            f"python s3_cleaner.py --bucket {bucket_name} --older-than 7d --dry-run",
            f"",
            f"# Files with 'EXCLUDE_ME' pattern:",
            f"python s3_cleaner.py --bucket {bucket_name} --exclude EXCLUDE_ME --dry-run",
            f"",
            f"# Large files over 10MB:",
            f"python s3_cleaner.py --bucket {bucket_name} --min-size 10MB --dry-run",
            f"",
            f"# Generate report of all files:",
            f"python s3_cleaner.py --bucket {bucket_name} --suffix .log --report log_files.csv --dry-run",
            f"",
            f"# Actual deletion with safety limit:",
            f"python s3_cleaner.py --bucket {bucket_name} --older-than 30d --max-deletions 10 --confirm"
        ]
        
        return examples


def main():
    parser = argparse.ArgumentParser(
        description="Populate MinIO with test files for S3 cleaner testing",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--bucket', default='test-bucket', help='S3 bucket name')
    parser.add_argument('--endpoint-url', default='http://localhost:9000', help='MinIO endpoint')
    parser.add_argument('--access-key', default='minioadmin', help='Access key')
    parser.add_argument('--secret-key', default='minioadmin', help='Secret key')
    parser.add_argument('--num-files', type=int, default=50, help='Number of test files to create')
    parser.add_argument('--clean-first', action='store_true', help='Delete all objects in bucket first')
    parser.add_argument('--list-only', action='store_true', help='Only list current bucket contents')
    parser.add_argument('--export-report', help='Export bucket contents to CSV report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = 'DEBUG' if args.verbose else 'INFO'
    setup_logging(log_level)
    
    try:
        # Initialize populator
        populator = MinIOPopulator(
            bucket=args.bucket,
            endpoint_url=args.endpoint_url,
            access_key=args.access_key,
            secret_key=args.secret_key
        )
        
        # Ensure bucket exists
        if not populator.ensure_bucket_exists():
            print("Failed to create/access bucket")
            return 1
        
        # Handle list-only mode
        if args.list_only:
            populator.show_bucket_summary()
            
            if args.export_report:
                summary = populator.get_bucket_summary()
                success = populator.export_to_csv(summary['objects'], args.export_report)
                if success:
                    print(f"\n📄 Report exported to: {args.export_report}")
            
            return 0
        
        # Clean bucket if requested
        if args.clean_first:
            populator.clean_bucket()
        
        # Create test files
        if args.num_files > 0:
            print(f"\n🚀 Creating {args.num_files} test files...")
            files_created = populator.create_test_files(args.num_files)
            
            print(f"\n🎯 Creating special test cases...")
            special_files = populator.create_special_test_cases()
            
            total_created = files_created + special_files
            print(f"\n✅ Population complete! Created {total_created} files")
        
        # Show final summary
        populator.show_bucket_summary()
        
        # Export report if requested
        if args.export_report:
            summary = populator.get_bucket_summary()
            success = populator.export_to_csv(summary['objects'], args.export_report)
            if success:
                print(f"\n📄 Report exported to: {args.export_report}")
        
        # Show example commands
        print(f"\n💡 Example s3_cleaner.py test commands:")
        examples = populator.generate_example_commands(args.bucket)
        for example in examples:
            print(f"   {example}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 