#!/bin/python
# -*-coding:Utf-8 -*

try:
    from subprocess import Popen, PIPE, check_output
    import re,json,sys
    from time import strftime, gmtime
    import argparse
except ImportError:
    print ("Fail to load module. You need module: subprocess, json, time, argparse")
    sys.exit(1)

parser = argparse.ArgumentParser(description='')
parser.add_argument("-s", "--since", dest='older', help="Start showing entries on or newer than the specified date. It can be set to 'today','yesterday','2012-10-30', '2012-10-30 18:17:16'", default="yesterday", type=str)
parser.add_argument("-u", "--until", dest='newer', help="Start showing entries on or older than the specified date", default="now", type=str) 
parser.add_argument("-c", "--command", dest='command', help="Show journalctl commande", action='store_true')
parser.add_argument("-v", "--verbose", dest='report', help="Show report", action='store_true')
parser.add_argument("-b", "--blacklist", dest='blacklist', help="Show blacklist", action='store_true')
parser.add_argument("-w", "--write", dest="write", help="Write blacklist to file", default=False, type=str )
parser.add_argument("-r", "--read", dest="read", help="Read blacklist from file", default=False, type=str )
parser.add_argument("-a", "--attemps", dest="attemps", help="Number of attemps by hosts ip", action='store_true')
args = parser.parse_args()

older = args.older
newer = args.newer
show_com = args.command
show_report = args.report
show_blacklist = args.blacklist
output_file = args.write
input_file = args.read

now = strftime("%Y-%m-%d  %H:%M:%S", gmtime())

output = check_output(["journalctl", "-u", "smtpd", "--since", older, "--until", newer, "--no-pager", "-ojson"], universal_newlines=True).split('\n')

regex_newsession = r"smtp-in: New session"
search_newsession = re.compile(regex_newsession)

regex_failed = r"smtp-in: Failed command on session"
search_failed = re.compile(regex_failed)

regex_fullsession = r"session [A-Za-z0-9]{16}"
search_fullsession = re.compile(regex_fullsession)

regex_session = r"[A-Za-z0-9]{16}"
search_session = re.compile(regex_session)

regex_ip = r"\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\]"
search_ip = re.compile(regex_ip)

def add_mess(jsonin):
    all_dict = {}
    for line in jsonin:
      if line:
        l = json.loads(line)
        message = l['MESSAGE']
        mess_date = l['__REALTIME_TIMESTAMP']
        if message is not None:
          if search_fullsession.search(message) is not None:
            session = search_session.search(message).group(0)
            if session not in all_dict:
               all_dict[session] = []
            all_dict[session].append([mess_date,message])
    return (all_dict)

all_dict = add_mess(output)

def find_faileds(all_dict):
    faileds_dict = {}
    for keys,values in all_dict.items():
      for mess in values:
        if search_failed.search(str(mess)) is not None:  
          faileds_dict[keys] = values
    return (faileds_dict)

faileds_dict = find_faileds(all_dict)

def parse_faileds(faileds_dict):
    blacklist = []
    attemps_dict = {}
    for fkeys,fvalues in faileds_dict.items():
        if search_ip.search(fvalues[0][1]) is not None:
            hostip = search_ip.search(fvalues[0][1]).group(0)
            hostip2 = hostip[1:-1]
            if hostip2 not in blacklist:
                blacklist.append(hostip2)
        for failed_attemps in fvalues[1]:
            if search_failed.search(failed_attemps) is not None:
                if search_ip.search(faileds_dict[fkeys][0][1]) is not None:
                    hi = search_ip.search(faileds_dict[fkeys][0][1]).group(0)
                    hi2 = hi[1:-1]
                    if hi2 not in attemps_dict:
                        attemps_dict[hi2] = 1
                    attemps_dict[hi2] += 1
    return (blacklist,attemps_dict)

blacklist,attemps_dict = parse_faileds(faileds_dict)

if args.attemps is True:
    for akeys,avalues in attemps_dict.items():
        print("Host: %s, Number of attemps: %s." % (akeys,avalues))

if show_com is True:
    print("journalctl -u smtpd --since '%s' --until '%s' --no-pager " % (older,newer))

if show_blacklist is True:
    for ipss in blacklist:
        print(ipss)

if input_file is not False:
    try :
        fr = open(input_file, 'r')
        for ip in fr:
            if search_ip.search(ip.rstrip()) is not None:
                ip1 = ip.rstrip()
                #print(ip1)
                if ip1 in blacklist:
                    blacklist.remove(ip1)
    except IOError: 
        print ("Info: Input File ./blacklist does not appear to exist.\nI will ignore it")

if show_report is True:
    print("journalctl -u smtpd --since '%s' --until '%s' --no-pager " % (older,newer))
    if output_file is not False:
        print("Total: %s failed session on %s since '%s' until '%s'  \nI have add %s ipv4 address in %s" % (len(faileds_dict), len(all_dict), older, newer, len(blacklist), output_file))
    else:
        print("Total: %s failed session on %s since '%s' until '%s'  \nI found %s ipv4 address but I didn't write it." % (len(faileds_dict), len(all_dict), older, newer, len(blacklist)))
        for ligne in blacklist:
            print(ligne)

if output_file is not False:
    fa = open(output_file, 'a')
    for line in blacklist:
        fa.write(line)
        fa.write("\n")
        
