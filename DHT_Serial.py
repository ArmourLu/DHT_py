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
COM_Path = '/dev/ttyUSB'
str_ScriptName = ''
ser = None

try:
  db = MySQLdb.connect(host = "localhost", user=MySQLID, passwd=MySQLpassword, db="dht")
except Exception, e:
  if(not en_SlientMode): print "Error: Can Not Connect to SQL Server. Exit."
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

  global COM_Path
  COM_Exists = 0

  if en_Emulation == 1:
    COM_Path = "/Emulation"
    ser = 1
    return ser

  for x in range(3):
    if(os.path.exists(COM_Path + str(x))):
       COM_Path = COM_Path + str(x)
       COM_Exists = 1

  if (not COM_Exists):
    return

  ser = serial.Serial(
    port=COM_Path,
    baudrate = 9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1)
  return ser

#-----------------------------
# Read from Serial Port
#-----------------------------
def Read_Serial(ser):
  DHT_read = ""

  if en_Emulation == 1:
    DHT_read = "H:" + str(random.randint(20,40)) + "%, T:" + str(random.randint(40,70)) + "C"
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
  global en_Emulation
  
  str_ScriptName = argv[0]
  if len(argv) < 2: return
  if argv[1].lower() == 'emulation':
    en_Emulation =1
  else:
    print "Error: Parameter not found: " + argv[1];
    exit(1)
  
#-----------------------------
# Main
#-----------------------------
def main(argv):
  global ser, db

  pase_argv(argv)
  
  # Setup serial port
  ser = Setup_Serial()
  if ser is None:
    if(not en_SlientMode): print "Error: Can Not Find COM Port."
    exit(1)

  # Initi DHT table on SQL server
  cursor = db.cursor()
  cursor.execute("Truncate table dht")
  db.commit()

  signal.signal(signal.SIGINT, signal_handler)

  # Read from Serial Port and insert to SQL server
  while 1:
    DHT_read = Read_Serial(ser).strip()
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
