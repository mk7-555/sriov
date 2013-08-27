#!/usr/bin/python

__author__ = "Madhu Kesavan"
__email__  = "madhusudhanan.kesavan@emulex.com"

'***************************************'
#	Native Python Modules
'***************************************'
import sys
import commands
import re
import shutil
import paramiko
import time
import os

'***************************************'
#	User defined Modules
'***************************************'
import peer_conf
import peer_utils
import build_utils
import log_utils
import system_under_test
import sut1_conf
import sut2_conf

sys.path.append('/root/mk7/sriov_scripts/guest_scripts')
import nic_tests

'***************************************'
#	Command Line Arguments
'***************************************'
scm_build_ver	= sys.argv[1]
firm_ver	= sys.argv[2]
driv_ver	= sys.argv[3]
num_ports	= int(sys.argv[4])
num_vfs		= int(sys.argv[5])

driv_path	= "/root/evt/driver/"
driver_name	= "be2net.ko"
host_logs_path	= "/root/evt/atm/logs"
vm_logs_path 	= "/root/evt/atm/logs/vm_logs/"
host_logs	= "%s/%s_sriov_host_logs_%s.txt" %(host_logs_path, scm_build_ver, time.ctime().replace(" ","_"))

#Skyhawk B0 Max Supported VFs
max_vfs_1port	= 63
max_vfs_2port	= 63
max_vfs_4port	= 31

vf_index_2port	= ['0', '1']
vf_index_4port	= ['0']
vm1_vf_list	= ['vf0', 'vf4', 'vf8', 'vf12']
vm2_vf_list	= ['vf1', 'vf5', 'vf9', 'vf13']

iface_list	= []
pf_iface_list	= []

'A nested dictionary structure to store the BDF for each VF PCI stub'
bdf_dict_vf 	= {}

'***************************************'
#	Virtualization Domain Params
'***************************************'
domainxml_path 	= "/etc/libvirt/qemu/"
xml_vm1 	= "VM1-RHEL-6.1.xml"
xml_vm2 	= "VM2-RHEL-6.1-clone.xml"
domain_vm1 	= "VM1-RHEL-6.1"
domain_vm2 	= "VM2-RHEL-6.1-clone"

#Test cases list run on Host
#TODO: Move to a separate config file ?
sriov_host_tests = ["load_driver", "ping_test", "unload_driver", "load_driver_with_VFs", "verify_vf", "verify_iface", "check_link", "detach_VFs", "attach_VFs", "change_vf_privilege"]


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


#TODO: Do not hardcode the PCI Device ID.
#TODO: Device IDs for VFs have changed. They are now the same as PFs.
def verify_vf(vf_per_port):
	print "Check lspci output to see if all VFs are instantiated"
	vf_count = int(commands.getoutput("lspci -nnvvvt | grep -i 0720 | wc -l"))
	vf_count -= num_ports
	if (vf_count != (num_ports*vf_per_port)):
		log_msg = "Number of VFs found: %d were not equal to the number requested: %d!\n" %(vf_count, num_ports*vf_per_port)
		sriov_results.record_test_data("verify_vf", "FAIL", "ABORT", log_msg)
	else:
		log_msg ="Number of VFs instantiated: %d\n" %(vf_count)
		sriov_results.record_test_data("verify_vf", "PASS", "INFO", log_msg)
		return 0


#TODO: MAC addresses might be other than 00:90:FA. Need to handle this condition.
def verify_iface(vf_per_port):
	print "Check ifconfig output to see if all interfaces are initialized"
	try:
		iface_count = int(commands.getoutput("ifconfig -a | egrep -i '00:90:FA:*|00:00:C9:*' | wc -l"))
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
	ifcfg_out = commands.getoutput("ifconfig -a | egrep -i '00:90:FA:*|00:00:C9:*'")
	tmp_lines = ifcfg_out.splitlines()
	for line in tmp_lines:
		match = re.search(r'^eth\d+', line)
		if match:
			list_iface.append(match.group())
		else:
			print "No interfaces found with name eth# !"
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

#TODO: Device IDs for VF has changed. Need to implement a new way to find out BDF. 
#TODO: Can use setpci to read the register at offset 0x58 and masking out the LSb. 1-indicates it is a VF. 0-indicates it is a PF.
def generate_vf_bdf_dict():
    	print "Getting the Bus:Device:Function number for each VF stub"
	vf_idx = 0
	pf_idx = 0
        #lspci_out = (commands.getoutput("lspci | grep -i Emulex | grep -i 0728")).splitlines()
        lspci_out = (commands.getoutput("lspci | grep -i Emulex | grep -i 0720")).splitlines()
	while (pf_idx < num_ports):
		pf_idx += 1
		lspci_out.pop(0)
        for vf_stub in lspci_out:
                match = re.search(r'\w+:\w+\.\w+', vf_stub)
                tmp1 = match.group().split(':')
                bus_id = tmp1[0]
                tmp2 = tmp1[1].split('.')
                dev_id =  tmp2[0]
                func_id = tmp2[1]
                vf_name = 'vf%s' %vf_idx
                bdf_dict_vf[vf_name] = {'bus_id':bus_id, 'dev_id':dev_id, 'func_id':func_id}
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
	print "Define the new XML configurations"
	define_out = commands.getoutput("virsh define %s" %xml_file)
	print define_out


#TODO: Convert argument to list
def start_VM(xml_file):
	print "Starting the Virtual Machine %s" %xml_file
	start_out = commands.getoutput("virsh start %s" %xml_file)
	sriov_results.record_test_data("start_VM", None, "INFO", start_out+commands.getoutput("virsh list")+"\n")


def shutdown_VM(xml_file):
	print "Shutting down the Virtual Machine %s" %xml_file
	shut_out = commands.getoutput("virsh shutdown %s" %xml_file)
	#sriov_results.record_test_data("shutdown_VM", None, "INFO", shut_out+commands.getoutput("virsh list")+"\n")
	#In record_test_data: handle cases when a key does not hash to any element


def copy_driver_files_to_VM(ip, dest):
	print "Copying the test driver files to Virtual Machine@%s" %ip
	print (commands.getoutput("scp -r %sbe2net-%s root@%s:%s" %(driv_path, driv_ver, ip, dest)))


def vlan_privilege(list_iface, vf_index):
	print "Changing privilege level of VFs to allow guest VLAN tagging"
	status = "PASS"
	commands.getoutput("dmesg -c")
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


def get_logs_file(ip, file, dest):
	print "Collecting logs file %s from Machine@%s" %(ip, file)
	ssh = paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	ssh.connect(ip)
	stdin, stdout, stderr = ssh.exec_command("scp %s root@%s:%s" %(file, ip, dest))
	print stderr.readlines()
	print stdout.readlines()


def poll_results():
	print"\n\n Polling the results directory to see if VMs have sent any results file..."
	while(not (os.path.isfile('/root/evt/atm/logs/vm_logs/vm1_logs_%s.txt' %driv_ver) and os.path.isfile('/root/evt/atm/logs/vm_logs/vm2_logs_%s.txt' %driv_ver))):
		time.sleep(2)
		print "Still waiting..."
	time.sleep(5)
	print "Results file available! Tests complete!!"


def form_email_text(all_tests):
	all_results = ""
	for test in all_tests:
		all_results = all_results + "*"*70 + log_utils.analyze_results(test.test_results) + "\n"*3
	return all_results



#TODO: Implement Python's getopt method for getting command line arguments
if __name__ == "__main__":
	
	print "*"*70+"\nSkyhawk SRIOV smoke tests Started\n"+"*"*70
	
	# Contructor takes test cases list and log file that you want to use
	sriov_results = log_utils.Results(sriov_host_tests, host_logs)

	'''build_utils.cleanup_downloads()

	build_utils.get_driv_build(driv_ver)'''
	
	#Test case 1: Load NIC driver without VFs
	print "-"*70+"\nTest case 1: Load NIC driver without VFs\n"+"-"*70
	load_driver(0)
	
	#Find out the PFs and their BDFs
	pf_iface_list = get_iface_list()

	#TODO: Add test case: Ping without VFs loaded
	
	#Test case 2: Unload NIC driver (without VFs)
	print "-"*70+"\nTest case 2: Unload NIC driver (without VFs)\n"+"-"*70
	unload_driver()
	
	#Test case 3: Load NIC driver with VFs
	print "-"*70+"\nTest case 3: Load NIC driver with VFs\n"+"-"*70
	load_driver(num_vfs)
	
	#Test case 4: Verify number of VF stubs instantiated
	print "-"*70+"\nTest case 4: Verify number of VF stubs instantiated\n"+"-"*70
	verify_vf(num_vfs)
	
	#Test case 5: Verify number of interfaces initialized
	print "-"*70+"\nTest case 5: Verify number of interfaces initialized\n"+"-"*70
	verify_iface(num_vfs)
	
	generate_vf_bdf_dict()
	
	#Test case 6: Check link up on all Physical interfaces
	print "-"*70+"\nTest case 6: Check link up on all Physical interfaces\n"+"-"*70
	if (not check_link(pf_iface_list)):
		sriov_results.record_test_data("check_link", "PASS", "INFO", "Link detected on all interfaces.\n")
	else:
		sriov_results.record_test_data("check_link", "FAIL", "FAIL", "Link NOT detected on all interfaces.\n")
	
	#Test case 7: Use Virsh to detach a VF stub from host
	#TODO: Change this. If the number of VMs is not two then what happens ?
	print "-"*70+"\nTest case 7: Use Virsh to detach a VF stub from host\n"+"-"*70
	if (not detach_VFs_from_host(vm1_vf_list) and not detach_VFs_from_host(vm2_vf_list)):
		sriov_results.record_test_data("detach_VFs", "PASS", "INFO", "All VFs Successfully detached from host\n")
	else:
		sriov_results.record_test_data("detach_VFs", "FAIL", "ABORT", "NOT All VFs Successfully detached from host\n")

	if (not attach_VFs_to_VM(domainxml_path+xml_vm1, vm1_vf_list) and not attach_VFs_to_VM(domainxml_path+xml_vm2, vm2_vf_list)):
		sriov_results.record_test_data("attach_VFs", "PASS", "INFO", "All VFs Successfully attached to VMs\n")
	else:
		sriov_results.record_test_data("detach_VFs", "FAIL", "ABORT", "NOT All VFs Successfully attached to VMs\n")
	time.sleep(10)
	
	try:
		start_VM(domain_vm1)
		start_VM(domain_vm2)
	except:
		sriov_results.record_test_data("start_VM", None, "ABORT", "VM cannot start. Check configuration or logs.\n")
	
	print "Waiting 180 seconds for the VMs to start..."
	time.sleep(180)

	#Test case 8: Assign VLAN privilege to VFs
	print "-"*70+"\nTest case 8: Assign VLAN privilege to VFs\n"+"-"*70
	if (not vlan_privilege(pf_iface_list, [vf_index_4port if num_ports==4 else vf_index_2port])):
		sriov_results.record_test_data("change_vf_privilege", "PASS", "INFO", "Successfully assigned VLAN privilege to VFs\n")
	else:
		sriov_results.record_test_data("change_vf_privilege", "FAIL", "WARN", "Successfully assigned VLAN privilege to VFs\n")
	
	sriov_results.logs.close()
	
	'**********************************************************************'
	#TODO: Change this to list based approach.
	#TODO: Add multithreading support to run VMs in parallel.
	'**********************************************************************'

	vm1 = system_under_test.Virtual_machine(sut1_conf)
	vm1_results = log_utils.Results(sut1_conf.nic_tests, vm1.logs_file)
	copy_driver_files_to_VM(vm1.ipaddress, vm1.driv_path)
	
	vm2 = system_under_test.Virtual_machine(sut2_conf)
	vm2_results = log_utils.Results(sut2_conf.nic_tests, vm2.logs_file)
	copy_driver_files_to_VM(vm2.ipaddress, vm2.driv_path)
	
	"""
	NIC tests on Virtual machine start here
	"""
	if not vm1.is_reachable():
		nic_tests.execute_tests(vm1, vm1_results)
		vm1.logs_file.close()		
		get_logs_file(vm1.ipaddress, vm1.logs_file, vm_logs_path)

	if not vm2.is_reachable():
		nic_tests.execute_tests(vm2, vm2_results)
		vm1.logs_file.close()
		get_logs_file(vm2.ipaddress, vm2.logs_file, vm_logs_path)
	
	shutdown_VM(domain_vm1)
	shutdown_VM(domain_vm2)
	# !!!!!! WARNING: Be sure not to delete the original VM xml configuration!
	restore_xml_config(domainxml_path+xml_vm1)
	restore_xml_config(domainxml_path+xml_vm2)
	
	log_utils.send_email(scm_build_ver, "PASS", "SRIOV Smoke Test Results", form_email_text([sriov_results, vm1_results, vm2_results]),  host_logs)
	
	print "*"*70+"\nSkyhawk SRIOV smoke tests completed\n"+"*"*70

