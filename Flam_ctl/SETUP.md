# QueueCTL - Complete Setup & Deployment Guide

## 🚀 Quick Start (5 minutes)

### Windows

1. **Open PowerShell** in the project directory
2. **Run setup script**:
   ```powershell
   .\setup.bat
   ```
3. **Test installation**:
   ```powershell
   queuectl --help
   ```

### Linux/Mac

1. **Open Terminal** in the project directory
2. **Run setup script**:
   ```bash
   bash setup.sh
   ```
3. **Test installation**:
   ```bash
   queuectl --help
   ```

---

## 📝 Manual Setup (if scripts don't work)

### Step 1: Install Python 3.8+

**Windows**: Download from [python.org](https://www.python.org/downloads/)  
**Linux**: `sudo apt install python3 python3-pip`  
**Mac**: `brew install python3`

### Step 2: Install Dependencies

```bash
cd queuectl
pip install -r requirements.txt
```

### Step 3: Install QueueCTL

```bash
pip install -e .
```

### Step 4: Verify Installation

```bash
queuectl --version
```

---

## 🎮 First Run

### Create Your First Job

```bash
# Simple echo job
queuectl enqueue "echo 'Hello, World!'"

# With custom JSON
queuectl enqueue '{"id":"job1","command":"echo hello","max_retries":5}'
```

### Start a Worker

```bash
# Start 1 worker
queuectl worker start

# Or start 3 workers in parallel
queuectl worker start --count 3
```

### Monitor Progress

In another terminal/window:

```bash
# View queue status
queuectl status

# List pending jobs
queuectl list --state pending

# View completed jobs
queuectl list --state completed
```

---

## 🧪 Run Tests

### Quick Tests

```bash
python tests/test_integration.py
```

### Detailed Unit Tests

```bash
python tests/test_queuectl.py
```

### Demo Simulation

```bash
python demo.py
```

### Live Processing Demo

```bash
python demo_live.py
```

---

## 📊 Real-World Examples

### Example 1: Batch File Processing

```bash
# Queue multiple file processing jobs
queuectl enqueue "python process.py file1.csv"
queuectl enqueue "python process.py file2.csv"
queuectl enqueue "python process.py file3.csv"

# Start workers for parallel processing
queuectl worker start --count 4

# Monitor progress
watch -n 1 'queuectl status'  # Unix/Linux
# OR on Windows PowerShell:
# while($true) { clear; queuectl status; start-sleep -s 1 }

# Check completed files
queuectl list --state completed
```

### Example 2: Retry Configuration

```bash
# Configure higher retries for important jobs
queuectl config set max-retries 10
queuectl config set backoff-base 3

# Enqueue critical job
queuectl enqueue "backup-database.sh"

# Start worker
queuectl worker start

# Check status
queuectl status
```

### Example 3: Handle Failed Jobs

```bash
# View failed jobs in DLQ
queuectl dlq list

# Retry specific failed job
queuectl dlq retry job-id-here

# Verify it's back in queue
queuectl list --state pending
```

---

## 🔧 Configuration Management

### View Current Config

```bash
queuectl config get
```

Output:
```
Current Configuration:
  backoff_base: 2
  max_retries: 3
  worker_timeout: 300
```

### Modify Config

```bash
# Increase max retries
queuectl config set max-retries 5

# Change backoff base (for faster retries)
queuectl config set backoff-base 1.5

# Increase timeout for long-running jobs
queuectl config set worker-timeout 600
```

### Reset to Defaults

```bash
queuectl config reset
```

---

## 📂 Project Structure

```
queuectl/
├── queuectl/                  # Main package
│   ├── __init__.py           # Package exports
│   ├── cli.py                # CLI commands (Click framework)
│   ├── models.py             # Job and JobState models
│   ├── database.py           # SQLite persistence
│   ├── config.py             # Configuration management
│   ├── queue.py              # Queue manager
│   └── worker.py             # Worker process logic
├── tests/                     # Test suite
│   ├── test_queuectl.py      # Unit tests
│   └── test_integration.py   # Integration tests
├── demo.py                   # Interactive demo
├── demo_live.py              # Live worker demo
├── setup.py                  # Package setup
├── pyproject.toml            # Project metadata
├── requirements.txt          # Dependencies
├── README.md                 # Main documentation
├── DESIGN.md                 # Architecture details
├── setup.sh                  # Linux/Mac setup
└── setup.bat                 # Windows setup
```

---

## 💾 Data Storage Locations

All data is stored in user's home directory:

**Linux/Mac**:
```
~/.queuectl/
├── jobs.db       (SQLite database)
└── config.json   (Configuration)
```

**Windows**:
```
%USERPROFILE%\.queuectl\
├── jobs.db       (SQLite database)
└── config.json   (Configuration)
```

---

## 🔍 Troubleshooting

### Issue: "queuectl: command not found"

**Solution**:
```bash
# Reinstall the package
pip install -e .

# Or use Python module directly
python -m queuectl.cli --help
```

### Issue: Worker not processing jobs

**Solutions**:
1. Check if jobs are pending:
   ```bash
   queuectl list --state pending
   ```

2. Check worker timeout isn't too short:
   ```bash
   queuectl config get worker-timeout
   ```

3. Restart worker (graceful restart):
   ```bash
   # Press Ctrl+C to stop current worker
   # Then start new one
   queuectl worker start --count 1
   ```

### Issue: Database appears locked

**Solution** (Windows): SQLite file locking is handled automatically. If issues persist:
1. Stop all workers: Press `Ctrl+C`
2. Wait 5 seconds
3. Restart workers

### Issue: Jobs stuck in PROCESSING state

**Possible Causes**:
1. Worker crashed unexpectedly
2. Job timeout too short

**Solution**:
- Stuck jobs will remain in PROCESSING state
- They won't be picked up by other workers
- Stop all workers, the locks will be released on restart

---

## 📈 Performance Tips

### For High Volume (1000+ jobs/minute)

1. **Increase Worker Count**:
   ```bash
   queuectl worker start --count 8  # Adjust based on CPU cores
   ```

2. **Optimize Configuration**:
   ```bash
   queuectl config set worker-timeout 60  # Reduce for faster retries
   queuectl config set backoff-base 1     # No delay between retries
   ```

3. **Monitor Performance**:
   ```bash
   watch -n 2 'queuectl status'
   ```

### For Reliable Processing

1. **Increase Retries**:
   ```bash
   queuectl config set max-retries 10
   ```

2. **Longer Backoff**:
   ```bash
   queuectl config set backoff-base 3
   ```

3. **Increase Timeout**:
   ```bash
   queuectl config set worker-timeout 600
   ```

---

## 🚨 Important Notes

### Data Safety

- Jobs are persisted to SQLite database
- Configuration is saved as JSON
- Both survive application restart

### Worker Behavior

- Workers process jobs FIFO (First In, First Out)
- Multiple workers share the same queue
- Job locking prevents duplicate execution
- Graceful shutdown ensures no data loss

### Limitations

- Single machine only (not distributed)
- No job priorities
- No scheduled jobs
- Jobs are not encrypted in storage

---

## 📞 Support

For issues or questions:

1. Check README.md for common usage
2. Review DESIGN.md for architecture details
3. Run tests: `python tests/test_integration.py`
4. Try demo: `python demo_live.py`

---

## 📄 License

This project is provided as-is for educational and practical use.

---

## ✅ Deployment Checklist

- [ ] Python 3.8+ installed
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Package installed: `pip install -e .`
- [ ] Tests pass: `python tests/test_integration.py`
- [ ] CLI works: `queuectl --help`
- [ ] Demo runs: `python demo_live.py`
- [ ] First job enqueued: `queuectl enqueue "echo test"`
- [ ] Worker starts: `queuectl worker start`
- [ ] Queue monitoring works: `queuectl status`

---

**Enjoy using QueueCTL!** 🎉
