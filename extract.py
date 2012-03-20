import csv
import cPickle

city = csv.reader(open('cities15000.txt', 'rb'), dialect='excel-tab')

database = dict()

for entry in city:
  name = entry[2].lower()
  latitude = entry[4]
  longitude = entry[5]
  database[ name ] = (latitude, longitude)
print len(database)
save_file = open('database.txt', 'w')
cPickle.dump(database, save_file)
