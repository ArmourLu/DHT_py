import time
from datetime import datetime
import serial
import os
import sys
import MySQLdb
from MySQLPwd import MySQLID, MySQLpassword
import signal


en_Debug = 0
COM_Path = '/dev/ttyUSB'
add_DHT_Reading = "insert into dht (Reading, DateTime) values (%s,%s)"
ser = None

try:
  db = MySQLdb.connect(host = "localhost", user=MySQLID, passwd=MySQLpassword, db="dht")
except Exception, e:
  print "Error: Can Not Connect to SQL Server. Exit."
  exit(1)


#-----------------------------
# Handler for Ctrl-C
#-----------------------------
def signal_handler(signal, frame):
  global ser, db

  ser.close()
  db.commit()
  print('Bye!')
  exit(0)
        
#-----------------------------
# Setup Serial Port
#-----------------------------
def Setup_Serial():

  global COM_Path
  COM_Exists = 0
  
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
  try:
    if(ser.inWaiting()>0):
      DHT_read=ser.readline()
  except Exception, e:
    return ""
  return DHT_read

#-----------------------------
# Main
#-----------------------------
if __name__ == '__main__':

  # Setup serial port
  ser = Setup_Serial()
  if ser is None:
    print "Error: Can Not Find COM Port."
    exit(1)

  # Initi DHT table on SQL server
  cursor = db.cursor()
  cursor.execute("Truncate table dht")
  db.commit()

  signal.signal(signal.SIGINT, signal_handler)

  # Read from Serial Port and insert to SQL server
  while 1:
    DHT_read = Read_Serial(ser)
    if(DHT_read != ""):
      time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
      os.system("clear")
      print "Reading from " + COM_Path + "..."
      print(DHT_read),
      print time_str
      print ""
      print("Press Ctrl-C to Exit...")
      data_DHT_Reading = (DHT_read,time_str)
      if(en_Debug):
        print add_DHT_Reading
        print data_DHT_Reading
      cursor.execute(add_DHT_Reading,data_DHT_Reading)
      db.commit()
    time.sleep(0.1)
