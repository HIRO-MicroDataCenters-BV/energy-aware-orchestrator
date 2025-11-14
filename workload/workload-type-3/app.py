import asyncio
import logging
import multiprocessing
import random
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta
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
            os.path.join(log_dir, 'workload-type-3.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Workload Type-3 App", description="Random burst workload: 20min active, 1hr idle cycle")

# Global state to track computation status
computation_state = {
    "is_running": False,
    "current_phase": "idle",  # "active" or "idle"
    "phase_start_time": None,
    "phase_end_time": None,
    "last_run": None,
    "total_cycles": 0,
    "active_cycles": 0,
    "idle_cycles": 0,
    "last_memory_allocated_mb": 0.0,
    "last_memory_cleaned_mb": 0.0,
    "current_intensity": 0.0  # 0.0 to 1.0 random intensity level
}

# Cycle configuration
ACTIVE_DURATION = 20 * 60  # 20 minutes in seconds
IDLE_DURATION = 60 * 60    # 1 hour in seconds


class ComputationStatus(BaseModel):
    is_running: bool
    current_phase: str
    phase_start_time: str = None
    phase_end_time: str = None
    time_remaining_in_phase: str = None
    last_run: str = None
    total_cycles: int
    active_cycles: int
    idle_cycles: int
    cpu_usage: float
    memory_usage: float
    cpu_count: int
    last_memory_allocated_mb: float = 0.0
    last_memory_cleaned_mb: float = 0.0
    current_intensity: float = 0.0
    next_phase: str = None


def get_phase_info():
    """Get current phase information and time remaining."""
    if not computation_state["phase_start_time"]:
        return None, None, None
    
    now = datetime.now()
    phase_start = datetime.fromisoformat(computation_state["phase_start_time"])
    phase_end = datetime.fromisoformat(computation_state["phase_end_time"])
    
    time_remaining = phase_end - now
    if time_remaining.total_seconds() <= 0:
        return "phase_complete", timedelta(0), None
    
    next_phase = "idle" if computation_state["current_phase"] == "active" else "active"
    return computation_state["current_phase"], time_remaining, next_phase


def random_cpu_memory_task(duration_seconds: int, intensity: float = 1.0) -> Dict[str, Any]:
    """
    Performs random intensity CPU and memory computation.
    Intensity ranges from 0.1 (low) to 1.0 (high).
    """
    start_time = time.time()
    end_time = start_time + duration_seconds
    
    operations_count = 0
    memory_allocated = 0
    memory_objects = []
    
    # Adjust parameters based on intensity
    matrix_size = int(100 + (300 * intensity))  # 100x100 to 400x400
    memory_chunk_size = int(200 + (800 * intensity))  # 200x200 to 1000x1000 arrays
    operation_sleep = 0.001 + (0.01 * (1 - intensity))  # Less sleep = higher intensity
    
    logger.info(f"Starting random computation (intensity: {intensity:.2f}) for {duration_seconds/60:.1f} minutes")
    logger.info(f"Process ID: {os.getpid()}, Matrix size: {matrix_size}x{matrix_size}, "
               f"Memory chunks: {memory_chunk_size}x{memory_chunk_size}")
    
    # Random initial memory allocation based on intensity
    initial_memory_count = int(5 + (15 * intensity))  # 5 to 20 arrays
    initial_memory = []
    for i in range(initial_memory_count):
        array_size = int(500 + random.randint(0, int(500 * intensity)))
        large_array = np.random.rand(array_size, array_size).astype(np.float64)
        initial_memory.append(large_array)
        memory_allocated += large_array.nbytes
    
    logger.info(f"Pre-allocated {memory_allocated / (1024**2):.1f}MB of memory")
    
    # Log progress based on duration
    log_interval = max(60, duration_seconds / 10)  # Log every minute or 1/10th of duration
    last_log_time = start_time
    
    while time.time() < end_time:
        current_time = time.time()
        
        # Log progress periodically
        if current_time - last_log_time >= log_interval:
            elapsed = current_time - start_time
            remaining = end_time - current_time
            current_memory = psutil.virtual_memory().percent
            current_cpu = psutil.cpu_percent(interval=1)
            logger.info(f"Random computation progress: {elapsed/60:.1f}m elapsed, "
                       f"{remaining/60:.1f}m remaining, intensity: {intensity:.2f}, "
                       f"operations: {operations_count}, memory: {current_memory:.1f}%, CPU: {current_cpu:.1f}%")
            last_log_time = current_time
        
        # Random matrix operations with varying complexity
        matrix_ops = random.randint(1, int(3 * intensity) + 1)
        for _ in range(matrix_ops):
            # Variable matrix sizes for randomness
            size_variant = random.randint(int(matrix_size * 0.7), int(matrix_size * 1.3))
            matrix_a = np.random.rand(size_variant, size_variant)
            matrix_b = np.random.rand(size_variant, size_variant)
            
            # Random operation type
            op_type = random.choice(['multiply', 'transpose', 'eigenvals', 'svd'])
            if op_type == 'multiply':
                result = np.dot(matrix_a, matrix_b)
            elif op_type == 'transpose':
                result = matrix_a.T @ matrix_b @ matrix_a
            elif op_type == 'eigenvals' and size_variant <= 200:  # Limit size for eigenvals
                result = np.linalg.eigvals(matrix_a[:100, :100])
            elif op_type == 'svd' and size_variant <= 150:  # Limit size for SVD
                result = np.linalg.svd(matrix_a[:100, :100], full_matrices=False)
            else:
                result = matrix_a + matrix_b
            
            operations_count += 1
        
        # Random memory operations
        if random.random() < intensity:  # Probability based on intensity
            # Create random-sized memory chunks
            chunk_count = random.randint(1, int(5 * intensity) + 1)
            temp_memory = []
            
            for _ in range(chunk_count):
                size_variant = random.randint(int(memory_chunk_size * 0.5), int(memory_chunk_size * 1.5))
                # Random array type and operations
                if random.choice([True, False]):
                    temp_array = np.random.rand(size_variant, size_variant).astype(np.float64)
                    # Random mathematical operations
                    operations = random.choice([
                        lambda x: np.sin(x) * np.cos(x),
                        lambda x: np.sqrt(np.abs(x)),
                        lambda x: x ** 2 + np.log(np.abs(x) + 1),
                        lambda x: np.exp(-x * 0.1)
                    ])
                    temp_array = operations(temp_array)
                else:
                    # Integer arrays for variety
                    temp_array = np.random.randint(0, 1000, (size_variant, size_variant)).astype(np.float64)
                
                temp_memory.append(temp_array)
                memory_allocated += temp_array.nbytes
            
            # Randomly decide how many to keep
            keep_count = random.randint(0, len(temp_memory))
            memory_objects.extend(temp_memory[:keep_count])
            
            # Random cleanup
            if len(memory_objects) > int(30 + (70 * intensity)):  # 30 to 100 objects max
                cleanup_count = random.randint(int(len(memory_objects) * 0.2), int(len(memory_objects) * 0.5))
                removed = memory_objects[:cleanup_count]
                memory_objects = memory_objects[cleanup_count:]
                for obj in removed:
                    memory_allocated -= obj.nbytes
                del removed
        
        # Random CPU-intensive operations
        if random.random() < intensity * 0.7:  # 70% of intensity level
            # Prime number calculations with random range
            start_range = random.randint(1000, 5000)
            end_range = start_range + random.randint(100, int(1000 * intensity))
            prime_count = 0
            
            for num in range(start_range, end_range):
                if all(num % i != 0 for i in range(2, int(num**0.5) + 1)):
                    prime_count += 1
        
        # Random string operations
        if random.random() < intensity * 0.5:  # 50% of intensity level
            string_size = random.randint(int(100000 * intensity), int(1000000 * intensity))
            large_string = "data" * (string_size // 4)
            
            # Random string operations
            operations = random.choice([
                lambda s: s.upper().replace("DATA", "PROC"),
                lambda s: s.lower().replace("data", "info"),
                lambda s: s.replace("a", "X").replace("t", "Y"),
                lambda s: "".join(reversed(s[:len(s)//2]))
            ])
            processed = operations(large_string)
            hash_val = hash(processed)
            del large_string, processed
        
        # Random complex data structures
        if random.random() < intensity * 0.3:  # 30% of intensity level
            dict_size = random.randint(int(100 * intensity), int(2000 * intensity))
            complex_dict = {}
            
            for i in range(dict_size):
                array_size = random.randint(50, int(200 * intensity))
                complex_dict[f"random_key_{i}_{random.randint(1000, 9999)}"] = {
                    "data": np.random.rand(array_size),
                    "metadata": {
                        "timestamp": current_time + random.random(),
                        "values": [random.randint(1, 1000) for _ in range(random.randint(10, 100))],
                        "intensity": intensity,
                        "random_id": random.randint(10000, 99999)
                    }
                }
            
            # Process the dictionary randomly
            sample_size = random.randint(dict_size // 10, dict_size // 2)
            sampled_items = random.sample(list(complex_dict.items()), min(sample_size, len(complex_dict)))
            
            total_sum = 0
            for key, value in sampled_items:
                total_sum += np.sum(value["data"])
                total_sum += sum(value["metadata"]["values"][:random.randint(1, len(value["metadata"]["values"]))])
            
            del complex_dict
        
        # Random sleep based on intensity (higher intensity = less sleep)
        time.sleep(operation_sleep + random.uniform(0, 0.005))
    
    # Cleanup phase
    total_cleanup = 0
    for obj in memory_objects:
        total_cleanup += obj.nbytes
    for obj in initial_memory:
        total_cleanup += obj.nbytes
    
    del memory_objects, initial_memory
    
    actual_duration = time.time() - start_time
    final_memory_usage = psutil.virtual_memory().percent
    final_cpu_usage = psutil.cpu_percent(interval=1)
    
    result = {
        "duration_minutes": actual_duration / 60,
        "intensity": intensity,
        "operations_count": operations_count,
        "memory_allocated_mb": memory_allocated / (1024**2),
        "memory_cleaned_mb": total_cleanup / (1024**2),
        "final_cpu_usage": final_cpu_usage,
        "final_memory_usage": final_memory_usage
    }
    
    logger.info(f"Random computation completed: {result}")
    return result


async def run_active_phase():
    """
    Runs the active phase with random intensity computation.
    """
    global computation_state
    
    if computation_state["is_running"]:
        logger.warning("Computation already running, skipping active phase")
        return
    
    # Generate random intensity for this cycle (0.3 to 1.0 for meaningful load)
    intensity = random.uniform(0.3, 1.0)
    computation_state["current_intensity"] = intensity
    
    computation_state["is_running"] = True
    computation_state["current_phase"] = "active"
    computation_state["phase_start_time"] = datetime.now().isoformat()
    computation_state["phase_end_time"] = (datetime.now() + timedelta(seconds=ACTIVE_DURATION)).isoformat()
    computation_state["last_run"] = datetime.now().isoformat()
    computation_state["total_cycles"] += 1
    computation_state["active_cycles"] += 1
    
    try:
        # Use random number of CPU cores (between 1 and all available)
        cpu_count = multiprocessing.cpu_count()
        worker_count = random.randint(max(1, cpu_count // 2), cpu_count)
        
        logger.info(f"Starting ACTIVE phase with intensity {intensity:.2f} on {worker_count}/{cpu_count} cores for {ACTIVE_DURATION/60:.1f} minutes")
        
        # Run random computation on multiple processes
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            # Submit tasks with varying intensities
            futures = []
            for i in range(worker_count):
                # Each worker gets slightly different intensity for more randomness
                worker_intensity = intensity + random.uniform(-0.1, 0.1)
                worker_intensity = max(0.1, min(1.0, worker_intensity))  # Clamp between 0.1 and 1.0
                futures.append(executor.submit(random_cpu_memory_task, ACTIVE_DURATION, worker_intensity))
            
            # Wait for all tasks to complete
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=ACTIVE_DURATION + 120)  # 2 minute buffer
                    results.append(result)
                except Exception as e:
                    logger.error(f"Random computation task failed: {e}")
        
        logger.info(f"Active phase completed. Results: {len(results)} processes finished")
        
        # Update memory metrics from results
        if results:
            avg_allocated = sum(r.get("memory_allocated_mb", 0) for r in results) / len(results)
            avg_cleaned = sum(r.get("memory_cleaned_mb", 0) for r in results) / len(results)
            computation_state["last_memory_allocated_mb"] = avg_allocated
            computation_state["last_memory_cleaned_mb"] = avg_cleaned
        
    except Exception as e:
        logger.error(f"Error during active phase: {e}")
    finally:
        computation_state["is_running"] = False


async def run_idle_phase():
    """
    Runs the idle phase - minimal activity.
    """
    global computation_state
    
    computation_state["current_phase"] = "idle"
    computation_state["phase_start_time"] = datetime.now().isoformat()
    computation_state["phase_end_time"] = (datetime.now() + timedelta(seconds=IDLE_DURATION)).isoformat()
    computation_state["idle_cycles"] += 1
    computation_state["current_intensity"] = 0.0
    
    logger.info(f"Starting IDLE phase for {IDLE_DURATION/60:.1f} minutes")
    
    # During idle phase, just wait with minimal activity
    await asyncio.sleep(IDLE_DURATION)
    
    logger.info("Idle phase completed")


async def random_cycle_scheduler():
    """
    Background task that alternates between active (20min) and idle (1hr) phases.
    """
    logger.info("Starting random cycle scheduler for workload-type-3")
    
    # Start with idle phase
    await run_idle_phase()
    
    while True:
        try:
            if computation_state["current_phase"] == "idle":
                # Switch to active phase
                await run_active_phase()
            else:
                # Switch to idle phase
                await run_idle_phase()
            
        except Exception as e:
            logger.error(f"Error in random cycle scheduler: {e}")
            # Wait a bit before retrying
            await asyncio.sleep(60)


@app.on_event("startup")
async def startup_event():
    """
    Start the background random cycle scheduler when the app starts.
    """
    logger.info("Starting workload-type-3 application")
    # Start the cycle scheduler as a background task
    asyncio.create_task(random_cycle_scheduler())


@app.get("/")
async def root():
    """
    Root endpoint providing basic app information.
    """
    return {
        "app": "Workload Type-3 App",
        "description": "Random burst workload with alternating active/idle cycles",
        "version": "1.0.0",
        "status": "running",
        "cycle_pattern": {
            "active_duration": f"{ACTIVE_DURATION/60:.0f} minutes",
            "idle_duration": f"{IDLE_DURATION/60:.0f} minutes",
            "total_cycle": f"{(ACTIVE_DURATION + IDLE_DURATION)/60:.0f} minutes"
        },
        "characteristics": [
            "Random intensity levels (0.3-1.0)",
            "Variable CPU core usage",
            "Random matrix and memory operations",
            "Unpredictable resource patterns"
        ]
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
    Get current computation status and cycle information.
    """
    current_phase, time_remaining, next_phase = get_phase_info()
    time_remaining_str = None
    
    if time_remaining and time_remaining.total_seconds() > 0:
        hours, remainder = divmod(int(time_remaining.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            time_remaining_str = f"{hours}h {minutes}m {seconds}s"
        else:
            time_remaining_str = f"{minutes}m {seconds}s"
    
    return ComputationStatus(
        is_running=computation_state["is_running"],
        current_phase=computation_state["current_phase"],
        phase_start_time=computation_state["phase_start_time"],
        phase_end_time=computation_state["phase_end_time"],
        time_remaining_in_phase=time_remaining_str,
        last_run=computation_state["last_run"],
        total_cycles=computation_state["total_cycles"],
        active_cycles=computation_state["active_cycles"],
        idle_cycles=computation_state["idle_cycles"],
        cpu_usage=psutil.cpu_percent(interval=1),
        memory_usage=psutil.virtual_memory().percent,
        cpu_count=multiprocessing.cpu_count(),
        last_memory_allocated_mb=computation_state["last_memory_allocated_mb"],
        last_memory_cleaned_mb=computation_state["last_memory_cleaned_mb"],
        current_intensity=computation_state["current_intensity"],
        next_phase=next_phase
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
        "current_phase": computation_state["current_phase"],
        "is_running": computation_state["is_running"],
        "current_intensity": computation_state["current_intensity"]
    }


@app.post("/trigger-active")
async def trigger_active_phase():
    """
    Manually trigger active phase (for testing).
    """
    if not computation_state["is_running"]:
        asyncio.create_task(run_active_phase())
        return {
            "message": "Active phase triggered", 
            "duration": f"{ACTIVE_DURATION/60:.0f} minutes",
            "note": "This will override the current cycle"
        }
    else:
        return {
            "message": "Computation already running", 
            "current_phase": computation_state["current_phase"],
            "current_intensity": computation_state["current_intensity"]
        }


@app.get("/cycle-info")
async def get_cycle_info():
    """
    Get detailed information about the current cycle pattern.
    """
    current_phase, time_remaining, next_phase = get_phase_info()
    
    return {
        "current_cycle": {
            "phase": computation_state["current_phase"],
            "intensity": computation_state["current_intensity"],
            "start_time": computation_state["phase_start_time"],
            "end_time": computation_state["phase_end_time"],
            "time_remaining": str(time_remaining).split('.')[0] if time_remaining else None
        },
        "cycle_statistics": {
            "total_cycles": computation_state["total_cycles"],
            "active_cycles": computation_state["active_cycles"],
            "idle_cycles": computation_state["idle_cycles"]
        },
        "configuration": {
            "active_duration_minutes": ACTIVE_DURATION / 60,
            "idle_duration_minutes": IDLE_DURATION / 60,
            "total_cycle_minutes": (ACTIVE_DURATION + IDLE_DURATION) / 60
        },
        "next_phase": next_phase
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)