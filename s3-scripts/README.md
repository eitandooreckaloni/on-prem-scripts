# S3 Tools for On-Premises Environment

A collection of Object-Oriented Python tools for managing S3-compatible storage (MinIO/AWS S3) in secure on-premises environments.

## 🏗️ Architecture

### Core Components

#### `s3_utils.py` - Shared Utilities Module
- **`S3Utils`** - Base class with common S3 operations
- **`S3FilterUtils`** - Static methods for filtering objects
- **`setup_logging()`** - Centralized logging configuration

#### Tool Classes (extend S3Utils)
- **`S3Cleaner`** - Smart cleanup with comprehensive filtering
- **`MinIOPopulator`** - Test data generation for validation

## 🛠️ Tools Available

### Core Tools
- `s3_cleaner.py` - Smart cleanup with advanced filtering, logging, and safety features
- `populate_minio.py` - Test data generator with ML/CV patterns
- `s3_utils.py` - Shared OOP utilities module

### Test Scripts
- `test_scenarios.sh` - Interactive testing suite
- `start-minio.sh` - MinIO Docker container startup

## 🚀 Quick Start

### 1. Start MinIO
```bash
cd s3-scripts
./start-minio.sh
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Generate Test Data
```bash
# Generate test data
python3 populate_minio.py --bucket test-bucket --num-files 60 --clean-first

# Or use interactive testing
./test_scenarios.sh
```

### 4. Test Cleanup Operations
```bash
# Dry run with advanced features
python3 s3_cleaner.py --bucket test-bucket --older-than 7d --dry-run --verbose

# Generate reports
python3 s3_cleaner.py --bucket test-bucket --min-size 1MB --report large_files.csv --dry-run

# Actual deletion with safety limits
python3 s3_cleaner.py --bucket test-bucket --older-than 30d --max-deletions 10 --confirm
```

## 📊 Key Features

### Enhanced S3Utils Base Class
- **Better error handling** with proper logging
- **Batch operations** for improved performance
- **Flexible connection management** (MinIO/AWS)
- **Built-in CSV export** functionality
- **Comprehensive bucket statistics**

### S3Cleaner Features
```python
# Multiple exclude patterns
--exclude logs --exclude temp --exclude cache

# Size range filtering
--min-size 100KB --max-size 10MB

# Safety limits
--max-deletions 1000

# Enhanced reporting
--report detailed_report.csv --verbose
```

### MinIOPopulator Features
- **ML/CV-specific file patterns** (models, training data, results)
- **Realistic date distributions** (very_old, old, recent, very_recent)
- **Metadata tagging** for better organization
- **Special test cases** for edge case testing
- **Enhanced reporting** with bucket statistics

## 🎯 Use Cases for On-Premises Environment

### Data Lifecycle Management
```bash
# Clean old training artifacts
python3 s3_cleaner.py --bucket ml-artifacts --prefix models/experiments/ --older-than 30d --confirm

# Remove large temporary files
python3 s3_cleaner.py --bucket workspace --min-size 100MB --exclude important --confirm

# Generate cleanup reports for compliance
python3 s3_cleaner.py --bucket data-lake --older-than 90d --report quarterly_cleanup.csv --dry-run
```

### Development & Testing
```bash
# Create realistic test environment
python3 populate_minio.py --bucket dev-testing --num-files 100 --clean-first

# Test cleanup policies safely
python3 s3_cleaner.py --bucket dev-testing --older-than 7d --max-deletions 50 --dry-run

# Export inventory for analysis
python3 populate_minio.py --bucket production --list-only --export-report inventory.csv
```

## 🧬 Extending the Tools

### Creating New Tools
```python
from s3_utils import S3Utils, S3FilterUtils, setup_logging

class MyS3Tool(S3Utils):
    def __init__(self, bucket, **kwargs):
        super().__init__(bucket, **kwargs)
    
    def my_custom_operation(self):
        objects = list(self.list_objects())
        # Your custom logic here
        return self.export_to_csv(objects, "my_report.csv")
```

### Adding New Filters
```python
# Extend S3FilterUtils with custom filters
@staticmethod
def filter_by_extension(objects, extensions):
    for obj in objects:
        if any(obj['Key'].endswith(ext) for ext in extensions):
            yield obj
```

## 📁 File Structure
```
s3-scripts/
├── s3_utils.py         # 🏗️ Core OOP utilities
├── s3_cleaner.py       # 🧹 S3 cleaner tool
├── populate_minio.py   # 📊 Test data generator
├── test_scenarios.sh   # 🧪 Interactive testing
├── start-minio.sh      # 🐳 MinIO startup
├── requirements.txt    # 📦 Dependencies
└── README.md          # 📖 This file
```

## 🔒 Security Considerations

- **Dry-run by default** - All operations default to preview mode
- **Safety limits** - `--max-deletions` prevents accidental mass deletion  
- **Comprehensive logging** - Full audit trail of all operations
- **Flexible authentication** - Supports various credential methods
- **No external dependencies** - Safe for air-gapped environments

## 💡 Tips for On-Premises Deployment

1. **Test thoroughly** with MinIO before production deployment
2. **Use the interactive test scripts** to validate filtering logic
3. **Generate reports first** before any actual deletions
4. **Set conservative safety limits** initially
5. **Leverage the OOP structure** for custom organizational tools

## 🤝 Contributing

The OOP design makes it easy to extend functionality:
- Add new filter types in `S3FilterUtils`
- Create specialized tools by extending `S3Utils`
- Enhance reporting with additional CSV fields
- Add new test scenarios to the test scripts

This architecture provides a solid foundation for building additional S3 management tools for your specific on-premises requirements. 