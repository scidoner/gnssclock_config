#/bin/bash
sudo install -D -m 0644 boot/firmware/config.txt /boot/firmware/config.txt
sudo install -D -m 0644 etc/chrony/chrony.conf /etc/chrony/chrony.conf
sudo install -D -m 0644 etc/default/gpsd /etc/default/gpsd
sudo install -D -m 0600 etc/ssh/sshd_config /etc/ssh/sshd_config
sudo install -D -m 0755 usr/local/bin/pps-optimize.sh /usr/local/bin/pps-optimize.sh
sudo install -D -m 0644 etc/systemd/system/pps-optimize.service /etc/systemd/system/pps-optimize.service
sudo install -D -m 0755 usr/local/bin/time-burner.py /usr/local/bin/time-burner.py
sudo install -D -m 0644 etc/systemd/system/time-burner.service /etc/systemd/system/time-burner.service  
