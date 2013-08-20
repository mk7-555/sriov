#!/usr/bin/python
#Author: Madhu Kesavan

import commands

#build_version = "10.0.529.0"
#driv_version = "10.0.527.0"
firm_version = "10.0.529.0"
ftp_user = "se"
ftp_passwd = "se123"
ftp_path_firm = "ftp://138.239.115.170/scm_builds/be2/Palau_10.0/"+firm_version+"/packages/Internal/"
firm_zip = "Palau_"+firm_version+"_SHB0_UNIFIED_FW_ARMFW_Internal.zip"
ufi_path = "packages/Firmware/skyhawkB0/perf/"
driv_src_path = "packages/NIC/linux_src/"
firm_dir = "/root/evt/firmware/"
driv_dir = "/root/evt/driver/"
ufi = "oc14-"+firm_version+".ufi"

def cleanup_downloads():
	print "Deleting files from previous downloads..."
	commands.getoutput("rm -rf %spackages" %firm_dir)
	commands.getoutput("rm -rf %s*.zip" %firm_dir)
	commands.getoutput("rm -rf %spackages" %driv_dir)
	commands.getoutput("rm -rf %s*.gz" %driv_dir)
	commands.getoutput("rm -rf %s*.zip" %driv_dir)

def get_firm_build():
	print "Getting firmware build from SCM FTP path %s" %ftp_path_firm
	print (commands.getoutput("curl %s%s -u %s:%s -o %s%s.zip" %(ftp_path_firm,firm_zip,ftp_user,ftp_passwd,firm_dir,firm_version)))
	print "Unzipping contents of firmware zip file"
	print (commands.getoutput("unzip %s%s.zip -d %s" %(firm_dir,firm_version,firm_dir)))
	print (commands.getoutput("cp %s%s%s %s" %(firm_dir,ufi_path,ufi,firm_dir)))

def get_driv_build(driv_version=""):
	ftp_path_driv = "ftp://138.239.115.170/scm_builds/be2/Palau_10.0/"+driv_version+"/packages/Internal/"
	driv_zip = "Palau_"+driv_version+"_LNX_NIC_Internal.zip" 
	print "Getting driver build from SCM FTP path %s" %ftp_path_driv
	print (commands.getoutput("curl %s%s -u %s:%s -o %s%s.zip" %(ftp_path_driv,driv_zip,ftp_user,ftp_passwd,driv_dir,driv_version)))
	print "Unzipping contents of driver zip file"
	print (commands.getoutput("unzip %s%s.zip -d %s" %(driv_dir,driv_version,driv_dir)))
	print (commands.getoutput("cp %s%sbe2net-%s.tar.gz %s" %(driv_dir,driv_src_path,driv_version,driv_dir)))
	print (commands.getoutput("tar xvzf %sbe2net-%s.tar.gz -C %s" %(driv_dir,driv_version,driv_dir)))
	print "Building driver module from source"
	print (commands.getoutput("make -C %sbe2net-%s" %(driv_dir,driv_version)))
	

#cleanup_downloads()
#get_firm_build()
#get_driv_build()

	


