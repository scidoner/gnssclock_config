# Raspberry Pi 5 GPS/PPS Stratum-1 Time Server

This repository builds a dedicated Raspberry Pi 5 NTP server using:

- GNSS time-of-day data from GPSD through `SHM 0`;
- a kernel PPS device on GPIO4;
- Chrony's direct PPS refclock, locked to the `gnss` SHM refclock;
- a boot-time PPS/Chrony optimization service; and
- public-key-only SSH administration.

The repository mirrors the Linux filesystem so each managed file has an obvious deployment destination.

> [!IMPORTANT]
> This is an NTP server, not a PTP grandmaster. PPS can discipline the Pi locally with very low error, but ordinary NTP clients and networks will normally see larger offsets.

## Repository layout

```text
.
├── .gitattributes
├── README.md
├── boot/
│   ├── README.md
│   └── firmware/
│       ├── README.md
│       └── config.txt
├── etc/
│   ├── README.md
│   ├── chrony/
│   │   ├── README.md
│   │   └── chrony.conf
│   ├── default/
│   │   ├── README.md
│   │   └── gpsd
│   ├── ssh/
│   │   ├── README.md
│   │   └── sshd_config
│   └── systemd/
│       ├── README.md
│       └── system/
│           ├── README.md
│           └── pps-optimize.service
└── usr/
    ├── README.md
    └── local/
        ├── README.md
        └── bin/
            ├── README.md
            └── pps-optimize.sh
```

The short READMEs inside mirrored directories are documentation only. Do not copy them into the Pi's system directories.

## Build assumptions

| Item | Configuration |
|---|---|
| Board | Raspberry Pi 5 |
| OS | Raspberry Pi OS Lite 64-bit, Bookworm or later |
| GPS serial device | `/dev/ttyAMA0` |
| GPS serial pins | GPIO15/GPIO14, physical pins 10/8 |
| GPSD time transport | NTP shared memory unit 0 |
| GNSS refid | `gnss` |
| PPS input | GPIO4, physical pin 7 |
| PPS device | `/dev/pps0` |
| PPS refid | `pps` |
| NTP daemon | Chrony |
| Example client network | `192.168.1.0/24`; change before deployment |

Raspberry Pi 5 exposes its default primary UART on the separate debug connector. This build enables UART0 on GPIO14/15 with `uart0-pi5` and uses `/dev/ttyAMA0`; do not substitute `/dev/serial0` without checking where it points.

## Hardware and wiring

Use a GPS/GNSS receiver with supported serial output, a 1 PPS output, and 3.3 V logic on signals connected to the Pi. A suitable antenna with clear sky view is essential.

Power the Pi off before wiring.

| GPS signal | Raspberry Pi 5 connection | Notes |
|---|---|---|
| GND | Physical pin 6, GND | Common ground is mandatory |
| GPS TX | Physical pin 10, GPIO15/RXD0 | GPS transmits to Pi receive |
| GPS RX | Physical pin 8, GPIO14/TXD0 | Optional unless configuring the receiver |
| PPS | Physical pin 7, GPIO4 | BCM GPIO number 4 |
| VIN/VCC | Module-specific | Use 5 V only if the breakout explicitly accepts it |

> [!CAUTION]
> Raspberry Pi GPIO is 3.3 V only and is not 5 V tolerant. Verify the receiver data sheet before connecting power, UART, or PPS.

## 1. Record the OS image

Install a specific Raspberry Pi OS Lite 64-bit image. In Raspberry Pi Imager, preconfigure:

- a unique hostname, such as `rpi5-time01`;
- an administrative user and SSH public key;
- wired networking with a DHCP reservation; and
- UTC or the required local timezone.

Record the exact image filename, release date, download URL, and SHA-256 checksum. Reusing only the label “latest” is not a repeatable build.

After first boot:

```bash
hostnamectl
cat /etc/os-release
uname -a
```

## 2. Remove the desktop and install packages

Run the purge over SSH only after confirming the Pi does not need a graphical desktop:

```bash
sudo apt-get purge -y \
  raspberrypi-ui-mods \
  lightdm \
  'xserver-xorg*' \
  wayfire \
  labwc \
  'chromium*' \
  firefox

sudo apt-get autoremove -y --purge
sudo apt-get update
sudo apt-get upgrade -y

sudo apt-get install -y \
  pps-tools \
  gpsd \
  gpsd-clients \
  chrony \
  git \
  lldpd \
  openssh-server \
  procps \
  zsh \
  linux-cpupower \
  python3 \
  util-linux \
  unattended-upgrades \
  zabbix-agent2
```

If `zabbix-agent2` is unavailable, omit it from this transaction and install it later from a separately documented, pinned Zabbix repository.

```bash
sudo systemctl enable --now lldpd
sudo systemctl enable --now unattended-upgrades
```

`unattended-upgrades` improves security but changes package state over time. Use a dated APT snapshot or a validated disk image when exact package reproduction is required.

## 3. Prepare the configuration

Commands below assume this repository is checked out on the Pi and the shell is at its root:

```bash
cd gnssclock_config
```

Before installation:

1. Change `allow 192.168.1.0/24` in `etc/chrony/chrony.conf` to the real client subnet.
2. Confirm the administrative user's public key is present in `~/.ssh/authorized_keys`.
3. Keep the current SSH session open until a second public-key-only session has been tested.
4. Review every managed file and commit local site changes to Git.

The repository's `config.txt` enables UART0 directly. On Raspberry Pi 5 the default serial console is on the separate debug UART, but verify that `/proc/cmdline` does not assign a console to `ttyAMA0` before connecting GPS data.

## 4. Back up and deploy the mirrored files

Create a dated backup:

```bash
backup_dir="/root/rpi5-time-backup-$(date -u +%Y%m%dT%H%M%SZ)"
sudo mkdir -p \
  "${backup_dir}/boot/firmware" \
  "${backup_dir}/etc/chrony" \
  "${backup_dir}/etc/default" \
  "${backup_dir}/etc/ssh" \
  "${backup_dir}/etc/systemd/system"

sudo cp -a /boot/firmware/config.txt "${backup_dir}/boot/firmware/"
sudo cp -a /etc/chrony/chrony.conf "${backup_dir}/etc/chrony/"
sudo cp -a /etc/default/gpsd "${backup_dir}/etc/default/"
sudo cp -a /etc/ssh/sshd_config "${backup_dir}/etc/ssh/"
```

Validate the repository SSH configuration before installing it:

```bash
sudo /usr/sbin/sshd -t -f "$PWD/etc/ssh/sshd_config"
```

Install only the managed files:

```bash
sudo install -D -m 0644 boot/firmware/config.txt \
  /boot/firmware/config.txt
sudo install -D -m 0644 etc/chrony/chrony.conf \
  /etc/chrony/chrony.conf
sudo install -D -m 0644 etc/default/gpsd \
  /etc/default/gpsd
sudo install -D -m 0600 etc/ssh/sshd_config \
  /etc/ssh/sshd_config
sudo install -D -m 0755 usr/local/bin/pps-optimize.sh \
  /usr/local/bin/pps-optimize.sh
sudo install -D -m 0644 etc/systemd/system/pps-optimize.service \
  /etc/systemd/system/pps-optimize.service
sudo install -D -m 0755 usr/local/bin/time-burner.py \
  /usr/local/bin/time-burner.py
sudo install -D -m 0644 etc/systemd/system/time-burner.service \
  /etc/systemd/system/time-burner.service  
```

Validate the installed daemon configurations:

```bash
sudo /usr/sbin/sshd -t
sudo chronyd -p -f /etc/chrony/chrony.conf
```

If either command reports an error, restore its backup before restarting the affected service.

Reload services and enable them for boot:

```bash
sudo systemctl daemon-reload
sudo systemctl enable gpsd.service
sudo systemctl enable chrony.service
sudo systemctl enable pps-optimize.service
sudo systemctl enable time-burner.service
sudo systemctl reload ssh
```

Open a second terminal and verify public-key SSH login now. Password login is disabled, root login is disabled, and SSH forwarding is disabled by the supplied `sshd_config`.

Reboot to activate UART0 and the GPIO4 PPS overlay:

```bash
sudo reboot
```

## 5. Verify GPS and PPS

After reconnecting:

```bash
ls -l /dev/ttyAMA0 /dev/pps0
lsmod | grep pps
systemctl --no-pager --full status gpsd.service chrony.service
```

Check PPS assertions:

```bash
sudo ppstest /dev/pps0
```

The sequence number should increment once per second. Press `Ctrl+C` after several assertions.

Check GPSD:

```bash
gpspipe -w -n 5
cgps -s
```

`cgps` should eventually show a valid fix, satellites in use, and current UTC time. Many receivers do not emit valid PPS until they have a fix.

## 6. Chrony refclocks

The repository installs these authoritative refclock lines:

```conf
refclock SHM 0 refid gnss offset 0.0 precision 1e-3 poll 0 filter 3 noselect
refclock PPS /dev/pps0 refid pps lock gnss offset 0.0 poll 3 prefer trust
```

GPSD reads only `/dev/ttyAMA0` and publishes serial time-of-day samples to `SHM 0`. Chrony opens `/dev/pps0` directly. `lock gnss` associates each precision pulse with the correct UTC second supplied by the `gnss` refclock.

The GNSS serial source is `noselect` because UART transport latency varies; it labels PPS rather than steering the clock. If the receiver has unusually high serial latency and PPS samples fail the lock test, measure that receiver's GNSS offset and update the `offset` value instead of copying another module's calibration.

> [!IMPORTANT]
> After an hour, run the `analyze.py` tool on the chrony statistics log, to determine the offset for the GNSS reference.

## 7. PPS optimization service and time-burner service

The included `pps-optimize.sh`, `pps-optimize.service`, `time-burner.py` and `time-burner.service` implement the optimization approach from the linked Austin's Nerdy Things thermal-management article:

- set the CPU frequency governor to `performance`;
- find the actual `pps_gpio` interrupt instead of assuming IRQ 200;
- pin that PPS interrupt to CPU0;
- give every returned `chronyd` PID `SCHED_FIFO` priority 50;
- pin every returned `chronyd` PID to CPU0;
- set `ksoftirqd/0` to nice value `-10`; and
- try to maintain a target CPU temperature of 54C but less than 80C.

The PPS optimize unit runs after `chrony.service`.

Verify it:

```bash
systemctl --no-pager --full status pps-optimize.service
systemctl --no-pager --full status time-burner.service
journalctl -u pps-optimize.service -b --no-pager
journalctl -u time-burner.service -b --no-pager
cpupower frequency-info
ps -eo pid,comm,psr,ni,rtprio | grep chronyd
```

Expected results include the `performance` governor, Chrony on processor 0, and real-time priority 50.

If Chrony is manually restarted, reapply the process-specific settings:

```bash
sudo systemctl restart pps-optimize.service
sudo systemctl restart time-burner.service
```

> [!WARNING]
> Real-time scheduling and the performance governor increase operational risk, power use, and heat. Use this only on a dedicated appliance with suitable cooling. Monitor `vcgencmd get_throttled` and disable the service if the system becomes unstable.

## 8. Validate synchronization and NTP service

Allow several minutes after a cold GPS start:

```bash
chronyc tracking
chronyc sources -v
chronyc sourcestats -v
ipcs -m
sudo ss -lunp | grep ':123 '
```

A healthy `chronyc sources -v` normally shows:

- `#* pps` as the selected local PPS refclock;
- `gnss` present but not selected, by design;
- reach increasing to `377`; and
- network sources available for sanity checking and holdover.

Wait for synchronization with an estimated remaining correction below 100 microseconds:

```bash
chronyc waitsync 60 0.0001
```

On a Chrony client, add the Pi's fixed address:

```conf
server 192.168.1.10 iburst prefer
```

Restart that client's Chrony service and confirm the Pi appears as a reachable source:

```bash
sudo systemctl restart chrony
chronyc -n sources -v
```

If a host firewall is enabled on the Pi, allow inbound UDP port 123 only from the configured client subnet.

## 9. Capture a build manifest

```bash
manifest_dir="$HOME/time-server-build-manifest"
mkdir -p "${manifest_dir}"

cat /etc/os-release >"${manifest_dir}/os-release.txt"
uname -a >"${manifest_dir}/uname.txt"
apt-mark showmanual >"${manifest_dir}/apt-manual.txt"
dpkg-query -W -f='${binary:Package}\t${Version}\n' \
  >"${manifest_dir}/packages.tsv"
chronyc tracking >"${manifest_dir}/chrony-tracking.txt"
chronyc sources -v >"${manifest_dir}/chrony-sources.txt"
systemctl status pps-optimize.service --no-pager \
  >"${manifest_dir}/pps-optimize-status.txt"

find boot etc usr -type f ! -name README.md -print0 |
  sort -z |
  xargs -0 sha256sum >"${manifest_dir}/repository-files.sha256"
```

Commit the final configuration and manifest metadata to the build repository. Do not commit private SSH keys, host keys, passwords, tokens, or monitoring secrets.

## Monitoring

Alert on:

- `gpsd`, `chrony`, or `pps-optimize` not active;
- GPS fix or PPS loss;
- `pps` no longer selected by Chrony;
- increasing RMS offset, skew, or root dispersion;
- reach below `377` for an extended period;
- CPU throttling, excessive temperature, or governor changes;
- UDP/123 no longer listening; and
- unexpected package or configuration changes.

Useful checks:

```bash
systemctl is-active gpsd chrony pps-optimize
chronyc tracking
chronyc sources -v
journalctl -u gpsd -u chrony -u pps-optimize --since today
vcgencmd measure_temp
vcgencmd get_throttled
```

Configure `zabbix-agent2` separately with the monitoring server address, TLS policy, and site-specific checks.

## Troubleshooting

### `/dev/pps0` does not exist

1. Confirm `/boot/firmware/config.txt` contains `dtoverlay=pps-gpio,gpiopin=4`.
2. Confirm GPIO4 is physical pin 7.
3. Check `dmesg | grep -i pps` and `lsmod | grep pps`.
4. Confirm receiver PPS voltage, common ground, and GPS fix.
5. Inspect available overlay polarity options with `dtoverlay -h pps-gpio`.

### `/dev/ttyAMA0` or NMEA is absent

1. Confirm `dtoverlay=uart0-pi5` is active.
2. Confirm GPS TX connects to Pi RX on physical pin 10.
3. Confirm the serial console is disabled.
4. Check receiver baud rate and protocol.
5. Inspect `journalctl -u gpsd -b`.

To inspect raw NMEA, temporarily stop GPSD:

```bash
sudo systemctl stop gpsd.service gpsd.socket
sudo timeout 10 cat /dev/ttyAMA0
sudo systemctl start gpsd.socket gpsd.service
```

### `gnss` is absent from Chrony

```bash
sudo systemctl restart gpsd
sudo systemctl restart chrony
ipcs -m
chronyc sources -v
journalctl -u chrony -u gpsd -b --no-pager
```

Confirm GPSD is running with `-n`, has a valid fix, and receives time-of-day data from `/dev/ttyAMA0`. GPSD publishes this to shared memory unit 0, matching `refclock SHM 0`.

### PPS is visible but not selected

- Confirm `gnss` is visible in `chronyc sources -v`.
- Confirm `ppstest /dev/pps0` receives one pulse per second.
- Confirm the PPS directive contains `refid pps lock gnss`.
- Keep multiple network sources available during commissioning.
- Check `chronyc sources -v`, `chronyc sourcestats -v`, and service logs.

### `pps-optimize.service` fails

```bash
journalctl -u pps-optimize.service -b --no-pager
grep -i pps /proc/interrupts
pgrep -a chronyd
cpupower frequency-info
```

The script intentionally fails if it cannot set the performance governor or find Chrony. A missing PPS IRQ produces a warning and leaves IRQ affinity unchanged.

### SSH reload fails

Do not close the working session.

```bash
sudo /usr/sbin/sshd -t
sudo cp -a \
  /root/rpi5-time-backup-YYYYMMDDTHHMMSSZ/etc/ssh/sshd_config \
  /etc/ssh/sshd_config
sudo /usr/sbin/sshd -t
sudo systemctl reload ssh
```

Replace the timestamped example with the exact intended backup directory.

## Security and operational notes

- Restrict Chrony's `allow` directive to trusted subnets.
- The supplied SSH configuration permits public-key authentication only.
- Never deploy the SSH configuration until a working administrative public key is confirmed.
- The supplied SSH policy disables agent, TCP, X11, and tunnel forwarding.
- Prefer wired Ethernet and a fixed DHCP reservation.
- Test upgrades and configuration changes on a spare unit or disk image.
- GPS supplies accurate but unauthenticated time. Monitor independent network sources for receiver, antenna, spoofing, or configuration faults.

## References

- Austin's Nerdy Things, [Revisiting Microsecond Accurate NTP for Raspberry Pi with GPS PPS in 2025](https://austinsnerdythings.com/2025/02/14/revisiting-microsecond-accurate-ntp-for-raspberry-pi-with-gps-pps-in-2025/)
- Austin's Nerdy Things, [World's Most Stable Raspberry Pi? 81% Better NTP with Thermal Management](https://austinsnerdythings.com/2025/11/24/worlds-most-stable-raspberry-pi-81-better-ntp-with-thermal-management/)
- Raspberry Pi, [UART configuration documentation](https://www.raspberrypi.com/documentation/configuration/computers/raspberry-pi.html#configure-uarts)
- Chrony, [`chrony.conf` reference](https://chrony-project.org/doc/4.6/chrony.conf.html)
- GPSD, [Time Service HOWTO](https://gpsd.gitlab.io/gpsd/gpsd-time-service-howto.html)
- Linux kernel, [PPS API documentation](https://www.kernel.org/doc/html/latest/driver-api/pps.html)
- OpenSSH, [`sshd_config` manual](https://man.openbsd.org/sshd_config)

## Acceptance checklist

- [ ] Exact OS image and checksum recorded
- [ ] GPS wiring checked against the receiver data sheet
- [ ] Site subnet committed to `chrony.conf`
- [ ] Administrative public key tested before password authentication is disabled
- [ ] `/dev/ttyAMA0` and `/dev/pps0` exist
- [ ] `ppstest` receives one assertion per second
- [ ] `cgps` shows a valid fix and UTC time
- [ ] `chronyc sources -v` shows `gnss` and selects `#* pps`
- [ ] `pps-optimize.service` is active and Chrony has RT priority 50 on CPU0
- [ ] Chrony listens on UDP/123
- [ ] A client on the allowed subnet synchronizes to the Pi
- [ ] Build manifest captured
- [ ] Monitoring and backup restoration tested
