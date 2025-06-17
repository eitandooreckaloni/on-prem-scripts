import argparse
import boto3
import csv
from datetime import datetime, timedelta
from dateutil import parser as dtparser
import humanfriendly
from concurrent.futures import ThreadPoolExecutor
import os


class S3Cleaner:
    def __init__(self, bucket, endpoint_url, access_key, secret_key, prefix=None):
        self.bucket = bucket
        self.prefix = prefix
        self.s3 = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

    def list_objects(self):
        paginator = self.s3.get_paginator('list_objects_v2')
        operation_parameters = {'Bucket': self.bucket}
        if self.prefix:
            operation_parameters['Prefix'] = self.prefix

        for page in paginator.paginate(**operation_parameters):
            for obj in page.get('Contents', []):
                yield obj

    def delete_object(self, key):
        self.s3.delete_object(Bucket=self.bucket, Key=key)

    @staticmethod
    def parse_time_filter(older_than=None, since=None):
        now = datetime.now(datetime.utcnow().astimezone().tzinfo)
        min_date, max_date = None, None
        if older_than:
            unit = older_than[-1]
            value = int(older_than[:-1])
            delta = {'d': timedelta(days=value), 'h': timedelta(hours=value), 'm': timedelta(minutes=value)}.get(unit)
            if not delta:
                raise ValueError("Invalid time format. Use '7d', '12h', etc.")
            max_date = now - delta
        if since:
            min_date = dtparser.parse(since)
        return min_date, max_date

    @staticmethod
    def parse_size_filter(min_size=None, max_size=None):
        return (
            humanfriendly.parse_size(min_size) if min_size else None,
            humanfriendly.parse_size(max_size) if max_size else None
        )

    def filter_objects(self, objects, min_date, max_date, exclude, suffix, min_size, max_size):
        for obj in objects:
            key = obj['Key']
            last_modified = obj['LastModified']
            size = obj['Size']

            if exclude and any(term in key for term in exclude):
                continue
            if suffix and not key.endswith(suffix):
                continue
            if min_date and last_modified < min_date:
                continue
            if max_date and last_modified > max_date:
                continue
            if min_size and size < min_size:
                continue
            if max_size and size > max_size:
                continue

            yield obj

    def generate_report(self, objects, path):
        with open(path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Key', 'LastModified', 'Size'])
            for obj in objects:
                writer.writerow([obj['Key'], obj['LastModified'], obj['Size']])


def main():
    parser = argparse.ArgumentParser(description="Smart S3 Cleanup Tool")
    parser.add_argument('--bucket', required=True)
    parser.add_argument('--endpoint-url', default='http://localhost:9000')
    parser.add_argument('--access-key', default='minioadmin')
    parser.add_argument('--secret-key', default='minioadmin')
    parser.add_argument('--older-than')
    parser.add_argument('--since')
    parser.add_argument('--exclude', action='append')
    parser.add_argument('--prefix')
    parser.add_argument('--suffix')
    parser.add_argument('--min-size')
    parser.add_argument('--max-size')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--confirm', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--report')
    parser.add_argument('--concurrency', type=int, default=4)

    args = parser.parse_args()

    cleaner = S3Cleaner(
        bucket=args.bucket,
        endpoint_url=args.endpoint_url,
        access_key=args.access_key,
        secret_key=args.secret_key,
        prefix=args.prefix
    )

    all_objects = list(cleaner.list_objects())
    min_date, max_date = S3Cleaner.parse_time_filter(args.older_than, args.since)
    min_size, max_size = S3Cleaner.parse_size_filter(args.min_size, args.max_size)
    matched_objects = list(cleaner.filter_objects(all_objects, min_date, max_date, args.exclude, args.suffix, min_size, max_size))

    if args.report:
        cleaner.generate_report(matched_objects, args.report)
        print(f"Report written to {args.report}")

    if args.dry_run:
        print(f"[Dry Run] {len(matched_objects)} objects would be deleted:")
        for obj in matched_objects:
            print(f" - {obj['Key']} ({obj['Size']} bytes)")
    elif args.confirm:
        print(f"Deleting {len(matched_objects)} objects...")
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = [executor.submit(cleaner.delete_object, obj['Key']) for obj in matched_objects]
            for future in futures:
                future.result()
        print("Deletion complete.")
    else:
        print(f"{len(matched_objects)} objects matched. Use --dry-run to preview or --confirm to delete.")


main()
