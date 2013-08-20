import telnetlib
import os
import time

host_ip = "10.192.32.14"
user = "admin"
password = "nbv12345"
interfaces = ["34", "36", "37", "38"]
iter=0

tnet_hndl = telnetlib.Telnet(host_ip)
print (tnet_hndl.read_until(b"login: "))
tnet_hndl.write(user.encode('ascii') + b"\n")
print (tnet_hndl.read_until(b"Password: "))
tnet_hndl.write(password.encode('ascii') + b"\n")
print (tnet_hndl.read_until(b"# "))
tnet_hndl.write(b"conf term" + b"\n")
print (tnet_hndl.read_until(b"# "))
#tnet_hndl.set_debuglevel(1)
while (iter < 1):
	for iface in interfaces:
		tnet_hndl.write(b"interface vfc" + iface.encode('ascii') + b"\n")
		print (tnet_hndl.read_until(b"# "))
		tnet_hndl.write(b"shutdown" + b"\n")
		print (tnet_hndl.read_until(b"# "))
		time.sleep(3)
		raw_input('Hit any key to no shut the ports: ')
		tnet_hndl.write(b"no shutdown" + b"\n")
	iter = iter+1
	print ("---------Iteration %d---------" %iter)
	time.sleep(5)
tnet_hndl.close()

