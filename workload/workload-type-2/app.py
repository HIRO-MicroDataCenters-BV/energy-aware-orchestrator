import asyncio
import logging
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
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
            os.path.join(log_dir, 'computation.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Workload Type-2 App", description="Periodic heavy computation workload for power consumption testing")

# Global state to track computation status
computation_state = {
    "is_running": False,
    "last_run": None,
    "next_run": None,
    "total_runs": 0,
    "last_memory_allocated_mb": 0.0,
    "last_memory_cleaned_mb": 0.0
}


class ComputationStatus(BaseModel):
    is_running: bool
    last_run: str = None
    next_run: str = None
    total_runs: int
    cpu_usage: float
    memory_usage: float
    cpu_count: int
    last_memory_allocated_mb: float = 0.0
    last_memory_cleaned_mb: float = 0.0


def cpu_intensive_task(duration_seconds: int = 30) -> Dict[str, Any]:
    """
    Performs CPU and memory-intensive computation for the specified duration.
    Uses matrix multiplication, prime number calculation, and memory allocation.
    """
    start_time = time.time()
    end_time = start_time + duration_seconds
    
    operations_count = 0
    prime_count = 0
    memory_allocated = 0
    memory_objects = []
    
    logger.info(f"Starting heavy computation (CPU + Memory) for {duration_seconds} seconds")
    logger.info(f"Process ID: {os.getpid()}, Initial memory usage: {psutil.virtual_memory().percent:.1f}%")
    
    # Pre-allocate some initial memory (about 100MB)
    initial_memory = []
    for i in range(10):
        # Create large arrays to consume memory
        large_array = np.random.rand(1000, 1000).astype(np.float64)  # ~8MB each
        initial_memory.append(large_array)
        memory_allocated += large_array.nbytes
    
    logger.info(f"Pre-allocated {memory_allocated / (1024**2):.1f}MB of memory")
    logger.info(f"Memory usage after pre-allocation: {psutil.virtual_memory().percent:.1f}%")
    
    # Log progress every 10 seconds
    last_log_time = start_time
    log_interval = 10.0  # seconds
    
    while time.time() < end_time:
        current_time = time.time()
        
        # Log progress periodically
        if current_time - last_log_time >= log_interval:
            elapsed = current_time - start_time
            remaining = end_time - current_time
            current_memory = psutil.virtual_memory().percent
            logger.info(f"Computation progress: {elapsed:.1f}s elapsed, {remaining:.1f}s remaining, "
                       f"operations: {operations_count}, memory: {current_memory:.1f}%")
            last_log_time = current_time
        
        # Matrix multiplication (CPU intensive)
        matrix_a = np.random.rand(200, 200)  # Increased size for more CPU work
        matrix_b = np.random.rand(200, 200)
        result = np.dot(matrix_a, matrix_b)
        operations_count += 1
        
        # Memory-intensive operations - allocate and manipulate large data structures
        if operations_count % 5 == 0:  # Every 5th operation
            # Create large temporary arrays
            temp_data = []
            for _ in range(5):
                # Create arrays that will stress memory
                temp_array = np.random.rand(500, 500).astype(np.float64)  # ~2MB each
                # Perform operations on the array to ensure it's actually used
                temp_array = temp_array * 2.0 + np.sin(temp_array)
                temp_data.append(temp_array)
                memory_allocated += temp_array.nbytes
            
            # Store some objects to maintain memory pressure
            memory_objects.extend(temp_data[:2])  # Keep 2 arrays, let 3 be garbage collected
            
            # Occasionally clean up old objects to simulate memory churn
            if len(memory_objects) > 50:
                logger.debug(f"Cleaning up memory objects. Current count: {len(memory_objects)}")
                # Remove oldest objects
                removed = memory_objects[:10]
                memory_objects = memory_objects[10:]
                for obj in removed:
                    memory_allocated -= obj.nbytes
                del removed
        
        # Prime number calculation (CPU intensive)
        for num in range(1000, 1200):  # Increased range
            if all(num % i != 0 for i in range(2, int(num**0.5) + 1)):
                prime_count += 1
        
        # String operations (memory intensive)
        if operations_count % 10 == 0:
            # Create and manipulate large strings
            large_string = "x" * 1000000  # 1MB string
            processed_string = large_string.upper().replace("X", "Y")
            # Force string to be processed
            hash_val = hash(processed_string)
            del large_string, processed_string
        
        # Dictionary operations (memory intensive)
        if operations_count % 7 == 0:
            # Create large dictionary
            large_dict = {f"key_{i}": np.random.rand(100) for i in range(1000)}
            # Process dictionary
            sum_values = sum(np.sum(arr) for arr in large_dict.values())
            del large_dict
        
        # Small sleep to prevent complete CPU saturation but allow memory pressure
        time.sleep(0.0005)  # Reduced sleep time
    
    # Clean up memory objects
    total_cleanup = 0
    for obj in memory_objects:
        total_cleanup += obj.nbytes
    for obj in initial_memory:
        total_cleanup += obj.nbytes
    
    del memory_objects, initial_memory
    
    actual_duration = time.time() - start_time
    final_memory_usage = psutil.virtual_memory().percent
    
    result = {
        "duration": actual_duration,
        "operations_count": operations_count,
        "prime_count": prime_count,
        "memory_allocated_mb": memory_allocated / (1024**2),
        "memory_cleaned_mb": total_cleanup / (1024**2),
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": final_memory_usage
    }
    
    logger.info(f"Computation completed: {result}")
    return result


async def run_heavy_computation():
    """
    Runs the heavy computation task using multiprocessing to maximize CPU usage.
    """
    global computation_state
    
    if computation_state["is_running"]:
        logger.warning("Computation already running, skipping this cycle")
        return
    
    computation_state["is_running"] = True
    computation_state["last_run"] = datetime.now().isoformat()
    computation_state["total_runs"] += 1
    
    try:
        # Use all available CPU cores for maximum load
        cpu_count = multiprocessing.cpu_count()
        logger.info(f"Starting computation on {cpu_count} cores")
        
        # Run computation on multiple processes
        with ProcessPoolExecutor(max_workers=cpu_count) as executor:
            # Submit tasks to all CPU cores
            futures = [executor.submit(cpu_intensive_task, 30) for _ in range(cpu_count)]
            
            # Wait for all tasks to complete
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=35)  # 5 seconds buffer
                    results.append(result)
                except Exception as e:
                    logger.error(f"Computation task failed: {e}")
        
        logger.info(f"All computation tasks completed. Results: {len(results)} tasks finished")
        
        # Update memory metrics from results
        if results:
            avg_allocated = sum(r.get("memory_allocated_mb", 0) for r in results) / len(results)
            avg_cleaned = sum(r.get("memory_cleaned_mb", 0) for r in results) / len(results)
            computation_state["last_memory_allocated_mb"] = avg_allocated
            computation_state["last_memory_cleaned_mb"] = avg_cleaned
        
    except Exception as e:
        logger.error(f"Error during computation: {e}")
    finally:
        computation_state["is_running"] = False
        # Schedule next run (5 minutes from now)
        next_run_time = datetime.now().timestamp() + 300  # 5 minutes
        computation_state["next_run"] = datetime.fromtimestamp(next_run_time).isoformat()


async def computation_scheduler():
    """
    Background task that runs heavy computation every 5 minutes.
    """
    logger.info("Starting computation scheduler")
    
    while True:
        try:
            await run_heavy_computation()
            # Wait 5 minutes before next computation
            logger.info("Waiting 5 minutes for next computation cycle")
            await asyncio.sleep(15 * 60)  # 15 minutes = 300 seconds
        except Exception as e:
            logger.error(f"Error in computation scheduler: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying


@app.on_event("startup")
async def startup_event():
    """
    Start the background computation scheduler when the app starts.
    """
    logger.info("Starting workload application")
    # Start the computation scheduler as a background task
    asyncio.create_task(computation_scheduler())


@app.get("/")
async def root():
    """
    Root endpoint providing basic app information.
    """
    return {
        "app": "Workload App",
        "description": "Heavy computation workload for power consumption testing",
        "version": "1.0.0",
        "status": "running"
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
    return ComputationStatus(
        is_running=computation_state["is_running"],
        last_run=computation_state["last_run"],
        next_run=computation_state["next_run"],
        total_runs=computation_state["total_runs"],
        cpu_usage=psutil.cpu_percent(interval=1),
        memory_usage=psutil.virtual_memory().percent,
        cpu_count=multiprocessing.cpu_count(),
        last_memory_allocated_mb=computation_state["last_memory_allocated_mb"],
        last_memory_cleaned_mb=computation_state["last_memory_cleaned_mb"]
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
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)