#!/usr/bin/python

#***********Python modules**********#
import sys
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

email_sender="aragon@lab.sj.emulex.com"
email_recipient="madhusudhanan.kesavan@emulex.com"

#Test cases list run on Guest 1
guest1_tests = ["load_driver", "verify_iface", "check_link", "ping_peer", "iperf_test, config_vlan", "vlan_ping", "vlan_iperf", "remove_vlan", "change_mtu", "jumbo_ping", "vf_to_vf_ping", "vf_to_pf_ping", "unload_driver"]
#Test cases list run on Guest 2
guest2_tests = ["load_driver", "verify_iface", "check_link", "ping_peer", "iperf_test, config_vlan", "vlan_ping", "vlan_iperf", "remove_vlan", "change_mtu", "jumbo_ping", "vf_to_vf_ping", "vf_to_pf_ping", "unload_driver"]

test_cases = ["load_driver", "check_link", "ping_test", "iperf_test", "config_vlan", "vlan_ping", "vlan_iperf", "remove_vlan", "change_mtu", "jumbo_ping"]

total_tests=len(test_cases)
total_pass=0
total_fail=0
pass_pcnt=0
fail_pcnt=0

class severity_codes:
	INFO 	= 0 #Print to stdout and Logfile
	WARN 	= 1 #Print to stdout, Logfile and Results
	FAIL 	= 2 #Print to stdout, Logfile, Results and Email
	ABORT 	= 3 #Print to all and Exit program

class test_status:
	PASS = 0 #True test case result
	FAIL = 1 #True test case result
	NONE = 2 #Not used for recording test case result



class Results:
	"This class contains the methods to record your test data."	
	
	# A dictionary to store the results of test cases executed.
	# TODO: This needs to be changed.
	test_results = {}
	total_pass=0
	total_fail=0
	logs = ""

	# Pass the test cases list to this constructor
	def __init__(self, list_tests="", logs_file=""):
		for test in list_tests:
			self.test_results[test] = {'status':'', 'severity':'', 'errmsg':''}
		self.logs = open(logs_file,"w")
		print self.test_results

	def record_test_data(self, test_case="", status="PASS", severity="INFO", err_msg=""):
		# Store to test_results only if PASS or FAIL. Otherwise just print to log file.
		if (status=="PASS" or status=="FAIL"):
			self.test_results[test_case]['status']=status
			self.test_results[test_case]['severity']=severity
			self.test_results[test_case]['errmsg']=err_msg
		if (severity == "INFO"):
			msg = "\nINFO::: %s	\n%s\n" %(test_case,err_msg)
			print msg
			self.logs.write(msg)
		elif (severity == "WARN"): # Log the error message and continue with other tests
			msg = "="*80 + "\n\t !WARN!\n\t%s\n%s\n" %(test_case, err_msg) + "="*80
			print msg
			self.logs.write(msg)
		elif (severity == "FAIL"):
			msg = "="*80 + "\n\t !!!FAIL!!!\n\t%s\n%s\n" %(test_case, err_msg) + "="*80
			print msg
			self.logs.write(msg)
		elif (severity == "ABORT"):
			msg = "="*80 + "\n\t !!!!!ABORT!!!!!\n%s\n%s\n" %(test_case, err_msg) + "="*80 
			print msg
			self.logs.write(msg)
			self.logs.close()		
		if (status == "PASS"):
			self.total_pass += 1
		elif (status == "FAIL"):
			self.total_fail += 1
		if (severity == "ABORT"):
			#TODO: Send email with results before aborting.
			#TODO: If aborting then call analyze results and update the global results string. Then call send_email.
			sys.exit(1)


#TODO: In sriov case there are two sets of results to analyze. So pass a handle to each object separately.
def analyze_results(results):
	overall_results=""
	for key in results.keys():
		overall_results = overall_results + "<br><br><b>Test case:</b> %s &nbsp;&nbsp;&nbsp;&nbsp;<b>Status</b> = %s &nbsp;&nbsp;&nbsp;&nbsp;<b>Comment</b> = %s<br>" %(key,results[key]['status'],results[key]['errmsg'])
	print overall_results
	return overall_results


#TODO: Provide the following arguments: Overall status, Subject, Body, Attachments
def send_email(scm_build_ver, overall_status="PASS", subject="", results="", logs=""):

	msg 		= MIMEMultipart('mixed')
	msg['Subject'] 	= subject
	msg['From'] 	= email_sender
	msg['To'] 	= email_recipient
	
	ctype, encoding = mimetypes.guess_type(logs)
	if ctype is None or encoding is not None:
		ctype = 'application/octet-stream'
	
	maintype, subtype = ctype.split('/',1)
	if maintype == 'text':
		fp = open(logs, 'r')
		logs = MIMEText(fp.read(), _subtype=subtype)
	fp.close()
	logs.add_header('Content-Disposition', 'attachment; filename=%s_NIC_TEST_RESULTS.txt' %scm_build_ver)
	
	html = """\
	<html>
	  <head></head>
	  <body>
		<p><b>NIC Test Results</b>
		</p>
		<b>Build version:</b>%s<br>
		<br><b> Results </b><br>%s
	  </body>
	</html>
	""" %(scm_build_ver,results)

	part1 = MIMEText(html, 'html')
	part2 = MIMEText(results,'plain')
	msg.attach(part1)
	msg.attach(part2)
	msg.attach(logs)
	s = smtplib.SMTP('138.239.113.183')
	s.sendmail(email_sender, email_recipient, msg.as_string())
	s.quit()


#initialize_results()

#for case in test_cases:
#	record_test_data(case, "FAIL", "ABORT", "No Error")

#print "\n\n"
#for key in test_results.keys():
#	print test_results[key]
#print "Total pass=%s" %total_pass


