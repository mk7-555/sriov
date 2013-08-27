#!/usr/bin/python

__author__ = "Madhu Kesavan"
__email__  = "madhusudhanan.kesavan@emulex.com"

import peer_conf
from time import ctime

"""
Configuration parameters for Virtual Machine 1
Modify parameters marked with +++ per test
TODO: Istead of providing IP addresses for peer here why not login to peer and find out dynamically ?
"""

ipaddress	= "192.168.100.10"
user		= "root"
passwd		= "4Emulex"
driv_path	= "/root/evt/drivers/"
'+++ driv_ver: per test variable'
driv_ver	= "10.0.615.0"
logs_file	= "/root/evt/atm/logs/%s_Nic_test_logs_%s.txt" %(ipaddress, ctime().replace(" ","_"))
'+++ num_ports: per test vairable'
num_ports	= 4
mtu_list	= ["2200", "4088", "8222", "9000"]

if (num_ports==1):
	ip_list		= ["194.24.15.15"]
	peer_list	= peer_conf.peer_list_1port
	vlan_list	= ["202"]
	vlan_ip_list	= ["194.24.16.15"]
	vlan_peer_list	= peer_conf.vlan_peer_1port
	vm_peer_list	= ["194.24.15.20"]
	pf_ip_list	= ["194.24.15.10"]
if (num_ports==2):
	ip_list		= ["194.24.8.15", "194.24.9.15"]
	peer_list	= peer_conf.peer_list_2port
	vlan_list	= ["201", "203"]
	vlan_ip_list	= ["194.24.19.15", "194.24.20.15"]
	vlan_peer_list	= peer_conf.vlan_peer_2port
	vm_peer_list	= ["194.24.8.20", "194.24.9.20"]
	pf_ip_list	= ["194.24.8.10", "194.24.9.10"]
if (num_ports==4):
	ip_list		= ["194.24.8.15", "194.24.9.15", "194.24.6.15", "194.24.7.15"]
	peer_list	= peer_conf.peer_list_4port
	vlan_list	= ["201", "203", "208", "210"]
	vlan_ip_list	= ["194.24.19.15", "194.24.20.15", "194.24.14.15", "194.24.15.15"]
	vlan_peer_list	= peer_conf.vlan_peer_1port
	vm_peer_list	= ["194.24.8.20", "194.24.9.20", "194.24.6.20", "194.24.7.20"]
	pf_ip_list	= ["194.24.8.10", "194.24.9.10", "194.24.6.10", "194.24.7.10"]

nic_tests = ["load_driver", "verify_iface", "check_link", "ping_peer", "iperf_test", "config_vlan", "vlan_ping", "vlan_iperf", "remove_vlan", "change_mtu", "jumbo_ping", "vf_to_vf_ping", "vf_to_pf_ping", "unload_driver"]
