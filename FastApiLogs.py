"""
Log Parser for Large Files - Memory Efficient Implementation
Parses large log files, identifies top 5 IPs with 500 errors,
and sends alerts if error rate exceeds threshold.
"""

import re
import heapq
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import argparse
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class LogParser:
    """
    Memory-efficient log parser that processes files line by line.
    Supports Apache/Nginx common log format and custom formats.
    """
    
    # Common log format regex patterns
    APACHE_COMMON = re.compile(
        r'(?P<ip>\d+\.\d+\.\d+\.\d+) - - \[(?P<datetime>[^\]]+)\] '
        r'"(?P<method>\w+) (?P<path>[^\s]+) HTTP/[^"]*" '
        r'(?P<status>\d+) (?P<size>\d+|-)'
    )
    
    NGINX_COMBINED = re.compile(
        r'(?P<ip>\d+\.\d+\.\d+\.\d+) - - \[(?P<datetime>[^\]]+)\] '
        r'"(?P<method>\w+) (?P<path>[^\s]+) HTTP/[^"]*" '
        r'(?P<status>\d+) (?P<size>\d+|-) '
        r'"(?P<referrer>[^"]*)" "(?P<user_agent>[^"]*)"'
    )
    
    # JSON format for modern applications
    JSON_FORMAT = 'json'
    
    def __init__(
        self,
        log_format: str = 'apache',
        time_window_minutes: Optional[int] = None
    ):
        """
        Initialize the log parser.
        
        Args:
            log_format: 'apache', 'nginx', or 'json'
            time_window_minutes: If set, only count errors within this time window
        """
        self.log_format = log_format
        self.time_window_minutes = time_window_minutes
        self.ip_500_errors = Counter()
        self.ip_total_requests = Counter()
        self.total_requests = 0
        self.total_500_errors = 0
        self.parse_errors = 0
        
    def parse_line(self, line: str) -> Optional[Dict[str, str]]:
        """
        Parse a single log line and extract relevant fields.
        
        Args:
            line: Single line from log file
            
        Returns:
            Dictionary with parsed fields or None if parsing fails
        """
        line = line.strip()
        if not line:
            return None
            
        try:
            if self.log_format == 'json':
                return json.loads(line)
            elif self.log_format == 'nginx':
                match = self.NGINX_COMBINED.match(line)
            else:  # apache or default
                match = self.APACHE_COMMON.match(line)
                
            if match:
                return match.groupdict()
            else:
                self.parse_errors += 1
                return None
                
        except Exception as e:
            self.parse_errors += 1
            return None
    
    def is_within_time_window(self, log_datetime: str) -> bool:
        """
        Check if log entry is within the specified time window.
        
        Args:
            log_datetime: Datetime string from log entry
            
        Returns:
            True if within window or no window set, False otherwise
        """
        if not self.time_window_minutes:
            return True
            
        try:
            # Parse common log datetime format: 01/Jan/2026:12:00:00 +0000
            log_time = datetime.strptime(
                log_datetime.split()[0],
                '%d/%b/%Y:%H:%M:%S'
            )
            now = datetime.now()
            diff_minutes = (now - log_time).total_seconds() / 60
            return diff_minutes <= self.time_window_minutes
        except Exception:
            return True  # Include if we can't parse the time
    
    def process_file(self, filepath: str, chunk_size: int = 8192) -> None:
        """
        Process log file line by line without loading into memory.
        
        Args:
            filepath: Path to log file
            chunk_size: Buffer size for reading file
        """
        print(f"Processing log file: {filepath}")
        print(f"Using {chunk_size} byte chunks for memory efficiency\n")
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            line_count = 0
            
            for line in f:
                line_count += 1
                
                # Progress indicator for large files
                if line_count % 100000 == 0:
                    print(f"Processed {line_count:,} lines... "
                          f"(Found {self.total_500_errors:,} 500 errors)")
                
                parsed = self.parse_line(line)
                if not parsed:
                    continue
                
                # Extract fields (handle both dict key formats)
                ip = parsed.get('ip') or parsed.get('remote_addr')
                status = parsed.get('status') or parsed.get('status_code')
                log_time = parsed.get('datetime') or parsed.get('timestamp')
                
                if not ip or not status:
                    continue
                
                # Check time window if specified
                if log_time and not self.is_within_time_window(log_time):
                    continue
                
                # Track statistics
                self.total_requests += 1
                self.ip_total_requests[ip] += 1
                
                # Track 500 errors
                if str(status).startswith('5'):
                    self.total_500_errors += 1
                    self.ip_500_errors[ip] += 1
        
        print(f"\nProcessing complete!")
        print(f"Total lines processed: {line_count:,}")
        print(f"Total requests: {self.total_requests:,}")
        print(f"Total 500 errors: {self.total_500_errors:,}")
        print(f"Parse errors: {self.parse_errors:,}\n")
    
    def get_top_ips(self, n: int = 5) -> List[Tuple[str, int]]:
        """
        Get top N IPs with most 500 errors using heap for efficiency.
        
        Args:
            n: Number of top IPs to return
            
        Returns:
            List of (IP, error_count) tuples
        """
        # heapq.nlargest is memory efficient for getting top N
        return heapq.nlargest(n, self.ip_500_errors.items(), key=lambda x: x[1])
    
    def calculate_error_rate(self) -> float:
        """
        Calculate overall 500 error rate.
        
        Returns:
            Error rate as percentage
        """
        if self.total_requests == 0:
            return 0.0
        return (self.total_500_errors / self.total_requests) * 100


class AlertManager:
    """
    Manages different types of alerts (console, email, webhook, file).
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize alert manager with configuration.
        
        Args:
            config: Dictionary with alert configuration
        """
        self.config = config or {}
    
    def send_console_alert(self, message: str) -> None:
        """Print alert to console."""
        print("\n" + "=" * 80)
        print("🚨 ALERT: ERROR THRESHOLD EXCEEDED 🚨")
        print("=" * 80)
        print(message)
        print("=" * 80 + "\n")
    
    def send_email_alert(self, message: str) -> None:
        """
        Send email alert (requires SMTP configuration).
        
        Args:
            message: Alert message to send
        """
        try:
            smtp_config = self.config.get('smtp', {})
            if not smtp_config:
                print("Email alert skipped: No SMTP configuration provided")
                return
            
            msg = MIMEMultipart()
            msg['From'] = smtp_config.get('from_email')
            msg['To'] = smtp_config.get('to_email')
            msg['Subject'] = '🚨 Log Alert: 500 Error Threshold Exceeded'
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(
                smtp_config.get('server'),
                smtp_config.get('port', 587)
            )
            server.starttls()
            server.login(
                smtp_config.get('username'),
                smtp_config.get('password')
            )
            server.send_message(msg)
            server.quit()
            
            print("✓ Email alert sent successfully")
            
        except Exception as e:
            print(f"✗ Failed to send email alert: {e}")
    
    def send_file_alert(self, message: str, filepath: str = 'alerts.log') -> None:
        """
        Write alert to a file.
        
        Args:
            message: Alert message
            filepath: Path to alert log file
        """
        try:
            with open(filepath, 'a') as f:
                timestamp = datetime.now().isoformat()
                f.write(f"\n{'=' * 80}\n")
                f.write(f"ALERT at {timestamp}\n")
                f.write(f"{'=' * 80}\n")
                f.write(message + "\n")
            print(f"✓ Alert written to {filepath}")
        except Exception as e:
            print(f"✗ Failed to write alert to file: {e}")
    
    def send_alert(
        self,
        top_ips: List[Tuple[str, int]],
        error_rate: float,
        threshold: float,
        alert_types: List[str] = None
    ) -> None:
        """
        Send alerts through configured channels.
        
        Args:
            top_ips: List of (IP, error_count) tuples
            error_rate: Current error rate
            threshold: Configured threshold
            alert_types: List of alert types to use
        """
        alert_types = alert_types or ['console']
        
        # Build alert message
        message = f"""
Error Rate Threshold Exceeded!

Current Error Rate: {error_rate:.2f}%
Threshold: {threshold:.2f}%

Top 5 IPs with 500 Errors:
{'=' * 60}
"""
        for i, (ip, count) in enumerate(top_ips, 1):
            message += f"{i}. {ip:<15} - {count:,} errors\n"
        
        message += f"\nTimestamp: {datetime.now().isoformat()}"
        
        # Send through configured channels
        for alert_type in alert_types:
            if alert_type == 'console':
                self.send_console_alert(message)
            elif alert_type == 'email':
                self.send_email_alert(message)
            elif alert_type == 'file':
                self.send_file_alert(message)


def create_sample_log_file(filepath: str = 'sample_server.log', num_lines: int = 10000):
    """
    Create a sample log file for testing purposes.
    
    Args:
        filepath: Path to create log file
        num_lines: Number of log lines to generate
    """
    import random
    
    ips = [
        '192.168.1.1', '192.168.1.2', '192.168.1.3', '192.168.1.4', '192.168.1.5',
        '10.0.0.1', '10.0.0.2', '10.0.0.3', '172.16.0.1', '172.16.0.2'
    ]
    
    # Make some IPs more likely to have 500 errors
    error_ips = ['192.168.1.1', '10.0.0.1', '172.16.0.1']
    
    paths = ['/api/users', '/api/products', '/api/orders', '/health', '/metrics']
    methods = ['GET', 'POST', 'PUT', 'DELETE']
    
    print(f"Generating sample log file: {filepath}")
    
    with open(filepath, 'w') as f:
        for i in range(num_lines):
            ip = random.choice(ips)
            method = random.choice(methods)
            path = random.choice(paths)
            
            # Higher chance of 500 for error_ips
            if ip in error_ips:
                status = random.choices([200, 500], weights=[0.7, 0.3])[0]
            else:
                status = random.choices([200, 404, 500], weights=[0.85, 0.10, 0.05])[0]
            
            size = random.randint(100, 5000)
            
            # Apache common log format
            line = (
                f'{ip} - - [10/Jan/2026:12:00:00 +0000] '
                f'"{method} {path} HTTP/1.1" {status} {size}\n'
            )
            f.write(line)
    
    print(f"✓ Created {num_lines:,} log lines\n")


def main():
    """Main function to run the log parser."""
    parser = argparse.ArgumentParser(
        description='Memory-efficient log parser for identifying 500 errors'
    )
    parser.add_argument(
        'logfile',
        nargs='?',
        help='Path to log file to parse'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=5.0,
        help='Error rate threshold percentage (default: 5.0)'
    )
    parser.add_argument(
        '--top-n',
        type=int,
        default=5,
        help='Number of top IPs to report (default: 5)'
    )
    parser.add_argument(
        '--format',
        choices=['apache', 'nginx', 'json'],
        default='apache',
        help='Log format (default: apache)'
    )
    parser.add_argument(
        '--time-window',
        type=int,
        help='Only analyze logs from last N minutes'
    )
    parser.add_argument(
        '--alert-types',
        nargs='+',
        choices=['console', 'email', 'file'],
        default=['console'],
        help='Alert types to use (default: console)'
    )
    parser.add_argument(
        '--create-sample',
        type=int,
        metavar='NUM_LINES',
        help='Create a sample log file with NUM_LINES lines'
    )
    parser.add_argument(
        '--config',
        help='Path to JSON configuration file for alerts'
    )
    
    args = parser.parse_args()
    
    # Create sample log file if requested
    if args.create_sample:
        sample_file = 'sample_server.log'
        create_sample_log_file(sample_file, args.create_sample)
        if not args.logfile:
            args.logfile = sample_file
    
    if not args.logfile:
        parser.error("Please provide a log file or use --create-sample")
    
    # Load alert configuration if provided
    alert_config = {}
    if args.config:
        try:
            with open(args.config, 'r') as f:
                alert_config = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
    
    # Initialize parser and process file
    log_parser = LogParser(
        log_format=args.format,
        time_window_minutes=args.time_window
    )
    
    try:
        log_parser.process_file(args.logfile)
    except FileNotFoundError:
        print(f"Error: Log file '{args.logfile}' not found")
        return
    except Exception as e:
        print(f"Error processing log file: {e}")
        return
    
    # Get results
    top_ips = log_parser.get_top_ips(args.top_n)
    error_rate = log_parser.calculate_error_rate()
    
    # Display results
    print(f"Analysis Results:")
    print(f"{'=' * 80}")
    print(f"Overall 500 Error Rate: {error_rate:.2f}%")
    print(f"Threshold: {args.threshold:.2f}%")
    print(f"\nTop {args.top_n} IPs with 500 Errors:")
    print(f"{'-' * 80}")
    
    for i, (ip, count) in enumerate(top_ips, 1):
        total = log_parser.ip_total_requests[ip]
        ip_rate = (count / total * 100) if total > 0 else 0
        print(f"{i}. {ip:<15} - {count:,} errors out of {total:,} requests "
              f"({ip_rate:.2f}%)")
    
    # Check threshold and send alerts if exceeded
    if error_rate > args.threshold:
        print(f"\n⚠️  Error rate ({error_rate:.2f}%) exceeds threshold ({args.threshold:.2f}%)")
        alert_manager = AlertManager(alert_config)
        alert_manager.send_alert(top_ips, error_rate, args.threshold, args.alert_types)
    else:
        print(f"\n✓ Error rate is within acceptable threshold")


if __name__ == '__main__':
    main()
