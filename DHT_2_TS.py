import MySQLdb
import os
import sys
import signal
import urllib, json
from TSPwd import TS_Write_API_Key, TS_Read_API_Key
from MySQLPwd import MySQLID, MySQLpassword
import time

en_Debug = 0
en_SlientMode = 0
en_Emulation = 0
en_Service = 0
cnt_Sensor = 0

db = None
#-----------------------------
# Handler for Ctrl-C
#-----------------------------
def signal_handler(signal, frame):
  global db

  db.commit()
  if(not en_SlientMode): print('Bye!')
  exit(0)

#-----------------------------
# Connect to MySQL
#-----------------------------
def connect_db():
  global db, en_Service
  
  if db != None: return db
  
  while 1:
    try:
      db = MySQLdb.connect(host = "localhost", user=MySQLID, passwd=MySQLpassword, db="dht")
      if(not en_SlientMode): print("MySQL: OK")
      return db
      break
    except Exception, e:
      if en_Service == 1:
        time.sleep(5)
        continue
      print str(e)
      print "Error: Can Not Connect to SQL Server. Exit."
      exit(1)

#-----------------------------
# Pase Parament
#-----------------------------
def pase_argv(argv):
  global en_Emulation, en_SlientMode, en_Service
  
  str_ScriptName = argv[0]
  if len(argv) < 2: return
  if argv[1].lower() == 'emulation':
    en_Emulation =1
  elif argv[1].lower() == 'service':
    en_SlientMode = 1
    en_Service = 1
  else:
    print "Error: Parameter not found: " + argv[1];
    exit(1)

#-----------------------------
# URL for Update Channel Feed
#-----------------------------
def TS_Update_Channel_Feed(API_Key, Fields, DateTime):
  global en_Debug, cnt_Sensor
  
  str_URL = 'https://api.thingspeak.com/update.json?api_key=' + API_Key
  if en_Debug: print(Fields)
  rows = Fields.split(',')
  field_index = 0
  for row in rows:
    field_index+=1
    if (row != '--') and (field_index <= cnt_Sensor*2):
      str_URL = str_URL + '&field' + str(field_index) + '=' + row
  str_URL = str_URL + '&created_at=' + str(DateTime) + '&timezone=Asia/Taipei'
  return str_URL

#-----------------------------
# Update Sensor Count
#-----------------------------
def Update_Sensor_Count():
  global db, cnt_Sensor

  cursor = db.cursor()
  cursor.execute("select Value from sysinfo where Name='SensorCount'")
  row = cursor.fetchone()
  cnt_Sensor = int(row[0])

#-----------------------------
# Main
#-----------------------------
def main(argv):
  global cnt_Sensor, en_Debug
  
  pase_argv(argv)
  db = connect_db()
  signal.signal(signal.SIGINT, signal_handler)

  # Initi DHT table on SQL server
  cursor = db.cursor()
  cursor_update = db.cursor()

  Update_Sensor_Count()
  if(not en_SlientMode): print "Sensor Count: " + str(cnt_Sensor)

  while 1:
    cursor.execute("select * from dht order by ID desc limit 1")
    row = cursor.fetchone()
    while row != None:
      if row[4] != 0:
        row = cursor.fetchone()
        continue
      
      TS_URL = TS_Update_Channel_Feed(TS_Write_API_Key, row[1], row[2])
      if en_Debug: print TS_URL
      try:
        response = urllib.urlopen(TS_URL)
        data = json.loads(response.read())
        if data == 0:
          if(not en_SlientMode): print 'Error: Can not update channel feed. ID=' + str(row[0])
        else:
          if en_Debug: print data['entry_id']
          cursor_update.execute('update dht set TS_Flag=' + str(data['entry_id']) + ' where ID=' + str(row[0]))
          if(not en_SlientMode): print('Updated field ID: ' + str(row[0]))
        row = cursor.fetchone()
      except Exception as e:
        if(not en_SlientMode): print('Failed to update field ID: ' + str(row[0]))
    time.sleep(15)

if __name__ == "__main__":
    main(sys.argv[0:])
