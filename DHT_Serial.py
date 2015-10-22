import time
from datetime import datetime
import serial
import os
import sys
import MySQLdb
from MySQLPwd import MySQLID, MySQLpassword
import signal
import random
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from EMailPwd import EmailID, Emailpassword
import socket
import fcntl
import struct

en_Debug = 0
en_SlientMode = 0
en_Emulation = 0
en_Service = 0
en_SendMail = 0

ServiceVer = ''
COM_Path = ''
str_ScriptName = ''
ser = None
db = None

#-----------------------------
# Get IP Address
#-----------------------------
def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])
  
#-----------------------------
# Send Event Alert
#-----------------------------
def Send_EventAlert(email, event):
  
  db = connect_db()
  cursor = db.cursor()

  cursor.execute('SELECT Value FROM dht.sysinfo where Name="ServiceName"')
  row = cursor.fetchone()
  str_ServiceName = row[0]

  cursor.execute('SELECT Value FROM dht.sysinfo where Name="ServiceVer"')
  row = cursor.fetchone()
  str_ServiceVer = row[0]

  if event == "boot":
      toaddr = []
      cursor.execute('SELECT email FROM dht.useralert where type like "%'+event+'%" and Enabled=TRUE')
      rows = cursor.fetchall()
      toaddr.append(EmailID + "@gmail.com")
      for row in rows:
        toaddr.append(row[0])

      if toaddr == []:
        return

      body = "Address: http://"+ get_ip_address("wlan0") + "/" + str_ServiceVer + "/dht.php\n"+\
              "Time: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
      title = str_ServiceName + " is Ready."

  elif event == "verify":
      toaddr = []
      cursor.execute('SELECT Email, ID, Hash FROM dht.useralert where EMail="'+email+'" and Enabled=FALSE')
      row = cursor.fetchone()
      if(row != None):
        toaddr.append(row[0])

      if toaddr == []:
        return

      body = "Please verify your email address by clicking the link below:\n"+\
             "http://"+ get_ip_address("wlan0") + "/" + str_ServiceVer + "/dht.php?cmd=" + event + "&id=" + str(row[1])  + "&key=" + str(row[2])
      title = "Verify your email address for " + str_ServiceName
      
  fromaddr = EmailID + "@gmail.com"
  msg = MIMEMultipart()
  msg['From'] = fromaddr
  msg['To'] = ", ".join(toaddr)
  msg['Subject'] = title
  msg.attach(MIMEText(body, 'plain'))
  Send_Email(fromaddr, toaddr, msg)

#-----------------------------
# Send EMail
#-----------------------------
def Send_Email(fromaddr, toaddr, msg):
   
   try:
     server = smtplib.SMTP('smtp.gmail.com', 587)
     server.ehlo()
     server.starttls()
     server.ehlo()
     server.login(EmailID, Emailpassword)
     text = msg.as_string()
     server.sendmail(fromaddr, toaddr, text)
     server.quit()
   except:
     pass
#-----------------------------
# Connect to MySQL
#-----------------------------
def connect_db():
  global db, en_Service, str_ServiceName, str_ServiceVer
  
  if db != None: return db
  
  while 1:
    try:
      db = MySQLdb.connect(host = "localhost", user=MySQLID, passwd=MySQLpassword, db="dht")
      return db
      break
    except Exception, e:
      if en_Service == 1:
        time.sleep(5)
        continue
      print str(e)
      print str_ScriptName + " Error: Can Not Connect to SQL Server. Exit."
      exit(1)

#-----------------------------
# Handler for Ctrl-C
#-----------------------------
def signal_handler(signal, frame):
  global ser, db

  if en_Emulation == 0: ser.close()
  db.commit()
  if(not en_SlientMode): print('Bye!')
  exit(0)
        
#-----------------------------
# Setup Serial Port
#-----------------------------
def Setup_Serial():

  global COM_Path, ser, en_Service
  
  COM_Exists = 0
  
  if en_Emulation == 1:
    COM_Path = "/Emulation"
    ser = 1
    return ser

  if COM_Path != '':
    try:
      if os.path.exists(COM_Path): return ser
    except Exception, e:
      COM_Path = ''
      ser = None
  
  while 1:
    for x in range(3):
      try:
        if(os.path.exists('/dev/ttyUSB' + str(x))):
           COM_Path = '/dev/ttyUSB' + str(x)
           COM_Exists = 1
           ser = serial.Serial(port=COM_Path,
                               baudrate = 115200,
                               parity=serial.PARITY_NONE,
                               stopbits=serial.STOPBITS_ONE,
                               bytesize=serial.EIGHTBITS,
                               timeout=1)
      except Exception, e:
        COM_Exists = 0
        continue
    if COM_Exists == 1 : break
    elif en_Service == 1 : continue
    else: break
    time.sleep(1)

  if (not COM_Exists):
    return

  return ser

#-----------------------------
# Read from Serial Port
#-----------------------------
def Read_Serial():
  global ser, en_Service
  
  if en_Service == 1: Setup_Serial()
  
  DHT_read = ""

  if en_Emulation == 1:
    DHT_read = "H:" + str(random.randint(55,65)) + "%, T:" + str(random.randint(25,30)) + "C"
    return DHT_read

  try:
    if(ser.inWaiting()>0):
      DHT_read=ser.readline()
  except Exception, e:
    return ""
  return DHT_read

#-----------------------------
# Pase Parament
#-----------------------------
def pase_argv(argv):
  global en_Emulation, str_ScriptName, en_SlientMode, en_Service, en_SendMail
  
  str_ScriptName = argv[0]
  if len(argv) < 2: return
  if argv[1].lower() == 'emulation':
    en_Emulation =1
  elif argv[1].lower() == 'service':
    en_SlientMode = 1
    en_Service = 1
  elif argv[1].lower() == 'mail':
    en_SendMail = 1
  else:
    print str_ScriptName + " Error: Parameter not found: " + argv[1];
    exit(1)
  
#-----------------------------
# Main
#-----------------------------
def main(argv):

  pase_argv(argv)
  db = connect_db()

  if(en_SendMail):
      Send_EventAlert(argv[2],argv[3])
      exit(0)
      
  time_tick = ""
  add_DHT_Reading = "insert into dht (Reading, DateTime, GroupID) values (%s,%s,%s)"
  
  # Setup serial port
  if Setup_Serial() is None:
    print str_ScriptName + " Error: Can Not Find COM Port."
    exit(1)

  # Initi DHT table on SQL server
  cursor = db.cursor()
  time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  cursor.execute("insert into dht_group (DateTime) values (%s)",time_str)
  cursor.execute("select ID from dht_group where DateTime='"+time_str+"'")
  row = cursor.fetchone()
  Group_ID = row[0]

  signal.signal(signal.SIGINT, signal_handler)
  Send_EventAlert(None,"boot")

  # Read from Serial Port and insert to SQL server
  while 1:
    DHT_read = Read_Serial().strip()
    if(DHT_read != ""):
      time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
      if(not en_SlientMode):
        os.system("clear")
        print "Reading from " + COM_Path + "..."
        print(DHT_read)
        print time_str + time_tick
        print ""
        print("Press Ctrl-C to Exit...")
        if time_tick == "": time_tick = "_"
        else: time_tick = ""
      data_DHT_Reading = (DHT_read,time_str,Group_ID)
      cursor.execute(add_DHT_Reading,data_DHT_Reading)
      db.commit()
    if en_Emulation == 1:
      time.sleep(1)
    else:
      time.sleep(0.1)

if __name__ == "__main__":
    main(sys.argv[0:])
