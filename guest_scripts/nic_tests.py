#!/usr/bin/python

"""
nic_tests.py: Wrapper file that runs NIC tests from peer_utils.py
"""

__author__ = "Madhu Kesavan"
__email__  = "madhusudhanan.kesavan@emulex.com"

#*****Python native modules*****#

#*****User defined modules*****#
import peer_utils


#@peer: is an instance of class virtual_machine from load_driv.py
#@results: is an instance of class Results from log_utils.py
def execute_tests(peer, results): 
	conn = peer_utils.connect_ssh(peer.ipaddress, peer.user, peer.passwd)

#Test case 1: Load NIC driver
	if (not peer_utils.check_driver(conn)):
		print "\nUnload driver and load again ?"
		(status, msg) = peer_utils.unload_driver(conn, peer.num_ports)
		results.record_test_data("unload_driver", None, "INFO", msg)
		if (status == 0):
			results.record_test_data("unload_driver", "PASS", "INFO", msg)
		else:
			results.record_test_data("unload_driver", "FAIL", "ABORT", msg)
			return
		print "Load NIC driver now"
		(status, msg) = peer_utils.load_nic_driver(conn, peer.driv_path, peer.driv_ver)
		if (status == 0):
			results.record_test_data("load_driver", "PASS", "INFO", msg)
		else:
			results.record_test_data("load_driver", "FAIL", "ABORT", msg)
			return
	else:
		print "Load NIC driver now"
		(status, msg) = peer_utils.load_nic_driver(conn, peer.driv_path, peer.driv_ver)
		if (status == 0):
			results.record_test_data("load_driver", "PASS", "INFO", msg)
		else:
			results.record_test_data("load_driver", "FAIL", "ABORT", msg)
			return

#Test case 2: Verify iface
	if_list = peer_utils.get_iface_list(conn)
	(status, msg) = peer_utils.verify_iface(if_list, peer.num_ports)
	if (status == 0):
		results.record_test_data("verify_iface", "PASS", "INFO", msg)
	else:
		results.record_test_data("verify_iface", "FAIL", "ABORT", msg)
		return

#Test case 3: Check link
	(status, msg) = peer_utils.check_link(conn, if_list, peer.num_ports)
	if (status == 0):
		results.record_test_data("check_link", "PASS", "INFO", msg)
	else:
		results.record_test_data("check_link", "FAIL", "ABORT", msg)
		return

#Test case 4: Ping peer
	#Configure unicast IP address on the interfaces
	if (not peer_utils.config_iface(conn, if_list, peer.ip_list)):
		(status, msg) = peer_utils.ping_test(conn, peer.peer_list, peer.num_ports, 0)
	if (status == 0):
		results.record_test_data("ping_peer", "PASS", "INFO", msg)
	else:
		results.record_test_data("ping_peer", "FAIL", "ABORT", msg)
		return

#Test case 5: Iperf test
	(status, msg) = peer_utils.iperf_test(conn, peer.peer_list, peer.num_ports)
	if (status == 0):
		results.record_test_data("iperf_test", "PASS", "INFO", msg)
	else:
		results.record_test_data("iperf_test", "FAIL", "WARN", msg)
		#return --- We probably want to continue running other tests

#Test case 6: Configure VLAN
	(status, msg) = peer_utils.config_vlan(conn, if_list, peer.vlan_list, peer.vlan_ip_list)
	if (status == 0):
		results.record_test_data("config_vlan", "PASS", "INFO", msg)
	else:
		results.record_test_data("config_vlan", "FAIL", "WARN", msg)
		#return --- We probably want to continue running other tests

#Test case 7: VLAN Ping
	(status, msg) = peer_utils.ping_test(conn, peer.vlan_peer_list, peer.num_ports, 0)
	if (status == 0):
		results.record_test_data("vlan_ping", "PASS", "INFO", msg)
	else:
		results.record_test_data("vlan_ping", "FAIL", "WARN", msg)
		#return --- We probably want to continue running other tests

#Test case 8: Iperf over VLAN
	(status, msg) = peer_utils.iperf_test(conn, peer.vlan_peer_list, peer.num_ports)
	if (status == 0):
		results.record_test_data("vlan_iperf", "PASS", "INFO", msg)
	else:
		results.record_test_data("vlan_iperf", "FAIL", "WARN", msg)
		#return --- We probably want to continue running other tests

#Test case 9: Remove VLAN
	(status, msg) = peer_utils.remove_vlan(conn, if_list, peer.vlan_list)
	if (status == 0):
		results.record_test_data("remove_vlan", "PASS", "INFO", msg)
	else:
		results.record_test_data("remove_vlan", "FAIL", "WARN", msg)
		return

#Test case 10: Change MTU size & Test case 11: Jumbo Ping
	#First Configure unicast IP address on the interfaces
	if (not peer_utils.config_iface(conn, if_list, peer.ip_list)):
		for mtu in peer.mtu_list:
			for iface in if_list:
				(status, msg) = peer_utils.change_mtu(conn, iface, mtu)
				if (status == 0):
					results.record_test_data("change_mtu", "PASS", "INFO", msg)
					pass
				else:
					results.record_test_data("change_mtu", "FAIL", "ABORT", msg)
					return
			(status, msg) = peer_utils.ping_test(conn, peer.peer_list, peer.num_ports, mtu)
			if (status == 0):
				results.record_test_data("jumbo_ping", "PASS", "INFO", msg)
			else:
				results.record_test_data("jumbo_ping", "FAIL", "ABORT", msg)
				#return--- We probably want to continue running other tests

#Test case 12: VF to VF Ping
	(status, msg) = peer_utils.ping_test(conn, peer.vm_peer_list, peer.num_ports)
	if (status == 0):
		results.record_test_data("vf_to_vf_ping", "PASS", "INFO", msg)
	else:
		results.record_test_data("vf_to_vf_ping", "FAIL", "WARN", msg)

#Test case 13: VF to PF Ping
	(status, msg) = peer_utils.ping_test(conn, peer.pf_ip_list, peer.num_ports)
	if (status == 0):
		results.record_test_data("vf_to_pf_ping", "PASS", "INFO", msg)
	else:
		results.record_test_data("vf_to_pf_ping", "FAIL", "WARN", msg)

#Test case 14: Unload Driver
	if (not peer_utils.check_driver(conn)):
		(status, msg) = peer_utils.unload_driver(conn, peer.num_ports)
		if (status == 0):
			results.record_test_data("unload_driver", "PASS", "INFO", msg)
		else:
			results.record_test_data("unload_driver", "FAIL", "ABORT", msg)
			return

	#Closing SSH connection to the VM
	conn.close()

#TODO: Modify "main" such that this module can be run as a standalone for NIC tests
if __name__ == "__main__":
	print "Starting NIC sanity tests"
	execute_tests(sut, results)
