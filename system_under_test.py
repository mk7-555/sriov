#!/usr/bin/python

__author__ = "Madhu Kesavan"
__email__  = "madhusudhanan.kesavan@emulex.com"

import commands
import re

#'object' is the parent of all classes.
class Physical_machine(object):
        'Pass in a config file with the following parameters'
        def __init__(self, config_file):
                self.ipaddress          = config_file.ipaddress
                self.user               = config_file.user
                self.passwd             = config_file.passwd
                self.driv_path          = config_file.driv_path
                self.driv_ver           = config_file.driv_ver
                self.logs_file          = config_file.logs_file
                self.num_ports          = config_file.num_ports
                self.ip_list            = config_file.ip_list
                self.peer_list          = config_file.peer_list
                self.vlan_list          = config_file.vlan_list
                self.vlan_ip_list       = config_file.vlan_ip_list
                self.vlan_peer_list     = config_file.vlan_peer_list
                self.mtu_list           = config_file.mtu_list
	
	def is_reachable(self):
		ping_out = commands.getoutput("ping %s -c 4" %self.ipaddress)
		if (re.search(r'Destination Host Unreachable', ping_out)):
			print "Machine @%s not reachable!" %self.ipaddress
			return 1
		else:
			print "Host @%s is up and running..." %self.ipaddress
			return 0


#This class subclasses the above defined class.
class Virtual_machine(Physical_machine):
	'Defines its own constructor so overrides base class constructor'
	def __init__(self, config_file):
		'Explicitly call base class constructor'
		Physical_machine.__init__(self, config_file)
		self.vm_peer_list	= config_file.vm_peer_list
		self.pf_ip_list		= config_file.pf_ip_list

