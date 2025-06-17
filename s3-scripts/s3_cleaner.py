#!/usr/bin/env python3
"""
S3 Cleaner - Smart Cleanup Tool

Smart S3 cleanup tool using the shared S3Utils module.
Supports filtering by time, size, patterns, and more.
"""

import argparse
import sys
from typing import List

from s3_utils import S3Utils, S3FilterUtils, setup_logging


class S3Cleaner(S3Utils):
    """S3 Cleaner class that extends S3Utils with cleanup-specific functionality"""
    
    def __init__(self, bucket: str, endpoint_url: str = None, 
                 access_key: str = None, secret_key: str = None, 
                 prefix: str = None, dry_run: bool = True):
        """
        Initialize S3 Cleaner
        
        Args:
            bucket: S3 bucket name
            endpoint_url: S3 endpoint URL
            access_key: AWS access key
            secret_key: AWS secret key
            prefix: Default prefix for operations
            dry_run: Whether to run in dry-run mode by default
        """
        super().__init__(bucket, endpoint_url, access_key, secret_key, prefix=prefix)
        self.dry_run = dry_run
        
    def clean_objects(self, older_than: str = None, since: str = None,
                     exclude_patterns: List[str] = None, suffix: str = None,
                     min_size: str = None, max_size: str = None,
                     max_deletions: int = None, concurrency: int = 4,
                     generate_report: str = None, confirm: bool = False) -> dict:
        """
        Main cleanup method with comprehensive filtering
        
        Args:
            older_than: Delete files older than this (e.g., '7d', '12h')
            since: Delete files since this date
            exclude_patterns: List of patterns to exclude
            suffix: Only delete files with this suffix
            min_size: Minimum file size (e.g., '1MB')
            max_size: Maximum file size (e.g., '100MB')
            max_deletions: Maximum number of files to delete (safety limit)
            concurrency: Number of concurrent deletion threads
            generate_report: Path to save CSV report
            confirm: Actually perform deletions (overrides dry_run)
            
        Returns:
            dict: Results summary
        """
        # Parse filters
        min_date, max_date = S3FilterUtils.parse_time_filter(older_than, since)
        min_bytes, max_bytes = S3FilterUtils.parse_size_filter(min_size, max_size)
        
        # Get all objects
        self.logger.info("Listing objects...")
        all_objects = list(self.list_objects())
        self.logger.info(f"Found {len(all_objects)} total objects")
        
        # Apply filters
        filtered_objects = list(S3FilterUtils.filter_objects(
            all_objects,
            min_date=min_date,
            max_date=max_date,
            exclude_patterns=exclude_patterns,
            suffix=suffix,
            min_size=min_bytes,
            max_size=max_bytes
        ))
        
        self.logger.info(f"After filtering: {len(filtered_objects)} objects match criteria")
        
        # Apply max_deletions limit
        if max_deletions and len(filtered_objects) > max_deletions:
            self.logger.warning(f"Limiting deletions to {max_deletions} objects (safety limit)")
            filtered_objects = filtered_objects[:max_deletions]
        
        # Generate report if requested
        if generate_report:
            success = self.export_to_csv(filtered_objects, generate_report)
            if success:
                self.logger.info(f"Report saved to {generate_report}")
            else:
                self.logger.error(f"Failed to generate report at {generate_report}")
        
        # Calculate summary statistics
        total_size = sum(obj['Size'] for obj in filtered_objects)
        results = {
            'total_objects': len(all_objects),
            'matched_objects': len(filtered_objects),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / 1024 / 1024,
            'deleted_objects': 0,
            'failed_deletions': 0,
            'dry_run': self.dry_run and not confirm
        }
        
        if not filtered_objects:
            self.logger.info("No objects matched the filter criteria")
            return results
        
        # Show what would be deleted
        self.logger.info(f"Objects to delete: {len(filtered_objects)}")
        self.logger.info(f"Total size to delete: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
        
        # Perform deletion or dry run
        if self.dry_run and not confirm:
            self.logger.info("DRY RUN - No files will be deleted")
            self._show_deletion_preview(filtered_objects)
        else:
            self.logger.info("Performing actual deletions...")
            results['dry_run'] = False
            
            # Perform deletions
            keys_to_delete = [obj['Key'] for obj in filtered_objects]
            successful, failed = self.delete_objects_batch(keys_to_delete, concurrency)
            
            results['deleted_objects'] = successful
            results['failed_deletions'] = failed
            
            self.logger.info(f"Deletion complete: {successful} successful, {failed} failed")
        
        return results
    
    def _show_deletion_preview(self, objects: List[dict], max_preview: int = 20) -> None:
        """Show preview of objects that would be deleted"""
        self.logger.info(f"Preview of objects to delete (showing first {min(len(objects), max_preview)}):")
        
        for i, obj in enumerate(objects[:max_preview]):
            size_human = obj['Size'] / 1024 / 1024 if obj['Size'] > 1024*1024 else obj['Size'] / 1024
            size_unit = 'MB' if obj['Size'] > 1024*1024 else 'KB'
            
            self.logger.info(f"  {i+1:3d}. {obj['Key']} ({size_human:.1f} {size_unit}, {obj['LastModified']})")
        
        if len(objects) > max_preview:
            self.logger.info(f"  ... and {len(objects) - max_preview} more objects")


def main():
    parser = argparse.ArgumentParser(
        description="Smart S3 Cleanup Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - show what would be deleted
  %(prog)s --bucket my-bucket --older-than 30d --dry-run
  
  # Delete files older than 7 days, excluding logs
  %(prog)s --bucket my-bucket --older-than 7d --exclude logs --confirm
  
  # Delete large files (>100MB) with report
  %(prog)s --bucket my-bucket --min-size 100MB --report large_files.csv --confirm
  
  # Interactive mode with safety limits
  %(prog)s --bucket my-bucket --older-than 7d --max-deletions 1000 --verbose
        """
    )
    
    # Connection parameters
    parser.add_argument('--bucket', required=True, help='S3 bucket name')
    parser.add_argument('--endpoint-url', default='http://localhost:9000', 
                       help='S3 endpoint URL (default: MinIO localhost)')
    parser.add_argument('--access-key', default='minioadmin', help='Access key')
    parser.add_argument('--secret-key', default='minioadmin', help='Secret key')
    parser.add_argument('--prefix', help='Only consider objects with this prefix')
    
    # Filtering options
    parser.add_argument('--older-than', help='Delete files older than (e.g., 7d, 12h, 30m)')
    parser.add_argument('--since', help='Delete files since this date')
    parser.add_argument('--exclude', action='append', dest='exclude_patterns',
                       help='Exclude files containing this pattern (can be used multiple times)')
    parser.add_argument('--suffix', help='Only delete files with this suffix')
    parser.add_argument('--min-size', help='Minimum file size (e.g., 1MB, 500KB)')
    parser.add_argument('--max-size', help='Maximum file size (e.g., 1GB, 100MB)')
    
    # Operation options
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Show what would be deleted without deleting (default)')
    parser.add_argument('--confirm', action='store_true',
                       help='Actually perform deletions (overrides --dry-run)')
    parser.add_argument('--max-deletions', type=int,
                       help='Maximum number of files to delete (safety limit)')
    parser.add_argument('--concurrency', type=int, default=4,
                       help='Number of concurrent deletion threads (default: 4)')
    
    # Reporting options
    parser.add_argument('--report', help='Generate CSV report at this path')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Enable quiet mode (errors only)')
    
    args = parser.parse_args()
    
    # Set up logging
    if args.quiet:
        log_level = 'ERROR'
    elif args.verbose:
        log_level = 'DEBUG'
    else:
        log_level = 'INFO'
    
    setup_logging(log_level)
    
    # Validate arguments
    if not args.older_than and not args.since and not args.min_size and not args.max_size and not args.suffix:
        print("Error: At least one filter must be specified (--older-than, --since, --min-size, --max-size, or --suffix)")
        sys.exit(1)
    
    if args.confirm and args.dry_run:
        print("Warning: --confirm overrides --dry-run. Deletions will be performed.")
    
    try:
        # Initialize cleaner
        cleaner = S3Cleaner(
            bucket=args.bucket,
            endpoint_url=args.endpoint_url,
            access_key=args.access_key,
            secret_key=args.secret_key,
            prefix=args.prefix,
            dry_run=args.dry_run
        )
        
        # Perform cleanup
        results = cleaner.clean_objects(
            older_than=args.older_than,
            since=args.since,
            exclude_patterns=args.exclude_patterns,
            suffix=args.suffix,
            min_size=args.min_size,
            max_size=args.max_size,
            max_deletions=args.max_deletions,
            concurrency=args.concurrency,
            generate_report=args.report,
            confirm=args.confirm
        )
        
        # Print summary
        print("\n" + "="*50)
        print("CLEANUP SUMMARY")
        print("="*50)
        print(f"Total objects in bucket: {results['total_objects']:,}")
        print(f"Objects matching filters: {results['matched_objects']:,}")
        print(f"Total size of matched objects: {results['total_size_mb']:.2f} MB")
        
        if results['dry_run']:
            print("MODE: DRY RUN (no files deleted)")
            print("Use --confirm to perform actual deletions")
        else:
            print("MODE: ACTUAL DELETION")
            print(f"Objects deleted: {results['deleted_objects']:,}")
            print(f"Failed deletions: {results['failed_deletions']:,}")
        
        print("="*50)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 