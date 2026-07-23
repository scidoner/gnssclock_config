#!/bin/bash
# PPS NTP Server Performance Optimization Script
# Sets CPU affinity, priorities, and performance governor at boot

set -e

echo "Setting up PPS NTP server performance optimizations..."

# Wait for system to be ready
sleep 5

# Set CPU governor to performance mode
echo "Setting CPU governor to performance..."
cpupower frequency-set -g performance

# Pin PPS interrupt to CPU0 (may fail if already pinned, that's OK)
echo "Configuring PPS interrupt affinity..."
echo 1 > /proc/irq/170/smp_affinity 2>/dev/null || echo "PPS IRQ already configured"

# Wait for chronyd to start
echo "Waiting for chronyd to start..."
timeout=30
while [ $timeout -gt 0 ]; do
    chronyd_pid=$(pgrep chronyd 2>/dev/null || echo "")
    if [ -n "$chronyd_pid" ]; then
        echo "Found chronyd PID: $chronyd_pid"
        break
    fi
    sleep 1
    ((timeout--))
done

if [ -z "$chronyd_pid" ]; then
    echo "Warning: chronyd not found after 30 seconds"
else
    # Set chronyd to real-time priority and pin to CPU 0
    echo "Setting chronyd to real-time priority and pinning to CPU 0..."
    for pid in ${chronyd_pid}; do
        chrt -f -p 50 $pid
        taskset -p 1 $pid
    done
fi

# Boost ksoftirqd/0 priority
echo "Boosting ksoftirqd/0 priority..."
ksoftirqd_pid=$(ps aux | grep '\[ksoftirqd/0\]' | grep -v grep | awk '{print $2}')
if [ -n "$ksoftirqd_pid" ]; then
    renice -n -10 $ksoftirqd_pid
    echo "ksoftirqd/0 priority boosted (PID: $ksoftirqd_pid)"
else
    echo "Warning: ksoftirqd/0 not found"
fi

echo "PPS NTP optimization complete!"

# Log current status
echo "=== Current Status ==="
echo "CPU Governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)"
echo "PPS IRQ Affinity: $(cat /proc/irq/170/effective_affinity_list 2>/dev/null || echo 'not readable')"
if [ -n "$chronyd_pid" ]; then
    for pid in ${chronyd_pid}; do
        echo "chronyd Priority: $(chrt -p $pid)"
    done
fi
echo "======================"