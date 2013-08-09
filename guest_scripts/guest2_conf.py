#!/usr/bin/python

vm_ip="192.168.100.11"
vm_user="root"
vm_passwd="4Emulex"

driv_path="/root/evt/drivers"
logs_path="/root/evt/atm/logs"
vm_logs="/root/evt/atm/logs/vm_logs"

vm_ip_1port = ["194.24.15.20"]
vm_ip_2port = ["194.24.8.20", "194.24.9.20"]
vm_ip_4port = ["194.24.8.20", "194.24.9.20", "194.24.6.20", "194.24.7.20"]

vlan_list_1port = ["202"]
vlan_list_2port = ["201", "203"]
vlan_list_4port = ["201", "203", "205", "207"]

vm_vlanip_1port = ["194.24.16.20"]
vm_vlanip_2port = ["194.24.19.20", "194.24.20.20"]
vm_vlanip_4port = ["194.24.11.20", "194.24.12.20", "194.24.13.20", "194.24.14.20"]

mtu_list = ["2200", "4088", "8222", "9000"]

#Test cases list run on Guest 2
nic_tests = ["load_driver", "verify_iface", "check_link", "ping_peer", "iperf_test", "config_vlan", "vlan_ping", "vlan_iperf", "remove_vlan", "change_mtu", "jumbo_ping", "vf_to_vf_ping", "vf_to_pf_ping", "unload_driver"]
