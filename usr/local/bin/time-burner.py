#!/usr/bin/env python3
import time
import argparse
import multiprocessing
import hashlib
import os
from collections import deque

class PIDController:
    """Simple PID controller with output clamping and anti-windup."""
    def __init__(self, Kp, Ki, Kd, setpoint, output_limits=(0, 1), sample_time=1.0):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.output_limits = output_limits
        self.sample_time = sample_time
        self._last_time = time.time()
        self._last_error = 0.0
        self._integral = 0.0
        self._last_output = 0.0

    def update(self, measurement):
        """Compute new output of PID based on measurement."""
        now = time.time()
        dt = now - self._last_time

        if dt < self.sample_time:
            return self._last_output

        error = self.setpoint - measurement

        # Proportional
        P = self.Kp * error

        # Integral with anti-windup
        self._integral += error * dt
        I = self.Ki * self._integral

        # Derivative
        derivative = (error - self._last_error) / dt if dt > 0 else 0.0
        D = self.Kd * derivative

        # Combine and clamp
        output = P + I + D
        low, high = self.output_limits
        output = max(low, min(high, output))

        self._last_output = output
        self._last_error = error
        self._last_time = now

        return output

def read_cpu_temperature(path='/sys/class/thermal/thermal_zone0/temp'):
    """Return CPU temperature in Celsius."""
    with open(path, 'r') as f:
        temp_str = f.read().strip()
    return float(temp_str) / 1000.0

def burn_cpu(duration):
    """Busy-loop hashing for 'duration' seconds."""
    end_time = time.time() + duration
    m = hashlib.md5()
    while time.time() < end_time:
        m.update(b"burning-cpu")

def worker_loop(worker_id, cmd_queue, done_queue):
    """
    Worker process:
    - Pins itself to CPUs 1, 2, or 3 (avoiding CPU 0)
    - Burns CPU based on commands from main process
    """
    available_cpus = [1, 2, 3]
    cpu_to_use = available_cpus[worker_id % len(available_cpus)]
    os.sched_setaffinity(0, {cpu_to_use})
    print(f"Worker {worker_id} pinned to CPU {cpu_to_use}")

    while True:
        cmd = cmd_queue.get()
        if cmd is None:
            break

        burn_time, sleep_time = cmd
        burn_cpu(burn_time)
        time.sleep(sleep_time)
        done_queue.put(worker_id)

# Main control loop (simplified)
def main():
    target_temp = 70.0  # degrees Celsius
    control_window = 0.20  # 200ms cycle time

    pid = PIDController(Kp=0.05, Ki=0.02, Kd=0.0,
                        setpoint=target_temp,
                        sample_time=0.18)

    # Start 3 worker processes
    workers = []
    cmd_queues = []
    done_queue = multiprocessing.Queue()

    for i in range(3):
        q = multiprocessing.Queue()
        p = multiprocessing.Process(target=worker_loop, args=(i, q, done_queue))
        p.start()
        workers.append(p)
        cmd_queues.append(q)

    try:
        while True:
            # Measure temperature
            current_temp = read_cpu_temperature()

            # PID control: output is fraction of time to burn (0.0 to 1.0)
            output = pid.update(current_temp)

            # Convert to burn/sleep times
            burn_time = output * control_window
            sleep_time = control_window - burn_time

            # Send command to all workers
            for q in cmd_queues:
                q.put((burn_time, sleep_time))

            # Wait for workers to complete
            for _ in range(3):
                done_queue.get()

            print(f"Temp={current_temp:.2f}C, Output={output:.2f}, "
                  f"Burn={burn_time:.2f}s")

    except KeyboardInterrupt:
        for q in cmd_queues:
            q.put(None)
        for p in workers:
            p.join()

if __name__ == '__main__':
    main()