import time
from datetime import datetime
import serial
import os
import sys
import MySQLdb
from MySQLPwd import MySQLID, MySQLpassword
import signal
import random

en_Debug = 0
en_SlientMode = 0
en_Emulation = 0
en_Service = 0

COM_Path = ''
str_ScriptName = ''
ser = None
db = None

#-----------------------------
# Connect to MySQL
#-----------------------------
def connect_db():
  global db, en_Service

  while 1:
    try:
      db = MySQLdb.connect(host = "localhost", user=MySQLID, passwd=MySQLpassword, db="dht")
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
                               baudrate = 9600,
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
  global en_Emulation, str_ScriptName, en_SlientMode, en_Service
  
  str_ScriptName = argv[0]
  if len(argv) < 2: return
  if argv[1].lower() == 'emulation':
    en_Emulation =1
  elif argv[1].lower() == 'service':
    en_SlientMode = 1
    en_Service = 1
  else:
    print str_ScriptName + " Error: Parameter not found: " + argv[1];
    exit(1)
  
#-----------------------------
# Main
#-----------------------------
def main(argv):
  global db

  pase_argv(argv)
  connect_db()
  
  # Setup serial port
  if Setup_Serial() is None:
    print str_ScriptName + " Error: Can Not Find COM Port."
    exit(1)

  # Initi DHT table on SQL server
  cursor = db.cursor()
  cursor.execute("Truncate table dht")
  db.commit()

  signal.signal(signal.SIGINT, signal_handler)

  # Read from Serial Port and insert to SQL server
  while 1:
    DHT_read = Read_Serial().strip()
    if(DHT_read != ""):
      time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
      if(not en_SlientMode):
        os.system("clear")
        print "Reading from " + COM_Path + "..."
        print(DHT_read)
        print time_str
        print ""
        print("Press Ctrl-C to Exit...")
      add_DHT_Reading = "insert into dht (Reading, DateTime) values (%s,%s)"
      data_DHT_Reading = (DHT_read,time_str)
      if(en_Debug and not en_SlientMode):
        print add_DHT_Reading
        print data_DHT_Reading
      cursor.execute(add_DHT_Reading,data_DHT_Reading)
      db.commit()
    if en_Emulation == 1:
      time.sleep(1)
    else:
      time.sleep(0.1)

if __name__ == "__main__":
    main(sys.argv[0:])
