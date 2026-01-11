# Log Parser - Memory Efficient 500 Error Analyzer

A Python script that efficiently parses large log files (even 50GB+) without loading them into memory, identifies the top 5 IP addresses returning 500 errors, and sends alerts if error rates exceed a threshold.

## Features

- **Memory Efficient**: Processes files line-by-line using streaming
- **Large File Support**: Can handle 50GB+ files without memory issues
- **Multiple Log Formats**: Supports Apache, Nginx, and JSON formats
- **Time Window Analysis**: Optionally analyze only recent logs
- **Multiple Alert Channels**: Console, email, and file-based alerts
- **Detailed Statistics**: Comprehensive error analysis and reporting
- **Sample Data Generation**: Built-in test data generator

## Quick Start

### Basic Usage

```bash
# Analyze a log file with default settings (5% threshold)
python FastApiLogs.py /path/to/server.log

# Create a sample log file for testing
python FastApiLogs.py --create-sample 100000

# Analyze with custom threshold
python FastApiLogs.py server.log --threshold 2.5

# Get top 10 IPs instead of default 5
python FastApiLogs.py server.log --top-n 10
```

### Advanced Usage

```bash
# Analyze only logs from last 60 minutes
python FastApiLogs.py server.log --time-window 60

# Use Nginx log format
python FastApiLogs.py nginx_access.log --format nginx

# Enable multiple alert types
python FastApiLogs.py server.log --alert-types console email file

# Use email alerts with config file
python FastApiLogs.py server.log --alert-types email --config alert_config.json
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `logfile` | Path to log file to parse | Required |
| `--threshold` | Error rate threshold percentage | 5.0 |
| `--top-n` | Number of top IPs to report | 5 |
| `--format` | Log format (apache/nginx/json) | apache |
| `--time-window` | Analyze last N minutes only | None |
| `--alert-types` | Alert channels (console/email/file) | console |
| `--create-sample` | Create sample log with N lines | None |
| `--config` | Path to alert config JSON file | None |

## Log Format Support

### Apache Common Log Format
```
192.168.1.1 - - [10/Jan/2026:12:00:00 +0000] "GET /api/users HTTP/1.1" 500 1234
```

### Nginx Combined Log Format
```
192.168.1.1 - - [10/Jan/2026:12:00:00 +0000] "GET /api/users HTTP/1.1" 500 1234 "http://example.com" "Mozilla/5.0"
```

### JSON Format
```json
{"ip": "192.168.1.1", "status": 500, "path": "/api/users", "timestamp": "2026-01-10T12:00:00"}
```

## Email Alert Configuration

Create `alert_config.json`:

```json
{
  "smtp": {
    "server": "smtp.gmail.com",
    "port": 587,
    "from_email": "alerts@example.com",
    "to_email": "admin@example.com",
    "username": "your-email@gmail.com",
    "password": "your-app-password"
  }
}
```

**Note**: For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password.

## Performance Characteristics

- **Memory Usage**: Constant ~10-50MB regardless of file size
- **Processing Speed**: ~100,000-500,000 lines/second (varies by hardware)
- **50GB File**: Approximately 10-30 minutes on typical hardware
- **Disk I/O**: Uses 8KB chunks for efficient buffering

## How It Works

### Memory Efficiency

The script uses several techniques to avoid loading the entire file:

1. **Streaming**: Reads file line-by-line using Python's file iterator
2. **Aggregation**: Stores only IP counts, not raw log lines
3. **Heap-based Top-N**: Uses `heapq.nlargest()` for efficient top-5 selection
4. **Counter**: Uses `collections.Counter` for memory-efficient counting

### Processing Pipeline

```
Read Line → Parse → Extract IP & Status → Track Counters → Alert if Threshold Exceeded
```

## Example Output

```
Processing log file: server.log
Using 8192 byte chunks for memory efficiency

Processed 100,000 lines... (Found 4,523 500 errors)
Processed 200,000 lines... (Found 9,012 500 errors)

Processing complete!
Total lines processed: 250,000
Total requests: 250,000
Total 500 errors: 10,450
Parse errors: 0

Analysis Results:
================================================================================
Overall 500 Error Rate: 4.18%
Threshold: 5.00%

Top 5 IPs with 500 Errors:
--------------------------------------------------------------------------------
1. 192.168.1.1   - 3,245 errors out of 25,000 requests (12.98%)
2. 10.0.0.1      - 2,890 errors out of 28,000 requests (10.32%)
3. 172.16.0.1    - 2,015 errors out of 20,000 requests (10.08%)
4. 192.168.1.2   - 1,200 errors out of 50,000 requests (2.40%)
5. 10.0.0.2      - 1,100 errors out of 45,000 requests (2.44%)

✓ Error rate is within acceptable threshold
```

## Use Cases

1. **Production Monitoring**: Analyze production logs to identify problematic IPs
2. **Incident Response**: Quickly identify attack sources during outages
3. **Capacity Planning**: Understand error patterns for infrastructure planning
4. **Security Analysis**: Detect potential DDoS or brute force attacks
5. **Performance Debugging**: Identify clients experiencing high error rates

## Troubleshooting

### Parse Errors
If you see many parse errors, check that the log format matches:
```bash
# Try different format
python FastApiLogs.py server.log --format nginx
```

### Email Alerts Not Working
- Verify SMTP credentials in config file
- For Gmail, enable "Less secure app access" or use App Password
- Check firewall rules for SMTP port (587)

### Out of Memory
The script should never run out of memory, but if it does:
- Check for extremely long lines (truncate if needed)
- Ensure you're not piping output to tools that buffer

## Testing

Generate a test log file:

```bash
# Create 1 million line test file
python FastApiLogs.py --create-sample 1000000

# Analyze it
python FastApiLogs.py sample_server.log --threshold 10
```

## License

MIT License - feel free to use and modify as needed.
