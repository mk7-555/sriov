#!/usr/bin/python

#**********Python modules**********#
import os
import sys
import subprocess
import commands
import re
import shutil
import paramiko
import time

#**********User modules**********#
import peer_conf
import peer_utils
import build_utils
import log_utils

sys.path.append('/root/evt/atm/sriov/guest_scripts')
import nic_tests
import guest1_conf
import guest2_conf

#**********Command line arguments**********#
scm_build_ver=sys.argv[1]
firm_ver=sys.argv[2]
driv_ver=sys.argv[3]
num_ports=int(sys.argv[4])

driv_path="/root/evt/driver/"
driver_name="be2net.ko"
host_logs_path="/root/evt/atm/logs"
host_logs=open("%s/%s_sriov_host_logs.txt" %(host_logs_path, scm_build_ver), 'w')

#Skyhawk B0 Max Supported VFs
max_vfs_1port=63
max_vfs_2port=63
max_vfs_4port=31
num_vfs=2

vf_index_2port=['0', '1']
#vf_index_4port=['0']
vm1_vf_list=['vf0', 'vf2']
#vm1_vf_list=['vf0', 'vf1']
vm2_vf_list=['vf1', 'vf3']
#vm2_vf_list=['vf2', 'vf3']

iface_list=[]
pf_iface_list=[]

#A nested dictionary structure to store the BDF for each VF PCI stub
bdf_dict_vf = {}

#**********Virtualization stuff**********#
domainxml_path = "/etc/libvirt/qemu/"
xml_vm1 = "VM1-RHEL-6.1.xml"
xml_vm2 = "VM2-RHEL-6.1-clone.xml"
domain_vm1 = "VM1-RHEL-6.1"
domain_vm2 = "VM2-RHEL-6.1-clone"

#Test cases list run on Host
sriov_host_tests = ["load_driver", "ping_test", "unload_driver", "load_driver_with_VFs", "verify_vf", "verify_iface", "check_link", "detach_VFs", "attach_VFs", "change_vf_privilege"]


class virtual_machine():
        def set_ip(self,ipaddress):
                self.ipaddress=ipaddress
        def set_user(self,user):
                self.user=user
        def set_passwd(self,passwd):
                self.passwd=passwd
        def set_driv_path(self,driv_path):
                self.driv_path=driv_path
	def set_driv_ver(self, driv_ver):
		self.driv_ver=driv_ver
        def set_logs_path(self,logs_path):
                self.logs_path=logs_path
	def set_num_ports(self,num_ports):
		self.num_ports=num_ports
	def set_ip_list(self,ip_list):
		self.ip_list=ip_list
        def set_peer_list(self,peer_list):
                self.peer_list=peer_list
	def set_vlan_list(self,vlan_list):
		self.vlan_list=vlan_list
	def set_vlan_ip_list(self,vlan_ip_list):
		self.vlan_ip_list=vlan_ip_list
	def set_vlan_peer_list(self,vlan_peer_list):
		self.vlan_peer_list=vlan_peer_list #TODO: Move attributes common to all machines to seperate class ?
	def set_mtu_list(self,mtu_list):
		self.mtu_list=mtu_list


def load_driver(vf_count):
	commands.getoutput("dmesg -c")
	if (vf_count != 0):
		log_msg = "Loading driver from %s with %s VFs. Version %s\n" %(driv_path, vf_count, driv_ver)
		insmod_out = commands.getoutput("insmod %sbe2net-%s/be2net.ko num_vfs=%s" %(driv_path, driv_ver, vf_count))
	else:
		log_msg = "Loading driver from %s. Version %s\n" %(driv_path, driv_ver)
		insmod_out = commands.getoutput("insmod %sbe2net-%s/be2net.ko" %(driv_path, driv_ver))
	sriov_results.record_test_data("load_driver", None, "INFO", log_msg+"\n"+insmod_out)
	time.sleep(10)
	dmesg_out = commands.getoutput("dmesg")
	sriov_results.record_test_data("load_driver", None, "INFO", dmesg_out)
	match = re.search(r'initialization failed', dmesg_out)
	if match:		
		if (vf_count != 0):
			sriov_results.record_test_data("load_driver_with_VFs", "FAIL", "ABORT", "Failed to load driver module with VFs\n")
		else:
			sriov_results.record_test_data("load_driver_with_VFs", "FAIL", "ABORT", "Failed to load driver module\n")
	else:
		log_msg ="Driver loaded successfully\n"
		lsmod_out = commands.getoutput("lsmod | grep -i be2net")
		if (vf_count != 0):
			sriov_results.record_test_data("load_driver_with_VFs", "PASS", "INFO", log_msg+"\n"+lsmod_out)
		else:
			sriov_results.record_test_data("load_driver", "PASS", "INFO", log_msg+"\n"+lsmod_out)
		return 0


def unload_driver():
	print "Unloading driver %s" %driver_name
	pf=0
	commands.getoutput("dmesg -c")
	rmmod_out = commands.getoutput("rmmod %s" %driver_name)
	time.sleep(10)
	sriov_results.record_test_data("unload_driver", None, "INFO", rmmod_out+"\n")
	dmesg_out = commands.getoutput("dmesg")
	tmp_lines = dmesg_out.splitlines()
	for line in tmp_lines:
		match = re.search(r'^be2net \w+:\w+:\w+\.\w+: PCI INT \w disabled',line)
		if match:
			print match.group()
			pf=pf+1
	if (pf==num_ports):
		sriov_results.record_test_data("unload_driver", "PASS", "INFO", "Successfully unloaded driver module: %s" %driver_name)
		return 0
	else:
		sriov_results.record_test_data("unload_driver", "FAIL", "ABORT", dmesg_out + "Failed to unload driver module: %s" %driver_name)


def verify_vf(vf_per_port):
	print "Check lspci output to see if all VFs are instantiated"
	try:
		vf_count = int(commands.getoutput("lspci -nnvvvt | grep -i 0728 | wc -l"))
		if (vf_count != (num_ports*vf_per_port)):
			log_msg = "Number of VFs found: %d were not equal to the number requested: %d!\n" %(vf_count, num_ports*vf_per_port)
			sriov_results.record_test_data("verify_vf", "FAIL", "ABORT", log_msg)
		else:
			log_msg ="Number of VFs instantiated: %d\n" %(vf_count)
			sriov_results.record_test_data("verify_vf", "PASS", "INFO", log_msg)
			return 0
	except:
		print "Failed to execute lspci command"
		sys.exit()


def verify_iface(vf_per_port):
	print "Check ifconfig output to see if all interfaces are initialized"
	try:
		iface_count = int(commands.getoutput("ifconfig -a | grep -i 00:90:FA:* | wc -l"))
		if (iface_count != (num_ports + num_ports*vf_per_port)):
			log_msg = "Number of interfaces found: %d were not equal to the number requested: %d!\n" %(iface_count, num_ports + num_ports*vf_per_port)
			sriov_results.record_test_data("verify_iface", "FAIL", "ABORT", log_msg)
		else:
			log_msg = "Number of interfaces initialized: %d\n" %(iface_count)
			sriov_results.record_test_data("verify_iface", "PASS", "INFO", log_msg)
			return 0
	except:
		print "Failed to execute ifconfig command"
		sys.exit()


def get_iface_list():
	list_iface=[]
	ifcfg_out = commands.getoutput("ifconfig -a | grep -i 00:90:FA*")
	tmp_lines = ifcfg_out.splitlines()
	for line in tmp_lines:
		match = re.search(r'^eth\d+', line)
		list_iface.append(match.group())
	sriov_results.record_test_data("get_iface_list", None, "INFO", list_iface)
	return list_iface


def check_link(list_iface):
	print "Check ethtool output to see if link is up on PFs"
	status = "PASS"
	for iface in list_iface:
		ifcfg_out = commands.getoutput("ifconfig %s up" %iface)
		time.sleep(2) #Need to wait, in-case interrupt arrives late
		ethtool_out = commands.getoutput("ethtool %s" %iface)
		sriov_results.record_test_data("check_link", None, "INFO", ethtool_out+"\n")
		match = re.search(r'Link detected: \w+', ethtool_out)
		link_status = match.group().split(':')
		if (link_status[1]==' yes'):
			sriov_results.record_test_data("check_link", None, "INFO", "Link detected on interface %s\n" %iface)
		else:
			status = "FAIL"
			sriov_results.record_test_data("check_link", None, "FAIL", "Link NOT detected on interface %s\n" %iface)
	if (status == "FAIL"):
		return 1
	else:
		return 0


def detach_VFs_from_host(bdf_list):
	print "Detaching VFs %s stubs from the host using Virsh" %bdf_list
	status = "PASS"
	for stub in bdf_list:
		detach_out = commands.getoutput("virsh nodedev-dettach pci_0000_%s_%s_%s" %(bdf_dict_vf[stub]['bus_id'],bdf_dict_vf[stub]['dev_id'],bdf_dict_vf[stub]['func_id']))
		print detach_out
		match = re.search(r'error: Could not find matching device \'pci_\w+_\w+_\w+_\w+\'', detach_out)
		if match:
			sriov_results.record_test_data("detach_VFs", None, "FAIL", "Problem detaching VF stub from host\n"+match.group()+detach_out)
			status = "FAIL"
		else:
			sriov_results.record_test_data("detach_VFs", None, "INFO", "Successfully detached VF stub %s" %stub)
	if (status == "FAIL"):
		return 1
	else:
		return 0


def generate_vf_bdf_dict():
    print "Getting the Bus Device Function ID for each VF stub"
	vf_idx = 0
        lspci_out = (commands.getoutput("lspci | grep -i Emulex | grep -i 0728")).splitlines()
        for vf_stub in lspci_out:
                match = re.search(r'\w+:\w+\.\w+', vf_stub)
                tmp1 = match.group().split(':')
                bus_id = tmp1[0]
                tmp2 = tmp1[1].split('.')
                dev_id =  tmp2[0]
                func_id = tmp2[1]
                vf_name = 'vf%s' %vf_idx
                bdf_dict_vf[vf_name] = {'bus_id':bus_id, 'dev_id':dev_id, 'func_id':func_id }
                vf_idx = vf_idx + 1
	for vf in bdf_dict_vf.keys():
		sriov_results.record_test_data("generate_vf_bdf_dict", None, "INFO", "%s \t %s\n" %(vf, bdf_dict_vf[vf]))


#TODO: Change argument to list type and handle null arguments
def attach_VFs_to_VM(xml_file, device_list):
	try:
		sriov_results.record_test_data("attach_VFs_to_VM", None, "INFO", "Editing the XML configuration file for domain %s" %xml_file)
		shutil.copy(xml_file, xml_file+"ORIG")
		orig_xml = open(xml_file+"ORIG", 'r')
		new_xml = open(xml_file, "w")
		for line in orig_xml:
			new_xml.write(line)
			match = re.search(r'\s\s<devices>\n', line)
			if match:
				for dev in device_list:
					new_xml.write( """    <hostdev mode='subsystem' type='pci'>
								<source>
								  <address domain='0x0000' bus='0x%s' slot='0x%s' function='0x%s'/>
								</source>
							      </hostdev>\n""" %(bdf_dict_vf[dev]['bus_id'], bdf_dict_vf[dev]['dev_id'], bdf_dict_vf[dev]['func_id']))
			else:
				pass
		orig_xml.close()
		new_xml.close()
		print "Define the new XML configurations"
		define_out = commands.getoutput("virsh define %s" %xml_file)
		print define_out
		#TODO: Add error handling code
		return 0
	except:
		print "Failed to edit XML configurations for VMs"
		return 1


def restore_xml_config(xml_file):
	try:
		os.remove(xml_file)
	except OSError, e:
		print "Error removing file %s - %s" %(e.filename, e.stderr)
	os.rename(xml_file+"ORIG", xml_file)
	print "Restored the original XML configuration file %s" %xml_file


#TODO: Convert argument to list
def start_VM(xml_file):
	print "Starting the Virtual Machine %s" %xml_file
	start_out = commands.getoutput("virsh start %s" %xml_file)
	sriov_results.record_test_data("start_VM", None, "INFO", start_out+commands.getoutput("virsh list")+"\n")


def shutdown_VM(xml_file):
	print "Shutting down the Virtual Machine %s" %xml_file
	shut_out = commands.getoutput("virsh shutdown %s" %xml_file)
	sriov_results.record_test_data("shutdown_VM", None, "INFO", shut_out+commands.getoutput("virsh list")+"\n")


#TODO: Convert argument to list
def scp_driver_files():
	print "Copying the test driver files to all VMs..."
	print (commands.getoutput("scp -r %sbe2net-%s root@%s:%s/" %(driv_path, driv_ver, guest1_conf.vm_ip, guest1_conf.driv_path)))
	print (commands.getoutput("scp -r %sbe2net-%s root@%s:%s/" %(driv_path, driv_ver, guest2_conf.vm_ip, guest2_conf.driv_path)))


def vlan_privilege(list_iface, vf_index):
	print "Changing privilege level of VFs to allow guest VLAN tagging"
	status = "PASS"
	for iface in list_iface:
		for vf in vf_index:
			ip_out = commands.getoutput("ip link set %s vf %s vlan 4095" %(iface, vf))
			sriov_results.record_test_data("change_vf_privilege", None, "INFO", commands.getoutput("dmesg"))
			if (ip_out == ""):
				sriov_results.record_test_data("change_vf_privilege", None, "INFO", "Successfully changed vlan privilege for vf %s on iface %s" %(vf, iface))
			else:
				match = re.search(r'RTNETLINK answers: Invalid argument', ip_out)
				if (match):
					status = "FAIL"
					sriov_results.record_test_data("change_vf_privilege", None, "FAIL", "Failed to change vlan privilege for VF %s on iface %s\n" %(vf, iface))
	if (status == "FAIL"):
		return 1
	else:
		return 0


def configure_peer_setup():
	conn = peer_utils.connect_ssh(peer_conf.mgmt_ip,peer_conf.user,peer_conf.passwd)
	if (peer_utils.check_driver(conn)):
		peer_utils.load_nic_driver(conn, peer_conf.driv_path, peer_conf.driv_ver)
	else:
		pass
	iface_list = peer_utils.get_iface_list(conn)
	if (not peer_utils.check_link(conn, iface_list, peer_conf.num_ports)):
		print "Link UP on all interfaces"
	if (not peer_utils.config_iface(conn, iface_list, peer_conf.peer_ip_2port)):
		print "Configured IP address on all interfaces"
	if (not peer_utils.run_iperf_server(conn)):
		print "Iperf started"
	print "Disconnecting from Peer machine..."
	conn.close()


def configure_virtual_machine(vm, conf):
	vm.set_ip(conf.vm_ip)
	vm.set_user(conf.vm_user)
	vm.set_passwd(conf.vm_passwd)
	vm.set_driv_path(conf.driv_path)
	vm.set_driv_ver(driv_ver)#Same driver as the PF. Change if needed.
	vm.set_logs_path(conf.vm_logs)
	vm.set_num_ports(num_ports)#Same as the number of PFs. Change if needed.
	vm.set_ip_list(conf.vm1_ip_2port)
	vm.set_peer_list(conf.peer_list_2port)
	vm.set_vlan_list(conf.vlan_list_2port)
	vm.set_vlan_ip_list(conf.vm1_vlanip_2port)
	vm.set_vlan_peer_list(conf.vlan_peer_2port)
	vm.set_mtu_list(conf.mtu_list)
	return


def remote_run(guest_ip, script):
	print "Running tests on remote machine %s" %guest_ip
	guest_ssh = paramiko.SSHClient()
	guest_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	#guest_ssh.connect(guest_ip,username='root',password='4Emulex')
	guest_ssh.connect(guest_ip)
	stdin, stdout, stderr = guest_ssh.exec_command("%s %s" %(script, driv_ver))
	print stderr.readlines()
	print stdout.readlines()#This needs to be changed. Lots of lines to print!


def poll_results():
	print"\n\n Polling the results directory to see if VMs have sent any results file..."
	while(not (os.path.isfile('/root/evt/atm/logs/vm_logs/vm1_logs_%s.txt' %driv_ver) and os.path.isfile('/root/evt/atm/logs/vm_logs/vm2_logs_%s.txt' %driv_ver))):
		time.sleep(2)
		print "Still waiting..."
	time.sleep(5)
	print "Results file available! Tests complete!!"


if __name__ == __main__:

	# Contructor takes test cases list and log file that you want to use
	sriov_results = log_utils.Results(sriov_host_tests, host_logs)

	build_utils.cleanup_downloads()

	build_utils.get_driv_build(driv_ver)

	#Test case 1: Load NIC driver without VFs
	load_driver(0)

	#Find out the PFs and their BDFs
	pf_iface_list = get_iface_list()

	#TODO: Add test case: Ping without VFs loaded
	
	#Test case 2: Unload NIC driver (without VFs)
	unload_driver()

	#Test case 3: Load NIC driver with VFs
	load_driver(num_vfs)

	#Test case 4: Verify number of VF stubs enabled
	verify_vf(num_vfs)

	#Test case 5: Verify number of interfaces initialized
	verify_iface(num_vfs)
	generate_vf_bdf_dict()

	#Test case 6: Check link up on all Physical interfaces
	if (not check_link(pf_iface_list)):
		sriov_results.record_test_data("check_link", "PASS", "INFO", "Link detected on all interfaces.\n")
	else:
		sriov_results.record_test_data("check_link", "FAIL", "FAIL", "Link NOT detected on all interfaces.\n")

	#Test case 7: Use Virsh to detach a VF stub from host
	if (not detach_VFs_from_host(vm1_vf_list) and not detach_VFs_from_host(vm2_vf_list)):
		sriov_results.record_test_data("detach_VFs", "PASS", "INFO", "All VFs Successfully detached from host\n")
	else:
		sriov_results.record_test_data("detach_VFs", "FAIL", "ABORT", "NOT All VFs Successfully detached from host\n")

	if (not attach_VFs_to_VM(domainxml_path+xml_vm1, vm1_vf_list) and not attach_VFs_to_VM(domainxml_path+xml_vm2, vm2_vf_list)):
		sriov_results.record_test_data("attach_VFs", "PASS", "INFO", "All VFs Successfully attached to VMs\n")
	else:
		sriov_results.record_test_data("detach_VFs", "FAIL", "ABORT", "NOT All VFs Successfully attached to VMs\n")
	time.sleep(10)

	start_VM(domain_vm1)
	start_VM(domain_vm2)
	print "Waiting 300 seconds for the VMs to start"
	time.sleep(300)

	scp_driver_files()

	#Test case 8: Assign VLAN privilege to VFs
	if (not vlan_privilege(pf_iface_list, vf_index_2port)):
		sriov_results.record_test_data("change_vf_privilege", "PASS", "INFO", "Successfully assigned VLAN privilege to VFs\n")
	else:
		sriov_results.record_test_data("change_vf_privilege", "FAIL", "WARN", "Successfully assigned VLAN privilege to VFs\n")

	#configure_peer_setup()

	vm1 = virtual_machine()
	config_vm_params(vm1, guest1_conf)
	log_utils.initialize_results(guest1_conf.nic_tests)

	vm2 = virtual_machine()
	config_vm_params(vm2, guest2_conf)
	log_utils.initialize_results(guest2_conf.nic_tests)

	nic_tests.execute_tests(vm1)
	nic_tests.execute_tests(vm2)

	# Add test cases for VF-VF and VF-PF

	shutdown_VM(domain_vm1)
	shutdown_VM(domain_vm2)

	# !!!!!! WARNING: Be sure not to delete the original VM xml configuration!
	restore_xml_config(domainxml_path+xml_vm1)
	restore_xml_config(domainxml_path+xml_vm2)
	#poll_results()

	print "end"