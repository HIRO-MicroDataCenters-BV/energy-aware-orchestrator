import asyncio
import logging
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, Any

import numpy as np
import psutil
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

# Configure logging with file output
import os
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist - use /tmp for writable location
log_dir = "/tmp/logs"
os.makedirs(log_dir, exist_ok=True)

# Configure logging with both console and file output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        RotatingFileHandler(
            os.path.join(log_dir, 'workload-type-1.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Workload Type-1 App", description="Scheduled heavy computation workload for specific time windows")

# Global state to track computation status
computation_state = {
    "is_running": False,
    "current_window": None,  # "morning" or "evening" or None
    "last_run": None,
    "current_run_start": None,
    "total_runs": 0,
    "morning_runs": 0,
    "evening_runs": 0,
    "last_memory_allocated_mb": 0.0,
    "last_memory_cleaned_mb": 0.0
}

# Time window configuration (in UTC for consistency)
TIME_WINDOWS = {
    "morning": {"start": dt_time(8, 0), "end": dt_time(10, 0)},   # 8-10 AM
    "evening": {"start": dt_time(18, 0), "end": dt_time(21, 0)}  # 6-9 PM
}

class ComputationStatus(BaseModel):
    is_running: bool
    current_window: str = None
    last_run: str = None
    current_run_start: str = None
    total_runs: int
    morning_runs: int
    evening_runs: int
    cpu_usage: float
    memory_usage: float
    cpu_count: int
    last_memory_allocated_mb: float = 0.0
    last_memory_cleaned_mb: float = 0.0
    next_window: str = None
    time_until_next_window: str = None


def get_current_time_info():
    """Get current time and determine if we're in a computation window."""
    now = datetime.now()
    current_time = now.time()
    
    # Check if current time falls within any window
    for window_name, window_config in TIME_WINDOWS.items():
        if window_config["start"] <= current_time <= window_config["end"]:
            return window_name, now
    
    return None, now


def get_next_window_info():
    """Get information about the next computation window."""
    now = datetime.now()
    current_time = now.time()
    
    # Find the next window today
    for window_name, window_config in TIME_WINDOWS.items():
        if current_time < window_config["start"]:
            next_start = datetime.combine(now.date(), window_config["start"])
            time_diff = next_start - now
            return window_name, str(time_diff).split('.')[0]  # Remove microseconds
    
    # If no window today, next is morning tomorrow
    tomorrow = now.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1)
    time_diff = tomorrow - now
    return "morning", str(time_diff).split('.')[0]


def cpu_memory_intensive_task(duration_seconds: int = 3600) -> Dict[str, Any]:
    """
    Performs intensive CPU and memory computation for extended periods.
    Designed for 2-hour sustained workloads with high resource utilization.
    """
    start_time = time.time()
    end_time = start_time + duration_seconds
    
    operations_count = 0
    matrix_operations = 0
    memory_allocated = 0
    memory_objects = []
    
    logger.info(f"Starting extended heavy computation for {duration_seconds/3600:.1f} hours")
    logger.info(f"Process ID: {os.getpid()}, Initial memory usage: {psutil.virtual_memory().percent:.1f}%")
    
    # Pre-allocate significant memory (about 200MB)
    initial_memory_pool = []
    for i in range(20):
        # Create large arrays to establish baseline memory pressure
        large_array = np.random.rand(1200, 1200).astype(np.float64)  # ~11MB each
        initial_memory_pool.append(large_array)
        memory_allocated += large_array.nbytes
    
    logger.info(f"Pre-allocated {memory_allocated / (1024**2):.1f}MB of memory")
    logger.info(f"Memory usage after pre-allocation: {psutil.virtual_memory().percent:.1f}%")
    
    # Log progress every 5 minutes during extended run
    last_log_time = start_time
    log_interval = 300.0  # 5 minutes
    
    while time.time() < end_time:
        current_time = time.time()
        
        # Log progress periodically
        if current_time - last_log_time >= log_interval:
            elapsed = current_time - start_time
            remaining = end_time - current_time
            current_memory = psutil.virtual_memory().percent
            current_cpu = psutil.cpu_percent(interval=1)
            logger.info(f"Extended computation progress: {elapsed/3600:.2f}h elapsed, "
                       f"{remaining/3600:.2f}h remaining, operations: {operations_count}, "
                       f"memory: {current_memory:.1f}%, CPU: {current_cpu:.1f}%")
            last_log_time = current_time
        
        # Intensive matrix operations (CPU heavy)
        for _ in range(3):  # Multiple operations per cycle
            matrix_a = np.random.rand(300, 300)  # Larger matrices for sustained load
            matrix_b = np.random.rand(300, 300)
            result = np.dot(matrix_a, matrix_b)
            # Additional operations on result
            result = np.transpose(result) @ result  # More CPU work
            matrix_operations += 1
            operations_count += 1
        
        # Memory-intensive operations with sustained pressure
        if operations_count % 3 == 0:  # More frequent memory operations
            # Create and maintain large data structures
            temp_data_pool = []
            for _ in range(8):  # More arrays per cycle
                # Larger arrays for sustained memory pressure
                temp_array = np.random.rand(800, 800).astype(np.float64)  # ~5MB each
                # Perform complex operations to ensure memory is actively used
                temp_array = np.sin(temp_array) * np.cos(temp_array) + np.sqrt(np.abs(temp_array))
                temp_data_pool.append(temp_array)
                memory_allocated += temp_array.nbytes
            
            # Keep more objects in memory for sustained pressure
            memory_objects.extend(temp_data_pool[:4])  # Keep half, let others be GC'd
            
            # Memory management - clean up when pool gets large
            if len(memory_objects) > 100:
                logger.debug(f"Managing memory pool. Current count: {len(memory_objects)}")
                # Remove oldest 20% of objects
                remove_count = len(memory_objects) // 5
                removed = memory_objects[:remove_count]
                memory_objects = memory_objects[remove_count:]
                for obj in removed:
                    memory_allocated -= obj.nbytes
                del removed
        
        # Extended string and data processing (sustained CPU + memory)
        if operations_count % 5 == 0:
            # Large string operations
            large_strings = []
            for i in range(10):
                large_string = f"data_{i}_" * 200000  # ~2MB string each
                processed = large_string.upper().replace("DATA", "PROC").replace("_", "-")
                large_strings.append(processed)
            
            # Process all strings
            combined = "".join(large_strings)
            hash_val = hash(combined)
            del large_strings, combined
        
        # Complex dictionary operations for sustained memory churn
        if operations_count % 7 == 0:
            # Create nested data structures
            complex_dict = {}
            for i in range(2000):  # Larger dictionary
                complex_dict[f"key_{i}"] = {
                    "data": np.random.rand(200),  # Array data
                    "metadata": {
                        "timestamp": current_time,
                        "values": list(range(i, i + 100))
                    }
                }
            
            # Process the dictionary
            total_sum = 0
            for key, value in complex_dict.items():
                total_sum += np.sum(value["data"])
                total_sum += sum(value["metadata"]["values"])
            
            del complex_dict
        
        # Scientific computation simulation (CPU intensive)
        if operations_count % 10 == 0:
            # Simulate scientific computations like FFT, linear algebra
            signal = np.random.rand(8192)  # Larger signal
            fft_result = np.fft.fft(signal)
            ifft_result = np.fft.ifft(fft_result)
            
            # Linear algebra operations
            A = np.random.rand(400, 400)
            B = np.random.rand(400, 400)
            C = A @ B @ A.T  # Chain of matrix operations
            eigenvals = np.linalg.eigvals(C[:100, :100])  # Eigenvalue computation
        
        # Minimal sleep to allow system responsiveness but maintain high load
        time.sleep(0.001)  # 1ms sleep
    
    # Cleanup phase
    total_cleanup = 0
    for obj in memory_objects:
        total_cleanup += obj.nbytes
    for obj in initial_memory_pool:
        total_cleanup += obj.nbytes
    
    del memory_objects, initial_memory_pool
    
    actual_duration = time.time() - start_time
    final_memory_usage = psutil.virtual_memory().percent
    final_cpu_usage = psutil.cpu_percent(interval=1)
    
    result = {
        "duration_hours": actual_duration / 3600,
        "operations_count": operations_count,
        "matrix_operations": matrix_operations,
        "memory_allocated_mb": memory_allocated / (1024**2),
        "memory_cleaned_mb": total_cleanup / (1024**2),
        "final_cpu_usage": final_cpu_usage,
        "final_memory_usage": final_memory_usage
    }
    
    logger.info(f"Extended computation completed: {result}")
    return result


async def run_extended_computation(window_name: str, duration_hours: int = 2):
    """
    Runs extended heavy computation during specified time windows.
    """
    global computation_state
    
    if computation_state["is_running"]:
        logger.warning(f"Computation already running, skipping {window_name} window")
        return
    
    computation_state["is_running"] = True
    computation_state["current_window"] = window_name
    computation_state["current_run_start"] = datetime.now().isoformat()
    computation_state["last_run"] = datetime.now().isoformat()
    computation_state["total_runs"] += 1
    
    if window_name == "morning":
        computation_state["morning_runs"] += 1
    elif window_name == "evening":
        computation_state["evening_runs"] += 1
    
    try:
        # Use all available CPU cores for maximum sustained load
        cpu_count = multiprocessing.cpu_count()
        duration_seconds = duration_hours * 3600  # Convert to seconds
        
        logger.info(f"Starting {window_name} computation window on {cpu_count} cores for {duration_hours} hours")
        
        # Run extended computation on multiple processes
        with ProcessPoolExecutor(max_workers=cpu_count) as executor:
            # Submit long-running tasks to all CPU cores
            futures = [executor.submit(cpu_memory_intensive_task, duration_seconds) 
                      for _ in range(cpu_count)]
            
            # Wait for all tasks to complete
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=duration_seconds + 300)  # 5 minute buffer
                    results.append(result)
                except Exception as e:
                    logger.error(f"Extended computation task failed: {e}")
        
        logger.info(f"{window_name.title()} computation window completed. "
                   f"Results: {len(results)} processes finished")
        
        # Update memory metrics from results
        if results:
            avg_allocated = sum(r.get("memory_allocated_mb", 0) for r in results) / len(results)
            avg_cleaned = sum(r.get("memory_cleaned_mb", 0) for r in results) / len(results)
            computation_state["last_memory_allocated_mb"] = avg_allocated
            computation_state["last_memory_cleaned_mb"] = avg_cleaned
        
    except Exception as e:
        logger.error(f"Error during {window_name} computation: {e}")
    finally:
        computation_state["is_running"] = False
        computation_state["current_window"] = None
        computation_state["current_run_start"] = None


async def time_window_scheduler():
    """
    Background task that monitors time windows and runs computation during specified periods.
    """
    logger.info("Starting time window scheduler for workload-type-1")
    
    while True:
        try:
            current_window, now = get_current_time_info()
            
            if current_window and not computation_state["is_running"]:
                logger.info(f"Entering {current_window} computation window")
                await run_extended_computation(current_window, duration_hours=2)
            
            # Check every minute
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in time window scheduler: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying


@app.on_event("startup")
async def startup_event():
    """
    Start the background time window scheduler when the app starts.
    """
    logger.info("Starting workload-type-1 application")
    # Start the time window scheduler as a background task
    asyncio.create_task(time_window_scheduler())


@app.get("/")
async def root():
    """
    Root endpoint providing basic app information.
    """
    return {
        "app": "Workload Type-1 App",
        "description": "Scheduled heavy computation workload for specific time windows (8-10 AM, 6-9 PM)",
        "version": "1.0.0",
        "status": "running",
        "time_windows": {
            "morning": "08:00 - 10:00 (2 hours)",
            "evening": "18:00 - 21:00 (3 hours)"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for Kubernetes probes.
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/status", response_model=ComputationStatus)
async def get_status():
    """
    Get current computation status and system metrics.
    """
    next_window, time_until = get_next_window_info()
    
    return ComputationStatus(
        is_running=computation_state["is_running"],
        current_window=computation_state["current_window"],
        last_run=computation_state["last_run"],
        current_run_start=computation_state["current_run_start"],
        total_runs=computation_state["total_runs"],
        morning_runs=computation_state["morning_runs"],
        evening_runs=computation_state["evening_runs"],
        cpu_usage=psutil.cpu_percent(interval=1),
        memory_usage=psutil.virtual_memory().percent,
        cpu_count=multiprocessing.cpu_count(),
        last_memory_allocated_mb=computation_state["last_memory_allocated_mb"],
        last_memory_cleaned_mb=computation_state["last_memory_cleaned_mb"],
        next_window=next_window,
        time_until_next_window=time_until
    )


@app.get("/metrics")
async def get_metrics():
    """
    Get current system metrics for monitoring.
    """
    return {
        "cpu_usage": psutil.cpu_percent(interval=1),
        "memory_usage": psutil.virtual_memory().percent,
        "memory_available": psutil.virtual_memory().available,
        "memory_total": psutil.virtual_memory().total,
        "cpu_count": multiprocessing.cpu_count(),
        "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
        "timestamp": datetime.now().isoformat(),
        "current_window": computation_state["current_window"],
        "is_running": computation_state["is_running"]
    }


@app.post("/trigger-morning")
async def trigger_morning_computation():
    """
    Manually trigger morning computation window (for testing).
    """
    if not computation_state["is_running"]:
        asyncio.create_task(run_extended_computation("morning", duration_hours=2))
        return {"message": "Morning computation triggered", "duration": "2 hours"}
    else:
        return {"message": "Computation already running", "current_window": computation_state["current_window"]}


@app.post("/trigger-evening")
async def trigger_evening_computation():
    """
    Manually trigger evening computation window (for testing).
    """
    if not computation_state["is_running"]:
        asyncio.create_task(run_extended_computation("evening", duration_hours=2))
        return {"message": "Evening computation triggered", "duration": "2 hours"}
    else:
        return {"message": "Computation already running", "current_window": computation_state["current_window"]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)