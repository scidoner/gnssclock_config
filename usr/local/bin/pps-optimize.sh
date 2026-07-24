#!/usr/bin/env bash
# Apply low-jitter CPU, IRQ, and scheduler settings for the PPS time service.

set -euo pipefail

log() {
    printf 'pps-optimize: %s\n' "$*"
}

log "setting CPU frequency governor to performance"
cpupower frequency-set --governor performance

pps_irq="$(
    awk '
        tolower($0) ~ /pps/ {
            irq = $1
            sub(/:$/, "", irq)
            if (irq ~ /^[0-9]+$/) {
                print irq
                exit
            }
        }
    ' /proc/interrupts
)"

if [[ -n "${pps_irq}" && -w "/proc/irq/${pps_irq}/smp_affinity_list" ]]; then
    log "pinning PPS IRQ ${pps_irq} to CPU 0"
    if ! printf '0\n' >"/proc/irq/${pps_irq}/smp_affinity_list"; then
        log "warning: kernel rejected PPS IRQ affinity change"
    fi
else
    log "warning: PPS GPIO IRQ was not found; leaving IRQ affinity unchanged"
fi

chronyd_pids=""
for _attempt in $(seq 1 30); do
    chronyd_pids="$(pgrep -x chronyd || true)"
    [[ -n "${chronyd_pids}" ]] && break
    sleep 1
done

if [[ -z "${chronyd_pids}" ]]; then
    log "error: chronyd was not found after 30 seconds"
    exit 1
fi

for chronyd_pid in ${chronyd_pids}; do
    log "assigning chronyd PID ${chronyd_pid} to CPU 0 with SCHED_FIFO priority 50"
    chrt --fifo --pid 50 "${chronyd_pid}"
    taskset --cpu-list --pid 0 "${chronyd_pid}"
done

ksoftirqd_pid="$(pgrep -xo 'ksoftirqd/0' || true)"
if [[ -n "${ksoftirqd_pid}" ]]; then
    log "setting ksoftirqd/0 PID ${ksoftirqd_pid} nice value to -10"
    renice -n -10 -p "${ksoftirqd_pid}"
else
    log "warning: ksoftirqd/0 was not found"
fi

log "CPU governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)"
if [[ -n "${pps_irq}" && -r "/proc/irq/${pps_irq}/effective_affinity_list" ]]; then
    log "PPS IRQ affinity: $(cat "/proc/irq/${pps_irq}/effective_affinity_list")"
fi
for chronyd_pid in ${chronyd_pids}; do
    log "chronyd PID ${chronyd_pid} scheduler: $(chrt --pid "${chronyd_pid}" | tr '\n' '; ')"
done
log "optimization complete"
