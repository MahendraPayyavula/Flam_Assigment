"""
CLI interface for queuectl
"""
import click
import json
import sys
import subprocess
import os
from tabulate import tabulate
from datetime import datetime

from .models import Job, JobState
from .queue import get_queue_manager
from .database import get_db
from .config import get_config
from .worker import Worker


@click.version_option("1.0.0")
@click.group()
def main():
    """QueueCTL - CLI-based background job queue system"""
    pass


@main.command()
@click.argument('job_data')
def enqueue(job_data):
    """Enqueue a new job
    
    Example: queuectl enqueue '{"id":"job1","command":"echo hello"}'
    """
    try:
        # Try to parse as JSON first
        try:
            data = json.loads(job_data)
            if isinstance(data, dict):
                command = data.get('command')
                job_id = data.get('id')
                max_retries = data.get('max_retries')
            else:
                # If JSON is not a dict, treat original string as command
                command = job_data
                job_id = None
                max_retries = None
        except json.JSONDecodeError:
            # If not JSON, treat as command string
            command = job_data
            job_id = None
            max_retries = None
        
        if not command:
            click.echo(click.style("Error: No command specified", fg='red'))
            sys.exit(1)
        
        qm = get_queue_manager()
        job = qm.enqueue(command, job_id=job_id, max_retries=max_retries)
        
        click.echo(click.style(f"✓ Job enqueued: {job.id}", fg='green'))
        click.echo(f"  Command: {job.command}")
        click.echo(f"  State: {job.state.value}")
        click.echo(f"  Max retries: {job.max_retries}")
    
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'))
        sys.exit(1)


@main.group()
def worker():
    """Worker commands"""
    pass


@worker.command('start')
@click.option('--count', default=1, help='Number of workers to start')
def worker_start(count):
    """Start worker process(es)
    
    Example: queuectl worker start --count 3
    """
    try:
        if count < 1:
            click.echo(click.style("Error: Count must be >= 1", fg='red'))
            sys.exit(1)
        
        click.echo(f"Starting {count} worker(s)...")
        
        # Start workers in the current process
        workers = []
        try:
            for i in range(count):
                worker_instance = Worker()
                workers.append(worker_instance)
                click.echo(f"Worker {worker_instance.worker_id} started")
            
            # Keep the process running
            if workers:
                workers[0].start()
        
        except KeyboardInterrupt:
            click.echo("\nShutting down workers...")
            for w in workers:
                w.stop()
    
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'))
        sys.exit(1)


@main.command()
def status():
    """Show system status"""
    try:
        qm = get_queue_manager()
        stats = qm.get_stats()
        
        click.echo("\n" + click.style("=== Queue Status ===", fg='cyan', bold=True))
        
        status_table = [
            ["Total Jobs", stats['total']],
            ["Pending", stats['pending']],
            ["Processing", stats['processing']],
            ["Completed", click.style(str(stats['completed']), fg='green')],
            ["Failed", click.style(str(stats['failed']), fg='yellow')],
            ["Dead Letter Queue", click.style(str(stats['dead']), fg='red')],
        ]
        
        click.echo(tabulate(status_table, headers=['State', 'Count'], tablefmt='grid'))
        
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'))
        sys.exit(1)


@main.command()
@click.option('--state', default=None, help='Filter by state (pending, processing, completed, failed, dead)')
@click.option('--limit', default=10, help='Limit number of results')
def list(state, limit):
    """List jobs
    
    Example: queuectl list --state pending
    """
    try:
        qm = get_queue_manager()
        jobs = qm.list_jobs(state=state)
        
        if not jobs:
            click.echo("No jobs found")
            return
        
        # Limit results
        jobs = jobs[:limit]
        
        # Format table
        table_data = []
        for job in jobs:
            table_data.append([
                job.id,
                job.state.value,
                job.command[:50] + "..." if len(job.command) > 50 else job.command,
                f"{job.attempts}/{job.max_retries}",
                job.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])
        
        headers = ["ID", "State", "Command", "Attempts", "Created"]
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        if len(jobs) == limit:
            click.echo(f"\n(showing {limit} jobs, use --limit to change)")
    
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'))
        sys.exit(1)


@main.group()
def dlq():
    """Dead Letter Queue commands"""
    pass


@dlq.command('list')
@click.option('--limit', default=10, help='Limit number of results')
def dlq_list(limit):
    """List dead letter queue jobs"""
    try:
        qm = get_queue_manager()
        jobs = qm.get_dlq_jobs()
        
        if not jobs:
            click.echo("No jobs in DLQ")
            return
        
        # Limit results
        jobs = jobs[:limit]
        
        # Format table
        table_data = []
        for job in jobs:
            table_data.append([
                job.id,
                job.command[:50] + "..." if len(job.command) > 50 else job.command,
                job.attempts,
                job.max_retries,
                job.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])
        
        headers = ["ID", "Command", "Attempts", "Max Retries", "Updated"]
        click.echo(click.style("Dead Letter Queue:", fg='red', bold=True))
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
    
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'))
        sys.exit(1)


@dlq.command('retry')
@click.argument('job_id')
def dlq_retry(job_id):
    """Retry a job from DLQ
    
    Example: queuectl dlq retry job1
    """
    try:
        qm = get_queue_manager()
        job = qm.retry_dlq_job(job_id)
        
        click.echo(click.style(f"✓ Job {job_id} moved back to queue for retry", fg='green'))
    
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'))
        sys.exit(1)


@main.group()
def config():
    """Configuration commands"""
    pass


@config.command('get')
@click.argument('key', required=False)
def config_get(key):
    """Get configuration value
    
    Example: queuectl config get max-retries
    """
    try:
        cfg = get_config()
        
        if key:
            value = cfg.get(key)
            if value is None:
                click.echo(click.style(f"Config key '{key}' not found", fg='red'))
                sys.exit(1)
            click.echo(f"{key}={value}")
        else:
            all_config = cfg.get_all()
            click.echo(click.style("Current Configuration:", fg='cyan', bold=True))
            for k, v in sorted(all_config.items()):
                click.echo(f"  {k}: {v}")
    
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'))
        sys.exit(1)


@config.command('set')
@click.argument('key')
@click.argument('value')
def config_set(key, value):
    """Set configuration value
    
    Example: queuectl config set max-retries 5
    """
    try:
        cfg = get_config()
        
        # Try to parse value as number
        try:
            parsed_value = int(value)
        except ValueError:
            try:
                parsed_value = float(value)
            except ValueError:
                parsed_value = value
        
        cfg.set(key, parsed_value)
        click.echo(click.style(f"✓ {key} = {parsed_value}", fg='green'))
    
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'))
        sys.exit(1)


@config.command('reset')
@click.confirmation_option(prompt='Are you sure you want to reset to defaults?')
def config_reset():
    """Reset configuration to defaults"""
    try:
        cfg = get_config()
        cfg.reset()
        click.echo(click.style("✓ Configuration reset to defaults", fg='green'))
    
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'))
        sys.exit(1)


@main.command()
@click.argument('job_id')
def info(job_id):
    """Get detailed job information
    
    Example: queuectl info job1
    """
    try:
        qm = get_queue_manager()
        job = qm.get_job(job_id)
        
        if not job:
            click.echo(click.style(f"Job {job_id} not found", fg='red'))
            sys.exit(1)
        
        click.echo(click.style(f"Job Details: {job_id}", fg='cyan', bold=True))
        click.echo(f"  Command: {job.command}")
        click.echo(f"  State: {job.state.value}")
        click.echo(f"  Attempts: {job.attempts}/{job.max_retries}")
        click.echo(f"  Created: {job.created_at.isoformat()}")
        click.echo(f"  Updated: {job.updated_at.isoformat()}")
    
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'))
        sys.exit(1)


@main.command()
def version():
    """Show version information"""
    click.echo("queuectl version 1.0.0")


if __name__ == '__main__':
    main()
