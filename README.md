# QueueCTL - Background Job Queue System

A production-grade, CLI-based background job queue system with worker processes, automatic retry with exponential backoff, and a Dead Letter Queue (DLQ) for permanently failed jobs.

## 🎯 Features

- **Job Enqueueing**: Add background jobs to the queue via CLI
- **Multiple Workers**: Run multiple worker processes in parallel
- **Automatic Retry**: Failed jobs are retried automatically with exponential backoff
- **Dead Letter Queue**: Permanently failed jobs are moved to DLQ for manual inspection
- **Persistent Storage**: Jobs survive application restarts (SQLite database)
- **Configuration Management**: Control retry count, backoff base, and other settings
- **Graceful Shutdown**: Workers finish current job before exiting
- **Job Locking**: Prevents duplicate processing of the same job
- **Statistics & Monitoring**: View queue status and job metrics
- **Clean CLI Interface**: User-friendly commands with help text

## 📋 Requirements

- Python 3.8+
- pip (Python package manager)

## 🚀 Installation

### 1. Clone or Download the Repository
```bash
cd queuectl
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
# OR
pip install -e .
```

This will install:
- `click` - CLI framework
- `pydantic` - Data validation
- `tabulate` - Pretty table printing

### 3. Verify Installation
```bash
queuectl --help
```

## 📖 Usage

### Basic Commands

#### Enqueue a Job
```bash
# Simple command
queuectl enqueue "echo 'Hello, World!'"

# With custom job ID and max retries
queuectl enqueue '{"id":"my-job","command":"sleep 2","max_retries":5}'
```

#### Start Workers
```bash
# Start a single worker
queuectl worker start

# Start 3 workers in parallel
queuectl worker start --count 3
```

#### View Queue Status
```bash
queuectl status
```

Output:
```
╒════════════════════════╤═════════╕
│ State                  │ Count   │
╞════════════════════════╪═════════╡
│ Total Jobs             │ 10      │
├────────────────────────┼─────────┤
│ Pending                │ 3       │
├────────────────────────┼─────────┤
│ Processing             │ 2       │
├────────────────────────┼─────────┤
│ Completed              │ 4       │
├────────────────────────┼─────────┤
│ Failed                 │ 0       │
├────────────────────────┼─────────┤
│ Dead Letter Queue      │ 1       │
╘════════════════════════╧═════════╛
```

#### List Jobs
```bash
# List all jobs
queuectl list

# Filter by state
queuectl list --state pending
queuectl list --state completed
queuectl list --state dead

# Limit results
queuectl list --limit 20
```

#### Dead Letter Queue (DLQ) Operations
```bash
# View all DLQ jobs
queuectl dlq list

# Retry a specific job from DLQ
queuectl dlq retry job-id-here
```

#### Get Job Details
```bash
queuectl info job-id-here
```

#### Configuration Management
```bash
# View all configuration
queuectl config get

# Get specific config value
queuectl config get max-retries

# Set configuration value
queuectl config set max-retries 5
queuectl config set backoff-base 3
queuectl config set worker-timeout 600

# Reset to defaults
queuectl config reset
```

## 🏗️ Architecture Overview

### Job Lifecycle

```
┌─────────────┐
│   PENDING   │ (Waiting to be picked up by worker)
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│   PROCESSING    │ (Currently being executed)
└──────┬──────────┘
       │
       ├─── Success ──────────┐
       │                       │
       ▼                       ▼
┌─────────────────┐    ┌──────────────┐
│   COMPLETED     │    │    FAILED    │
└─────────────────┘    └──────┬───────┘
                               │
                     ┌─────────┴─────────┐
                     │                   │
            Retry < max_retries    Retry ≥ max_retries
                     │                   │
                     ▼                   ▼
                  PENDING          ┌──────────┐
                                   │   DEAD   │ (DLQ)
                                   └──────────┘
```

### Data Persistence

Jobs are stored in SQLite database located at:
- **Linux/Mac**: `~/.queuectl/jobs.db`
- **Windows**: `%USERPROFILE%\.queuectl\jobs.db`

Configuration is stored at:
- **Linux/Mac**: `~/.queuectl/config.json`
- **Windows**: `%USERPROFILE%\.queuectl\config.json`

### Job Schema

Each job contains:
```json
{
  "id": "unique-job-id",
  "command": "shell command to execute",
  "state": "pending|processing|completed|failed|dead",
  "attempts": 0,
  "max_retries": 3,
  "created_at": "2025-11-04T10:30:00Z",
  "updated_at": "2025-11-04T10:30:00Z"
}
```

### Worker Process

1. **Job Polling**: Worker polls for pending jobs every 1 second
2. **Job Locking**: Worker acquires lock to prevent duplicate processing
3. **Command Execution**: Worker executes the job command in a shell
4. **Result Processing**:
   - **Success** (exit code 0): Mark as COMPLETED
   - **Failure** (non-zero exit): Increment attempts
     - If `attempts < max_retries`: Return to PENDING (exponential backoff)
     - If `attempts >= max_retries`: Move to DEAD (DLQ)
5. **Graceful Shutdown**: Worker finishes current job before stopping

### Retry Mechanism

- **Exponential Backoff Formula**: `delay = backoff_base ^ attempts` seconds
- **Default Configuration**:
  - `backoff_base`: 2
  - `max_retries`: 3
  - `worker_timeout`: 300 seconds (5 minutes)

Example with default backoff_base=2:
- Attempt 0 (initial): 0 seconds
- Attempt 1 (retry): 2 seconds
- Attempt 2 (retry): 4 seconds
- Attempt 3 (retry): 8 seconds
- After 3 failed attempts → Move to DLQ

## 🔧 Configuration

Configuration is stored in `~/.queuectl/config.json`:

```json
{
  "max_retries": 3,
  "backoff_base": 2,
  "worker_timeout": 300
}
```

### Configuration Options

| Key | Default | Description |
|-----|---------|-------------|
| `max_retries` | 3 | Maximum number of retry attempts |
| `backoff_base` | 2 | Base for exponential backoff calculation |
| `worker_timeout` | 300 | Timeout for job execution in seconds |

## 🧪 Testing

### Run Unit Tests
```bash
python tests/test_queuectl.py
```

### Run Integration Tests
```bash
python tests/test_integration.py
```

### Test Scenarios Covered

1. ✅ **Basic Job Enqueue**: Job is created and stored
2. ✅ **Job Retry & DLQ**: Failed jobs retry and move to DLQ after max attempts
3. ✅ **Multiple Workers**: Multiple workers process jobs without conflicts
4. ✅ **Job Persistence**: Jobs survive application restart
5. ✅ **Command Execution**: Success/failure handled correctly
6. ✅ **Configuration Management**: Config can be set, get, and reset
7. ✅ **DLQ Retry**: Jobs from DLQ can be retried
8. ✅ **Queue Statistics**: Stats accurately reflect job counts

## 📝 Usage Examples

### Example 1: Simple Echo Job
```bash
# Enqueue
queuectl enqueue "echo 'Processing...'"

# Start worker
queuectl worker start --count 1

# View status
queuectl status
```

### Example 2: Batch Processing
```bash
# Enqueue multiple jobs
queuectl enqueue "python process_file.py file1.txt"
queuectl enqueue "python process_file.py file2.txt"
queuectl enqueue "python process_file.py file3.txt"

# Start multiple workers for parallel processing
queuectl worker start --count 3

# Monitor progress
watch -n 2 'queuectl status'  # Unix/Linux
# OR on Windows PowerShell:
# while ($true) { Clear-Host; queuectl status; Start-Sleep -s 2 }

# List completed jobs
queuectl list --state completed

# Handle failed jobs from DLQ
queuectl dlq list
queuectl dlq retry job-id  # Retry a specific job
```

### Example 3: Custom Configuration
```bash
# Set higher retry count for important jobs
queuectl config set max-retries 10

# Increase backoff for slower systems
queuectl config set backoff-base 3

# Enqueue with custom settings
queuectl enqueue "important-task"

# Verify configuration
queuectl config get
```

## ⚠️ Assumptions & Trade-offs

### Design Decisions

1. **SQLite for Persistence**: 
   - ✅ No external dependencies (embedded database)
   - ✅ Suitable for small to medium-scale deployments
   - ⚠️ Not ideal for distributed systems (use Redis/RabbitMQ for that)

2. **Single Machine Deployment**:
   - All workers and queues run on the same machine
   - Database file is local
   - Suitable for local task processing

3. **Job Locking**:
   - Uses database-level locking (timestamp + worker_id)
   - Prevents duplicate execution in single-machine setup
   - Not suitable for distributed workers

4. **Exponential Backoff**:
   - Simple formula: `base ^ attempts`
   - Provides reasonable spacing for retries
   - Can be customized via configuration

5. **Graceful Shutdown**:
   - Workers catch SIGINT/SIGTERM signals
   - Complete current job before exiting
   - Pending jobs are left in queue for other workers

6. **No Job Priorities**:
   - Jobs are processed in FIFO order
   - Could be added as a future enhancement

7. **No Scheduled Jobs**:
   - Only immediate job execution supported
   - Could be added by adding `run_at` field to jobs

### Limitations

- Single-machine only (not distributed)
- No job priorities
- No scheduled/delayed job execution
- No job timeout retry (only failure retry)
- No built-in monitoring dashboard (could be added)

## 📊 Bonus Features Implemented

- ✅ Job timeout handling (`worker_timeout` config)
- ✅ Configuration management (CLI-based config)
- ✅ Job output logging (stderr/stdout captured)
- ✅ Statistics and metrics (`queuectl status`)
- ✅ Clean error handling and validation

## 🐛 Troubleshooting

### Issue: "queuectl command not found"
**Solution**: Ensure package is installed with `pip install -e .`

### Issue: Database locked
**Solution**: This shouldn't happen with SQLite. If it does, restart workers and database access.

### Issue: Worker not processing jobs
**Solution**: 
- Check if jobs are in PENDING state: `queuectl list --state pending`
- Check worker timeout isn't too short: `queuectl config get worker-timeout`

### Issue: Jobs stuck in PROCESSING state
**Solution**: 
- Unlock stuck jobs with database access
- Or restart workers (graceful shutdown will free locks)

## 📂 Project Structure

```
queuectl/
├── queuectl/
│   ├── __init__.py           # Package initialization
│   ├── cli.py                # CLI commands
│   ├── models.py             # Job and JobState models
│   ├── database.py           # SQLite persistence layer
│   ├── config.py             # Configuration management
│   ├── queue.py              # Queue manager
│   └── worker.py             # Worker process logic
├── tests/
│   ├── test_queuectl.py      # Unit tests
│   └── test_integration.py   # Integration tests
├── setup.py                  # Package setup
├── pyproject.toml            # Project metadata
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## 🔐 Code Quality

- ✅ Modular architecture with separation of concerns
- ✅ Type hints for better code clarity
- ✅ Comprehensive error handling
- ✅ Logging for debugging
- ✅ Docstrings for all functions
- ✅ Unit and integration tests

## 📄 License

This project is provided as-is for educational and practical use.

## 👨‍💻 Author

Backend Developer Internship Assignment - QueueCTL Implementation

---

## 🚦 Quick Start Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Verify installation: `queuectl --help`
- [ ] Run tests: `python tests/test_integration.py`
- [ ] Enqueue a job: `queuectl enqueue "echo 'Hello'"`
- [ ] Start workers: `queuectl worker start --count 2`
- [ ] Monitor progress: `queuectl status`
- [ ] Check results: `queuectl list --state completed`

Enjoy using QueueCTL! 🎉

# Architecture:
<img width="1636" height="532" alt="Screenshot 2025-11-13 112724" src="https://github.com/user-attachments/assets/99de5a92-3c1a-4e4b-a948-c62e61dcb24b" />




# video Link :
https://drive.google.com/file/d/1Oi2EHEZJQDSda-u_Xh4YCr3nXHNZMyqF/view?usp=sharing
