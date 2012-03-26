import cPickle

file_cities = open('cities.txt', 'r')
file_countries = open('countries.txt', 'r')
cities = cPickle.load(file_cities)
countries = cPickle.load(file_countries)
