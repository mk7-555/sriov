#!/usr/bin/python

import paramiko
import re
import time


def connect_ssh(ip, usr, pwd):
	print "Connecting Linux Peer @ %s" %ip
	try:
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		ssh.connect(ip,username=usr,password=pwd)
		return ssh
	except:
		print "\n****** Could not connect to Peer @ %s!!! ******" %ip

def check_driver(conn):
	print "Checking if driver is already loaded"
	stdin, stdout, stderr = conn.exec_command("lsmod | grep -i be2net")
	lsmod_out = stdout.readline()
	print lsmod_out
	if (re.search(r'^be2net', lsmod_out)):
		print "be2net driver is already loaded"
		return 0
	else:
		print "Driver is not loaded"
		return 1


def load_nic_driver(conn, path, ver):
	#Clear the system logs first
	conn.exec_command("dmesg -c")
	kill_network_manager(conn)
	#Now load the driver module
	print "Loading NIC driver from %sbe2net-%s" %(path,ver)
	stdin, stdout, stderr = conn.exec_command("insmod %s/be2net-%s/be2net.ko" %(path,ver))
	time.sleep(10)
	print  stdout.readlines()
	stdin, stdout, stderr = conn.exec_command("dmesg -c")
	dmesg_out = stdout.read()
	match = re.search(r'initialization failed', dmesg_out)
	if match:
                log_msg = "Failed to load NIC driver module.\n System logs below.\n%s" %dmesg_out
                return (1,log_msg)
        else:
                log_msg ="Driver loaded successfully\n"
                stdin, stdout, stderr = conn.exec_command("lsmod | grep -i be2net")
		log_msg = log_msg + stdout.read()
                return (0,log_msg)


def kill_network_manager(conn):
	#Times to try: ttt
	ttt = 5
	i=0
	stdin, stdout, stderr = conn.exec_command("service NetworkManager status")
	status_out = stdout.read()
	print status_out
	running = re.search(r"NetworkManager \(pid  \d+\) is running...", status_out)
	if running:
		while i<ttt:
			stdin, stdout, stderr = conn.exec_command("service NetworkManager stop")
			print stdout.read()
			stdin, stdout, stderr = conn.exec_command("service NetworkManager status")
			status_out = stdout.read()
			match = re.search(r"NetworkManager is stopped", status_out)
			if match:
				print "NetworkManager stopped successfully"
				return
			else:
				i+=1
		print "\nGiving up on stopping NetworkManager\n"
	else:
		return
	

def unload_driver(conn, num_ports):
        print "\nUnloading be2net driver\n"
        pf=0
	conn.exec_command("dmesg -c")
        stdin, stdout, stderr = conn.exec_command("rmmod be2net")
        time.sleep(10)
	print  stdout.readlines()
        stdin, stdout, stderr = conn.exec_command("dmesg -c")
	dmesg_out = stdout.read()
        tmp_lines = dmesg_out.splitlines()
        '''for line in tmp_lines:
                match = re.search(r'^be2net \w+:\w+:\w+\.\w+: PCI INT \w disabled',line) #**************************This is not working for VFs**************#
                if match:
                        print match.group()
                        pf=pf+1
        if (pf==num_ports):'''
        log_msg ="Successfully unloaded be2net driver module\n"
        return (0,log_msg)
        '''else:
                log_msg ="Something went wrong in unloading driver module\n"
		return (1,log_msg)'''


def get_iface_list(conn):
	print "\nGetting the interface list\n"
	if_list=[]
        stdin, stdout, stderr = conn.exec_command("ifconfig -a | egrep -i '00:90:FA*|00:00:C9*'")
	ifcfg_out = stdout.readlines()
        for line in ifcfg_out:
                match = re.search(r'^eth\d+', line)
                if_list.append(match.group())
	print "Interfaces found: %s" %if_list
	return if_list


def verify_iface(list_iface,num_ports):
	print "\nChecking number of Interfaces found"
	if (len(list_iface) == num_ports):
		log_msg = "Number of Interfaces found: %s is equal to the number of ports: %s" % (len(list_iface),num_ports)
		return (0,log_msg)
	else:
		log_msg = "Number of Interfaces found: %s is NOT equal to the number of ports: %s!!" % (len(list_iface),num_ports)
		return (1,log_msg)


def check_link(conn, if_list, num_ports):
	print "\nUsing ethtool check if link is up on ports"
	status = "PASS"
	log_msg = ""
        for i in range(0, num_ports):
                #Bring up the interface before checking for link. Some version of driver don't see link up otherwise
                conn.exec_command("ifconfig %s up" %if_list[i])
                stdin, stdout, stderr = conn.exec_command("ethtool %s" %if_list[i])
                ethtool_out = stdout.read()
		print ethtool_out
                match = re.search(r'Link detected: \w+', ethtool_out)
                link_status = match.group().split(':')
                if (link_status[1] == ' yes'):
                        log_msg = log_msg + "\nLink detected on interface %s" %if_list[i]
                else:
                        log_msg = log_msg + "\nLink NOT detected on interface %s" %if_list[i]
			status = "FAIL"
	if (status == "FAIL"):
		return (1,log_msg)
	else:
		return (0,log_msg)


def config_iface(conn, if_list, ip_list):
        print "Configuring IP address on the interfaces %s" %if_list
        try:
		for (iface, ip) in zip(if_list, ip_list):
			stdin, stdout, stderr = conn.exec_command("ifconfig %s %s up" %(iface, ip))
		#TODO:Add more error handling code
	except:
		return 1
        stdin, stdout, stderr = conn.exec_command("ifconfig -a")
	print stdout.read()
	return 0


def ping_test(conn, list_peer, num_ports, mtu=0):
        print "Performing PING test on each port (not in parallel)"
	log_msg = ""
	status = "PASS"
        for i in range(0,num_ports):
                if (mtu!=0):
                        stdin, stdout, stderr = conn.exec_command("ping %s -c 10 -s %s" %(list_peer[i],mtu))
			ping_out = stdout.read()
                else:
                        stdin, stdout, stderr = conn.exec_command("ping %s -c 10" %list_peer[i])
			ping_out = stdout.read()
                print ping_out
                #match = re.search(r'Destination Host Unreachable', ping_out)
		packet_loss = re.search(r'(\d+)% packet loss', ping_out)
                #TODO:Add error handling when no ip is configured on host interfaces
                if packet_loss:
			lost = int (packet_loss.groups()[0])
			if lost > 0:
				log_msg = "!!! Ping failed: %s !!! Aborting further tests" %(packet_loss.group())
				log_msg = log_msg + "Ping failed to peer @ %s\n" %list_peer[i]
				status = "FAIL"
                else:
                        log_msg = log_msg + "Ping successful to peer @ %s\n" %list_peer[i]
        if (status == "FAIL"):
		return (1,log_msg)
	else:
		return (0,log_msg)


def iperf_test(conn, list_peer, num_ports):
        print "Performing TCP test with IPERF on each port (not in parallel)"
	log_msg = ""
	status = "PASS"
        for i in range(0,num_ports):
                stdin, stderr, stdout = conn.exec_command("iperf -c %s -w 2M -t 30 -P 5" %list_peer[i])
                iperf_out = stdout.read()
		print iperf_out
                match1 = re.search(r'connect failed: Connection refused', iperf_out)
                match2 = re.search(r'write1 failed: Broken pipe', iperf_out)
                if (match1 or match2):
                        log_msg = log_msg + "\nIperf test failed to peer @ %s\n" %list_peer[i]
			status = "FAIL"
                else:
                        log_msg = log_msg + "\n Iperf test to peer @ %s successful\n" %list_peer[i]
        if (status == "FAIL"):
		return (1,log_msg)
	else:
		return (0,log_msg)


def config_vlan(conn, if_list, vlan_list, vlan_ip_list):
	print "\nAdding VLAN tag on interfaces %s" %if_list
	for (iface, vlan, vlan_ip) in zip(if_list, vlan_list, vlan_ip_list):
		stdin, stdout, stderr = conn.exec_command("ifconfig %s 0.0.0.0" %iface)
		stdin, stdout, stderr = conn.exec_command("vconfig add %s %s" %(iface,vlan))
		print stdout.read()#TODO: Add error handing code
		stdin, stdout, stderr = conn.exec_command("ifconfig %s.%s %s up" %(iface,vlan,vlan_ip))
	return (0, "\nVLAN tag added on all interfaces")


def remove_vlan(conn, if_list, vlan_list):
	print "\nRemoving VLAN tag on interfaces %s" %if_list
	for (iface, vlan) in zip(if_list, vlan_list):
		stdin, stdout, stderr = conn.exec_command("vconfig rem %s.%s" %(iface,vlan))
		print stdout.read()
	return (0, "\nVLAN tag removed on all interfaces")


def change_mtu(conn, iface, mtu):
        print "Changing MTU size on the interfaces using ip"
	log_msg = ""
        stdin, stdout, stderr = conn.exec_command("ip link set %s mtu %s" %(iface, mtu))
        time.sleep(5)
        stdin, stdout, stderr = conn.exec_command("ip link show %s" %iface)
        ip_out = stdout.read()
	print ip_out
        match = re.search(r'mtu %s' %mtu, ip_out)
        if (match):
                log_msg = log_msg + "\nSuccessfully set mtu size %s for interface %s" %(mtu, iface)
		return (0,log_msg)
        else:
                log_msg = "\nRead MTU size is not same as set MTU size"
        	return (1,log_msg)


def run_iperf_server(conn):
	print "Running Iperf server..."
	#Kill any iperf sessions if already running
	conn.exec_command("killall iperf")
	conn.exec_command("iperf -s -w2M &")
	#print stdout.read()
	return 0



	
		
