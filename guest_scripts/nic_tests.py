#!/usr/bin/python

#*****Built-in modules*****#


#*****User defined modules*****#
import peer_utils


#Argument is a instance of class virtual_machine
def execute_tests(peer): 
	test_logs=open("%s/%s_nic_sanity_logs.txt" %(peer.logs_path, peer.ipaddress),"w")
	conn = peer_utils.connect_ssh(peer.ipaddress, peer.user, peer.passwd)
#Test case 1: Load NIC driver
	if (not peer_utils.check_driver(conn)):
		print "\nUnload driver and load again ?"
		(status, msg) = peer_utils.unload_driver(peer.num_ports)
		if (status == 0):
			print msg
		else:
			print msg
			return
	else:
		print "Load NIC driver now"
		(status, msg) = peer_utils.load_nic_driver(conn, peer.driv_path, peer.driv_ver)
		if (status == 0):
			print msg
			#TODO: Log test case status
		else:
			print msg
			return
#Test case 2: Verify iface
	if_list = peer_utils.get_iface_list(conn)
	(status, msg) = peer_utils.verify_iface(if_list, peer.num_ports)
	if (status == 0):
		print msg
		#TODO: Log test case status
	else:
		print msg
		return
#Test case 3: Check link
	(status, msg) = peer_utils.check_link(conn, if_list, peer.num_ports)
	if (status == 0):
		print msg
		#TODO: Log test case status
	else:
		print msg
		return
#Test case 4: Ping peer
	#Configure unicast IP address on the interfaces
	if (not peer_utils.config_iface(conn, if_list, peer.ip_list)):
		(status, msg) = peer_utils.ping_test(conn, peer.peer_list, peer.num_ports, 0)
	if (status == 0):
		print msg
		#TODO: Log test case status
	else:
		print msg
		return
#Test case 5: Iperf test
	(status, msg) = peer_utils.iperf_test(conn, peer.peer_list, peer.num_ports)
	if (status == 0):
		print msg
		#TODO: Log test case status
	else:
		print msg
		return
#Test case 6: Configure VLAN
	(status, msg) = peer_utils.config_vlan(conn, if_list, peer.vlan_list, peer.vlan_ip_list)
#Test case 7: VLAN Ping
	(status, msg) = peer_utils.ping_test(conn, peer.vlan_peer_list, peer.num_ports, 0)
	if (status == 0):
		print msg
		#TODO: Log test case status
	else:
		print msg
		return
#Test case 8: Iperf over VLAN
	(status, msg) = peer_utils.iperf_test(conn, peer.vlan_peer_list, peer.num_ports)
	if (status == 0):
		print msg
		#TODO: Log test case status
	else:
		print msg
		return
#Test case 9: Remove VLAN
	(status, msg) = peer_utils.remove_vlan(conn, if_list, peer.vlan_list)
	if (status == 0):
		print msg
		#TODO: Log test case status
	else:
		print msg
		return
#Test case 10: Change MTU size & #Test case 11: Jumbo Ping
	#First Configure unicast IP address on the interfaces
	if (not peer_utils.config_iface(conn, if_list, peer.ip_list)):
		for mtu in peer.mtu_list:
			for iface in if_list:
				(status, msg) = peer_utils.change_mtu(conn, iface, mtu)
				if (status == 0):
					print msg
					pass
				else:
					print msg
					return
			(status, msg) = peer_utils.ping_test(conn, peer.peer_list, peer.num_ports, mtu)
			if (status == 0):
				print msg
				#TODO: Log test case status
			else:
				print msg
				return
#Test case 14: Unload Driver
	if (not peer_utils.check_driver(conn)):
		(status, msg) = peer_utils.unload_driver(peer.num_ports)
		if (status == 0):
			print msg
		else:
			print msg
			return

# MOVE the following tests to a different file
#Test case 12: VF to VF Ping 
#Test case 13: VF to PF Ping



if __name__ == "__main__":
	print "Starting NIC sanity tests"
	execute_tests(obj)
