#!/usr/bin/python                                                                                                                                                                                

#On CentOS, you need to install MySQL-python.x86_64

import sys

# Importing some neccessary libraries
try:
    import MySQLdb as mysql, argparse
except ImportError:
   print "Fail to load module. Please install python-argparse and MySQL-python.x86_64"
   sys.exit(3)

parser = argparse.ArgumentParser()
parser.add_argument("-u", "--user", help="MySQL-user for database connection", required=True)
parser.add_argument("-p", "--password", help="MySQL-password for database connection", required=True)                                                                                                
parser.add_argument("-H", "--host", help="DB-Host you want to connect", required=True)
parser.add_argument("-w", "--warning", help="Warning connected client. Default is set to 90", type=int, default=90)
parser.add_argument("-c", "--critical", help="Critical connected client. Default is set to 100", type=int, default=100)
args = parser.parse_args()

# Defining MySQL-command configuration
host   = args.host
user   = args.user                                                                                                                                                                                   
password = args.password
warning = int(args.warning)
critical = int(args.critical)

# Queries which are executed for checking
queryStatus  = "SHOW STATUS LIKE 'Threads_connected'"

db  = mysql.connect(host=host, user=user, passwd=password)
cursor  = db.cursor()

def execute(user, password, host, queryStatus):
  exitcode = 3
  cursor.execute(queryStatus)
  result = cursor.fetchone()
  value = int(result[1])
  if value <= warning:
    resultString = "There is %s connected client. |client=%s;%s;%s" % (value, value, warning, critical)
    exitcode = 0
  if warning <= value <= critical:
    resultString = "Number of connected client is more than %s|client=%s;%s;%s " % (warning, value, warning, critical)
    exitcode = 1
  if critical <= value:
    resultString = "Number of connected client is more than %s|client=%s;%s;%s " % (critical, value, warning, critical)
    exitcode = 2
  return (resultString, exitcode)
  db.close()

result = execute(user, password, host, queryStatus)

print result[0]

sys.exit(result[1])
