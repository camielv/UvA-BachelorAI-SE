import csv
import cPickle

city = csv.reader(open('countries.csv', 'rb'), delimiter=',')

database = dict()

for entry in city:
  name = entry[1].lower()
  database[ name ] = True
print len(database)
print database
save_file = open('countries.txt', 'w')
cPickle.dump(database, save_file)
