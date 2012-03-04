# whoosh imports
###############################################
from whoosh.index import create_in
from whoosh.index import open_dir
from whoosh.fields import *
from whoosh.qparser import QueryParser
from whoosh import qparser
from whoosh.scoring import WeightingModel
from whoosh.scoring import Weighting
from whoosh.scoring import PL2
from whoosh.scoring import BM25F

# tornado imports
##############################################
import tornado.httpserver
import tornado.ioloop
import tornado.web


# other imports
###############################################
import re
from math import sqrt
from math import log
import matplotlib
matplotlib.use('Agg')

# program constants
###############################################
indexdir='index'
webdir='web'
search_file = webdir + '/search.html'


# This is the cosine implementation from whoosh 0.3
###############################################
class Cosine(Weighting):
    """A cosine vector-space scoring algorithm, translated into Python
    from Terrier's Java implementation.
    """

    def score(self, searcher, fieldnum, text, docnum, weight, QTF=1):
        idf = searcher.idf(fieldnum, text)

        DTW = (1.0 + log(weight)) * idf
        QMF = 1.0 # TODO: Fix this
        QTW = ((0.5 + (0.5 * QTF / QMF))) * idf
        return DTW * QTW



# opening the index
###############################################
index = open_dir(indexdir)

# instantiating three searcher objects
###############################################
searcher_bm25f = index.searcher(weighting=BM25F)
searcher_pl2 = index.searcher(weighting=PL2)
searcher_cosine = index.searcher(weighting=Cosine)

# reader 
###############################################
reader = index.reader()

# parsers
###############################################
parser_content = qparser.QueryParser("content")
parser_title = qparser.QueryParser("title")
parser = qparser.MultifieldParser(['content', 'title'])

# tornado request handlers
###############################################
class MainHandler(tornado.web.RequestHandler):
    def get(self):
        # read the html file on every request - very inefficient
        f = open(search_file, 'r')
        lines = f.readlines()
        for l in lines:
          self.write(l) 
        #self.write("You requested the main page")

class SearchHandler(tornado.web.RequestHandler):
    def get(self, story_id):
        self.write("You requested the story " + story_id)

# tornado web application
###############################################
application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/", SearchHandler),
])

# tornado http server
# you still have to do:
# http_server.listen(<some port number>)
# tornado.ioloop.IOLoop.instance().start()
###############################################
http_server = tornado.httpserver.HTTPServer(application)

# method to start the server on a specified port
###############################################
def start_server(port):
  http_server.listen(port)
  tornado.ioloop.IOLoop.instance().start()


# utility methods
###############################################

def display(generator):
  for i in generator:
    print i

def get_term_freq_query(query):
   terms = re.split("\s", query)
   term_freq ={}
   for t in terms:
     if t in term_freq:
       term_freq[t] += 1
     else:
       term_freq[t] = 1
   return term_freq
 
def get_term_freq_doc(docid):
   docnum = searcher.document_number(id=docid)
   freq_generator = searcher.vector_as("frequency", docnum, "content")
   term_freq = {}
   for t in freq_generator:
     term_freq[t[0]] = t[1]
   return term_freq

def get_term_freq_col():
   lexicon  = reader.lexicon('content')
   term_freq = {}
   for l in lexicon:
     freq = reader.doc_frequency('content', l)
     term_freq[l] = freq
   return term_freq   

# Cosine similarity between a document and a query
def compute_cosine(docid, query):
   term_freq_query = get_term_freq_query(query)
   term_freq_doc = get_term_freq_doc(docid) 
   return _cosine(term_freq_query, term_freq_doc)  

def _cosine(x, y):
  # always compare the longest document against the shortest
    if len(x) < len(y):
      a = x
      x = y
      y = a
      del a
    xsum  = sum([k*k for k in x.values()])
    ysum  = sum([k*k for k in y.values()])  
    score = 0
    for word in x.iterkeys():
      if word not in y: 
        continue
      score += x[word]*y[word]
    score = score / sqrt(xsum*ysum)
        
    print "cosine similarity: %.2f" % score
    return score
  
