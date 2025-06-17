#!/bin/bash

# Test Scenarios for S3 Cleaner v2 (OOP Version)
# Run this script to easily test various cleanup scenarios with the refactored tools

BUCKET="test-bucket"
PYTHON="python3"

echo "🧪 S3 Cleaner Test Scenarios"
echo "============================="

# Function to run a test scenario
run_test() {
    local description="$1"
    local command="$2"
    
    echo ""
    echo "📋 Test: $description"
    echo "🔧 Command: $command"
    echo "---"
    eval $command
    echo ""
    read -p "Press Enter to continue to next test..."
}

# Check if MinIO is running
echo "🔍 Checking MinIO status..."
if ! curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo "❌ MinIO doesn't appear to be running at localhost:9000"
    echo "💡 Run: ./start-minio.sh"
    exit 1
fi
echo "✅ MinIO is running"

# Menu for test options
echo ""
echo "Select a test scenario:"
echo "1) Populate test bucket with sample files"
echo "2) Quick cleanup tests (dry-run)"
echo "3) Advanced filtering tests"
echo "4) Size-based filtering tests"
echo "5) Report generation and export tests"
echo "6) Show bucket contents"
echo "7) Clean bucket (delete all files)"
echo "8) Run comprehensive test suite"
echo "9) Exit"

read -p "Enter choice (1-9): " choice

case $choice in
    1)
        echo "🚀 Populating test bucket..."
        $PYTHON populate_minio.py --bucket $BUCKET --num-files 60 --clean-first --verbose
        ;;
    
    2)
        echo "🧪 Running quick cleanup tests..."
        
        run_test "List all files (dry-run with detailed output)" \
            "$PYTHON s3_cleaner.py --bucket $BUCKET --suffix .txt --dry-run"
        
        run_test "Files older than 30 days (with detailed preview)" \
            "$PYTHON s3_cleaner.py --bucket $BUCKET --older-than 30d --dry-run --verbose"
        
        run_test "Files older than 7 days (with size info)" \
            "$PYTHON s3_cleaner.py --bucket $BUCKET --older-than 7d --dry-run"
        
        run_test "Recent files with max deletions safety limit" \
            "$PYTHON s3_cleaner.py --bucket $BUCKET --older-than 1d --max-deletions 5 --dry-run"
        ;;
    
    3)
        echo "🎯 Running advanced filtering tests..."
        
        run_test "Multiple exclude patterns" \
            "$PYTHON s3_cleaner.py --bucket $BUCKET --exclude EXCLUDE_ME --exclude temp --dry-run"
        
        run_test "Complex filter: old .log files excluding models" \
            "$PYTHON s3_cleaner.py --bucket $BUCKET --older-than 7d --suffix .log --exclude models --dry-run"
        
        run_test "Prefix filtering with size limits" \
            "$PYTHON s3_cleaner.py --bucket $BUCKET --prefix large_files/ --min-size 1MB --dry-run"
        
        run_test "Date range filtering (since parameter)" \
            "$PYTHON s3_cleaner.py --bucket $BUCKET --since '2024-01-01' --max-size 1KB --dry-run"
        ;;
    
    4)
        echo "📏 Running size-based filtering tests..."
        
        run_test "Large files with detailed reporting" \
            "$PYTHON s3_cleaner.py --bucket $BUCKET --min-size 10MB --dry-run --verbose"
        
        run_test "Medium files with size range" \
            "$PYTHON s3_cleaner.py --bucket $BUCKET --min-size 100KB --max-size 1MB --dry-run"
        
        run_test "Tiny files with safety limits" \
            "$PYTHON s3_cleaner.py --bucket $BUCKET --max-size 1KB --max-deletions 10 --dry-run"
        ;;
    
    5)
        echo "📊 Running report generation and export tests..."
        
        run_test "Generate CSV report of all files" \
            "$PYTHON s3_cleaner.py --bucket $BUCKET --suffix .txt --dry-run --report all_files.csv && echo 'Report saved!' && head -5 all_files.csv"
        
        run_test "Export bucket contents using populator" \
            "$PYTHON populate_minio.py --bucket $BUCKET --list-only --export-report bucket_contents.csv && echo 'Bucket export saved!' && head -5 bucket_contents.csv"
        
        run_test "Large files report with metadata" \
            "$PYTHON s3_cleaner.py --bucket $BUCKET --min-size 1MB --dry-run --report large_files.csv --verbose"
        ;;
    
    6)
        echo "📋 Showing bucket contents..."
        $PYTHON populate_minio.py --bucket $BUCKET --list-only --verbose
        ;;
    
    7)
        echo "🧹 Cleaning bucket..."
        read -p "Are you sure you want to delete ALL files in bucket '$BUCKET'? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            $PYTHON populate_minio.py --bucket $BUCKET --clean-first --num-files 0
        else
            echo "Cancelled."
        fi
        ;;
    
    8)
        echo "🚀 Running comprehensive test suite..."
        
        # First populate
        echo "Step 1: Populating with test data..."
        $PYTHON populate_minio.py --bucket $BUCKET --num-files 60 --clean-first
        
        echo ""
        echo "Step 2: Running comprehensive cleanup tests..."
        
        # Time-based tests
        echo "⏰ Time-based filtering:"
        $PYTHON s3_cleaner.py --bucket $BUCKET --older-than 30d --dry-run --verbose
        $PYTHON s3_cleaner.py --bucket $BUCKET --older-than 7d --max-deletions 5 --dry-run
        
        # Pattern-based tests
        echo "🎯 Pattern-based filtering:"
        $PYTHON s3_cleaner.py --bucket $BUCKET --exclude EXCLUDE_ME --exclude temp --dry-run
        $PYTHON s3_cleaner.py --bucket $BUCKET --suffix .log --exclude models --dry-run
        
        # Size-based tests
        echo "📏 Size-based filtering:"
        $PYTHON s3_cleaner.py --bucket $BUCKET --min-size 10MB --dry-run
        $PYTHON s3_cleaner.py --bucket $BUCKET --min-size 1KB --max-size 100KB --dry-run
        
        # Generate multiple reports
        echo "📊 Generating multiple reports:"
        $PYTHON s3_cleaner.py --bucket $BUCKET --older-than 7d --dry-run --report old_files.csv
        $PYTHON s3_cleaner.py --bucket $BUCKET --min-size 1MB --dry-run --report large_files.csv
        $PYTHON populate_minio.py --bucket $BUCKET --list-only --export-report complete_inventory.csv
        
        echo "✅ Comprehensive test suite completed!"
        echo "📄 Generated reports: old_files.csv, large_files.csv, complete_inventory.csv"
        ;;
    
    9)
        echo "👋 Goodbye!"
        exit 0
        ;;
    
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac

echo ""
echo "✅ Test scenario completed!"
echo ""
echo "🔧 Available tools:"
echo "   • s3_utils.py       - Shared OOP utilities"
echo "   • s3_cleaner.py     - S3 cleaner with advanced features"
echo "   • populate_minio.py - Test data generator"
echo ""
echo "💡 Features provided:"
echo "   • Better error handling and logging"
echo "   • Multiple filtering options (size, date, patterns)"
echo "   • Enhanced reporting capabilities"
echo "   • Reusable OOP design for extending functionality" 