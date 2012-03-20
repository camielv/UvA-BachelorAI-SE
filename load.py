# whoosh imports
import urllib2
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
from whoosh.scoring import TF_IDF
from whoosh.scoring import Frequency

# tornado imports
##############################################
import tornado.httpserver
import tornado.ioloop
import tornado.web


# other imports
###############################################
import re
import os
import os.path
import shutil
import time
import random
import subprocess
from math import sqrt
from math import log
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt 
import pylab  
from xml.dom import minidom
import datetime
import nltk
import operator

# program constants
###############################################
indexdir='index'
webdir='web'
header_file = webdir + '/header.html'
search_file = webdir + '/index.html'
footer_file = webdir + '/footer.html'
working_dir = os.environ["PWD"]


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


# Create the index
###############################################
def create_index(dir=indexdir, stemming=True, stopwords=None):
  if os.path.exists(dir):
    shutil.rmtree(dir)
  os.mkdir(dir)
  res = -1
  if stemming:
    if stopwords == None:
      res= subprocess.call(["python", "tools/scripts/preprocessing/whoosh_index.py", "-i", dir, "-w", "data/aggregated", "-s"])
    else: 
      res= subprocess.call(["python", "tools/scripts/preprocessing/whoosh_index.py", "-i", dir, "-w", "data/aggregated", "-s", "-r", stopwords])
  else:
    if stopwords == None:
      res= subprocess.call(["python", "tools/scripts/preprocessing/whoosh_index.py", "-i", dir, "-w", "data/aggregated"])
    else:
      res= subprocess.call(["python", "tools/scripts/preprocessing/whoosh_index.py", "-i", dir, "-w", "data/aggregated", "-r", stopwords])
     
  if (res != 0):
    raise Exception("Problem creating index!")


# opening the index
###############################################
index = open_dir(indexdir)

# instantiating three searcher objects
###############################################
searcher_bm25f = index.searcher(weighting=BM25F)
searcher_pl2 = index.searcher(weighting=PL2)
searcher_cosine = index.searcher(weighting=Cosine)
searcher_tf_idf = index.searcher(weighting=TF_IDF)
searcher_frequency = index.searcher(weighting=Frequency)

# reader 
###############################################
reader = index.reader()

# parsers
###############################################
parser_content = qparser.QueryParser("content")
parser_title = qparser.QueryParser("title")
parser = qparser.MultifieldParser(['content', 'title'])

# Website parts
html_header = open(header_file, 'r').readlines()
html_search = open(search_file, 'r').readlines()
html_footer = open(footer_file, 'r').readlines()

# tornado request handlers
###############################################
class MainHandler(tornado.web.RequestHandler):
    def get(self):
        # Read the html file on every request.
        lines = list()
        lines.extend(html_header)
        lines.append("<div class=\"center\">")
        lines.extend(html_search)
        lines.append("</div>")
        lines.extend(html_footer)

        # Write index file
        for l in lines:
          self.write(l) 


class CloudDisplayer(tornado.web.RequestHandler):
    def get(self):
        docid = self.get_argument("docid")
        res = application.searcher_bm25f.find("id", unicode(docid))
        path = get_relative_path(res[0]['path'])
        docnum = int(res[0].docnum)

        dom = minidom.parse(path)
        blocks = dom.getElementsByTagName('block')
        article = ""
        for block in blocks:
          if(block.hasAttribute('class') and (block.getAttribute('class') == 'full_text')):
            for i in range(len(block.childNodes)):
              article += block.childNodes[i].toxml()

        article = nltk.clean_html(article)
        article = strip_non_ascii(article)
        article = nltk.Text((word for word in re.findall(r"(?u)\w+", article.lower()) if word not in set(nltk.corpus.stopwords.words("english"))))

        key_terms = nltk.FreqDist(article)
        key_terms = [(word, freq) for (word, freq) in key_terms.items() if freq > 0]

        tf_idf_terms = list()
	for i in range(len(key_terms)):
          (term, freq) = key_terms[i]
          score = application.searcher_bm25f.idf("content", term)
          tf_idf_terms.append( (term, freq * score) )

        tf_idf_terms = sorted( tf_idf_terms, key=operator.itemgetter(1), reverse=True )
	print tf_idf_terms

        top_terms = "" 
        for i in range(10):
          (term, score) = tf_idf_terms[i]
          top_terms += (term + " ") * int(round(score * 10))

        lines = html_header
        for l in lines:
          self.write(l)
        
        self.write("<a href=\"/display?docid=" + docid + "\">Back to document</a><br /><br />")
        
        applet = "<applet name=\"wordle\" codebase=\"http://wordle.appspot.com\" mayscript=\"mayscript\" code=\"wordle.WordleApplet.class\" archive=\"/j/v1356/wordle.jar\" width=\"100%\" height=\"400\"><param name=\"text\" value=\"" + top_terms + "\"><param name=\"java_arguments\" value=\"-Xmx256m -Xms64m\"></applet>"
        self.write(applet)

        lines = html_footer
        for l in lines:
          self.write(l)

'''
class CloudDisplayer(tornado.web.RequestHandler):
    def get(self):
        docid = self.get_argument("docid")
        res = application.searcher_bm25f.find("id", unicode(docid))
        path = get_relative_path(res[0]['path'])
        docnum = int(res[0].docnum)

        keywords_and_scores = application.searcher_bm25f.key_terms([docnum], "content", numterms=10)
        keylijst = []
        for i in range(len(keywords_and_scores)):
          keylijst.append(keywords_and_scores[i][0])
          print application.searcher_bm25f.idf("content",keywords_and_scores[i][0]), keywords_and_scores[i][0]
   
        print keywords_and_scores
        print keylijst

        keystringlijst = " ".join(keylijst)
        print keystringlijst

        keytermint = []
        for i in range(len(keywords_and_scores)):
          keytermint.append(keywords_and_scores[i][:1] + (int(keywords_and_scores[i][1]*1000),))
        cloud, cloudlink = generate_term_cloud(keytermint, len(keytermint))

        # Generate page
        lines = html_header
        for l in lines:
          self.write(l)

        frame = "<h1>Word Cloud</h1><iframe src=\"" + cloudlink + "\"></iframe>"
        self.write(frame)

        lines = html_footer
        for l in lines:
          self.write(l)
'''

class SearchHandler(tornado.web.RequestHandler):
    def get(self):
        query = self.get_argument("query")
        scoring = self.get_argument("scoring")
        field = self.get_argument("field")
        page = self.get_arguments("page")
        searcher = None
        if scoring == "Cosine":
          searcher = application.searcher_cosine
        elif scoring == "PL2":
          searcher = application.searcher_pl2
        elif scoring == "BM25F":
          searcher = application.searcher_bm25f
        elif scoring == "TF_IDF":
          searcher = application.searcher_tf_idf
        elif scoring == "Frequency":
          searcher = application.searcher_frequency
        else:
          searcher = application.searcher_bm25f

        # Generate page
        lines = html_header
        for l in lines:
          self.write(l)
        self.write("<h1>Results</h1><p>")
        
        res = searcher.find(field, unicode(query), limit = 100000)

        self.write("Query: " + query)
        self.write(" <a href=\"/trend?query=" + query + "\">(Trend of query)</a>")
        self.write("<br />")
        self.write("Scoring: " + scoring)
        self.write("<br />")
        self.write("Field: " + field)
        self.write("<br /> <br />")
        self.write("Number of hits:  " + str(len(res)) + "<br /></p>")

        # Generate subpages
        try:
          page = int(page[0])
        except:
          page = 0

        pages = len(res) / 10
        if (len(res) % 10 == 0 and pages > 0):
          pages -= 1
        if (page > pages):
          page = pages
        if (page < 0):
          page = 0
        if (page == pages):
          res = res[page*10:]
        else:
          res = res[page*10:(page+1)*10]

        for r in res:
          nextid = str(r['id'])
          nexttitle = r['title']
          path = get_relative_path(r['path'])
          self.write("<p><a href=/display?docid=" + nextid + ">"+ nexttitle +"</a><br />")

          dom = minidom.parse(path)
          blocks = dom.getElementsByTagName('block')
          for block in blocks:
            if(block.hasAttribute('class') and (block.getAttribute('class') == 'online_lead_paragraph')):
              for i in range(len(block.childNodes)):
                self.write(block.childNodes[i].toxml())
          self.write('</p>')

        self.write('<h3>More results</h3><p>')

        for i in range(pages+1):
          if (i == page):
            self.write(' ' + str(i) + ' ')
          else :
            link = " <a href=\"/search?query=" + query + "&field=" + field + "&scoring=" + scoring + "&page="
            self.write(link + str(i) + '">' + str(i) + '</a> ')

        self.write('</p>')
        lines = html_footer
        for l in lines:
          self.write(l)

class DocumentDisplayer(tornado.web.RequestHandler):
    def get(self):
      docid=self.get_argument("docid")
      res = application.searcher_bm25f.find("id", unicode(docid))
      path = get_relative_path(res[0]['path'])
      title = get_relative_path(res[0]['title'])
      docnum = int(res[0].docnum)

      keywords_and_scores = application.searcher_bm25f.key_terms([docnum], "content", numterms=10)

      keylijst = []
      count = 0
      for i in range(len(keywords_and_scores)):
        keylijst.append(keywords_and_scores[i][0])
        count += 1
        if( count == 2 ):
          count = 0
          keystringlijst = " ".join(keylijst)
          keylijst = list()
          res = application.searcher_bm25f.find("content", keystringlijst, limit=int(11))
          if( len(res) > 1 ):
            break

      # Generate page
      lines = html_header
      for l in lines:
        self.write(l)

      self.write("<h1>" + title + "</h1>")
      self.write("<p><a href=\"/cloud?docid=" + docid + "\">Generate Cloud</a></p><h2>Relevant Articles</h2><p>")

      for r in res:
        res_id = r['id']
        if (res_id == docid):
          continue
        res_path = get_relative_path(r['path'])
        res_title = r['title']
        self.write("<p><a href=/display?docid=" + res_id + ">"+ res_title +"</a><br />")

        dom = minidom.parse(res_path)
        blocks = dom.getElementsByTagName('block')
        for block in blocks:
          if(block.hasAttribute('class') and (block.getAttribute('class') == 'online_lead_paragraph')):
            for i in range(len(block.childNodes)):
              self.write(block.childNodes[i].toxml())
        self.write('</p>')

      self.write("</p><h2>Article</h2><p>")

      # Print Article 
      dom = minidom.parse(path)
      blocks = dom.getElementsByTagName('block')
      for block in blocks:
        if(block.hasAttribute('class') and (block.getAttribute('class') == 'full_text')):
          for i in range(len(block.childNodes)):
            self.write(block.childNodes[i].toxml())

      lines = html_footer
      for l in lines:
        self.write(l)

class TrendDisplayer(tornado.web.RequestHandler):
    def get(self):
      query = self.get_argument("query", default=" ")

      res = application.searcher_bm25f.find("content", unicode(query), limit=100000)

      trend = dict()

      for r in res:
        path = get_relative_path(r['path'])
        dom = minidom.parse(path)
        metas = dom.getElementsByTagName('meta')
        day = 0
        month = 0
        year = 0
        for meta in metas:
          if(meta.hasAttribute('name') and (meta.getAttribute('name') == 'publication_day_of_month') and meta.hasAttribute('content')):
            day = int(meta.getAttribute('content'))
          elif(meta.hasAttribute('name') and (meta.getAttribute('name') == 'publication_month') and meta.hasAttribute('content')):
            month = int(meta.getAttribute('content'))
          elif(meta.hasAttribute('name') and (meta.getAttribute('name') == 'publication_year') and meta.hasAttribute('content')):
            year = int(meta.getAttribute('content'))
          else:
            pass

        key = datetime.date(year, month, day)
        if(trend.has_key(key)):
          trend[key] += 1
        else:
          trend[key] = 1

      # Generate Page
      lines = html_header
      for l in lines:
        self.write(l)

      self.write("<a href=\"/display?docid=" + docid + "\">Back to document</a><br /><br />")

      self.write('<div id=\"header\"><img src=\"' + plot_trend_word(trend, query) + " width=\"600\" height=\"250\"  /></div>")

      lines = html_footer
      for l in lines:
        self.write(l)
class LexiconDisplayer(tornado.web.RequestHandler):
    def get(self):
      self.post()
    def post(self):
      field = self.get_argument("field", default="title")
      sort_by = self.get_argument("sort_by", default="term")
      lex = application.reader.lexicon(field)
      list_terms = []
      for l in lex:
        list_terms.append((l,
           application.reader.doc_frequency("title", l), 
           application.reader.doc_frequency("content", l)))
      self.write("<h2>") 
      srtd=list_terms
      if (sort_by == "frequency_title"):
         srtd = sorted(list_terms, key = lambda x:x[1], reverse=True)
         self.write("<a href="+generate_term_cloud([(x[0], x[1]) for x in srtd], 150) + "> Tag cloud for the top 50 entries in the table - if it doesn't load immediately just spam \"refresh \" </a><br />")
         self.write("<a href="+ plot([x[1] for x in srtd])+ "> Term distribution plot. </a><br />")
      elif (sort_by == "frequency_content"):
         srtd = sorted(list_terms, key = lambda x:x[2], reverse=True)  
         self.write("<a href="+generate_term_cloud([(x[0], x[2]/100) for x in srtd], 150) + "> Tag cloud for the top 50 entries in the table - takes several seconds, just spam \"refresh \" </a><br />")
         self.write("<a href="+ plot([x[2] for x in srtd])+ "> Term distribution plot. </a><br />")
      else:
         self.write("<a href="+ plot([x[2] for x in list_terms])+ "> Term distribution plot. </a>")
       

      self.write("</h2>")
      self.write("<table border = \"1\">")
      self.write("<tr>")
      self.write("<td> # </td>")
      self.write("<td> <a href=/lexdisplay?field="+field+"&sort_by=term> Term </a> </td>")
      self.write("<td> <a href=/lexdisplay?field="+field+"&sort_by=frequency_title> frequency in field \"title\" </a> </td>")
      self.write("<td> <a href=/lexdisplay?field="+field+"&sort_by=frequency_content> frequency in field \"content\" </a> </td>")
      self.write("</tr>")
      
      for i in range(0, len(list_terms)):
        self.write("<tr>")
        self.write("<td>" + str(i) + " </td>")
        self.write("<td><a href=/termstat?term=" + srtd[i][0] + ">"+ srtd[i][0] +"</a></td>")
        self.write("<td>"+ str(srtd[i][1]) +"</td>")
        self.write("<td>"+ str(srtd[i][2]) +"</td>")
        self.write("</tr>")

class TermStatisticsDisplayer(tornado.web.RequestHandler):
    def get(self):
      term = self.get_argument("term")
      freq_cont = application.reader.doc_frequency("content", term)
      freq_titl = application.reader.doc_frequency("title", term)
      cont = application.searcher_frequency.find("content", term, limit=max(freq_cont, 1))
      titl = application.searcher_frequency.find("title", term, limit=max(freq_titl,1))

      self.write("<h1>" + term + "</h1><br />")      
      self.write("Frequency in titles: " + str(freq_titl) + "<br />")
      for t in titl:
        nextid = str(t['id'])
        nexttitle = t['title']
        self.write("<a href=/display?docid=" + nextid + ">"+ nexttitle +"</a><br />")
      self.write("<br />Frequency in content: " + str(freq_cont) +"<br />" )    
      for c in cont:
        nextid = str(c['id'])
        nexttitle = c['title']
        self.write("<a href=/display?docid=" + nextid + ">"+ nexttitle +"</a><br />")

class Closer(tornado.web.RequestHandler):
    def get(self):
      close_resources(application)

class Indexer(tornado.web.RequestHandler):
    def post(self):
      tempfile = "tempfilestop"
      f = open(tempfile, 'w')
      sw = self.get_argument("stopwords", default=" ")
      words = re.split("\s", sw)
      for i in range(0, len(words)):
        f.write(words[i] + " ")
      f.close()
      close_resources(application)
      shutil.rmtree(indexdir) 
      if(self.get_argument("stemming") == "yes"):
        create_index(application.indexdir, stemming=True, stopwords=tempfile)
      else:     
        create_index(application.indexdir, stemming=False, stopwords=tempfile)
      os.remove(tempfile)
 
      application.index = open_dir(application.indexdir)

      # instantiating three searcher objects
      ###############################################
      application.searcher_bm25f = application.index.searcher(weighting=BM25F)
      application.searcher_pl2 = application.index.searcher(weighting=PL2)
      application.searcher_cosine = application.index.searcher(weighting=Cosine)
      application.searcher_tf_idf = application.index.searcher(weighting=TF_IDF)
      application.searcher_frequency = application.index.searcher(weighting=Frequency)

      # reader 
      ###############################################
      application.reader = application.index.reader()

      # parsers
      ###############################################
      application.parser_content = qparser.QueryParser("content")
      application.parser_title = qparser.QueryParser("title")
      application.parser = qparser.MultifieldParser(['content', 'title'])

     
      self.write("<h1>Indexed!</h1>")

class ZipfPlotter(tornado.web.RequestHandler):
    def get(self):
      pass        
# tornado web application
###############################################
#settings = {"static_path" : "/home/bkovach1/nytimes_corpus/web"}
settings = {"static_path" : webdir}
application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/search", SearchHandler),
    (r"/cloud", CloudDisplayer),
    (r"/display", DocumentDisplayer),
    (r"/trend", TrendDisplayer),
    (r"/lexdisplay", LexiconDisplayer),
    (r"/close", Closer),
    (r"/index", Indexer),
    (r"/termstat", TermStatisticsDisplayer)
], **settings)
application.index = index
application.indexdir = indexdir
application.searcher_bm25f = searcher_bm25f
application.searcher_pl2 = searcher_pl2
application.searcher_cosine = searcher_cosine
application.searcher_tf_idf = searcher_tf_idf
application.searcher_frequency = searcher_frequency
application.reader = reader
application.parser_content = parser_content
application.parser_title = parser_title
application.parser = parser


# tornado http server
# you still have to do:
# http_server.listen(<some port number>)
# tornado.ioloop.IOLoop.instance().start()
###############################################
http_server = tornado.httpserver.HTTPServer(application)

# method to start the server on a specified port
###############################################
def start_server(port):
  http_server = tornado.httpserver.HTTPServer(application)
  http_server.listen(port)
  tornado.ioloop.IOLoop.instance().start()


# close resources
###############################################
def close_resources(application):
  application.index.close()
  application.reader.close()
  application.searcher_bm25f.close()
  application.searcher_pl2.close()
  application.searcher_cosine.close()
  application.searcher_tf_idf.close()
  application.searcher_frequency.close()


# utility methods
###############################################




#terms_list is a list of tuples. The first element of
#each tuple is a term. The second is a number (frequency.)
#return a link to a term cloud

def generate_term_cloud(terms_list, words):
  import fietstas_rest
  from fietstas_rest import Fietstas

  doc = ""
  terms = [x[0] for x in terms_list]
  weights = [x[1] for x in terms_list]  
  for i in range(0, min(words,len(terms))):
    for j in range(0, weights[i]):
      doc += (terms[i] + " ")
 
  f = Fietstas(key='0ce798c52985460e9b79dbb23812fc42') 
  doc_id = f.upload_document(document = doc)
  cloud_link, cloud = f.make_cloud(docs=doc_id, words = words, stopwords = 1)
  if cloud is None:
    # Cloud is not available yet: wait in a loop
    for i in range(10):
      time.sleep(2)
      cloud = f.get_cloud(cloud_link)
      if cloud is not None:
        break
  return cloud, cloud_link

# plots and returns a link to the plotted file
def plot(weights_list):
  plt.clf()
  #plt.plot(range(0, len(weights_list)), weights_list, 'ro')
  plt.loglog(range(0, len(weights_list)), weights_list, 'ro')
  plt.xlabel('Rank')
  plt.ylabel('Frequency')
  plt.savefig("web/plot.png")  
  return "/static/plot.png"

def plot_trend_word(trend, query):
  keys = trend.keys()
  keys.sort()
  values = list()
  for i in range(len(keys)):
    values.append(trend[keys[i]])

  figure = pylab.figure(figsize = (12,5))
  ax = figure.add_subplot(1, 1, 1)
  ax.bar(range(len(values)), values,align='center', log=False)
  ax.set_title("Word trend " + query)
  ax.set_ylabel("Frequency Results")
  ax.set_xlabel("Date")
  ax.set_xticks(range(len(values)))
  ax.set_xticklabels(keys)
  figure.autofmt_xdate()
  figure.savefig('web/trend.png')
  return "static/trend.png"

def get_relative_path(path):
  parts = re.split("\.\.\/", path)
  return parts[len(parts)-1]

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

def strip_non_ascii(string):
    ''' Returns the string without non ASCII characters'''
    stripped = (c for c in string if 0 < ord(c) < 127)
    return ''.join(stripped) 

start_server(29004)
