"""
Parses TREC-format articles from NYT Corpus
and indexes them using Whoosh. 

author: Manos Tsagkias <e.tsagkias@uva.nl>
date: 30 January 2010
"""

import sys, getopt, glob, re, codecs
from os import path

from whoosh.index import create_in, exists_in
from whoosh.fields import *
from whoosh.filedb.filewriting import NO_MERGE
from whoosh.analysis import StandardAnalyzer, StemmingAnalyzer
from whoosh.formats import Frequency

def usage():
    print """
    Parser for New York Times Corpus by LDC
    by Manos Tsagkias <e.tsagkias@uva.nl>
    
    Usage summary:
      -h          print usage summary
      -w <DIR>    TREC-format files of NYT Corpus
      -i <DIR>    Whoosh index directory
      -r          Stopwords file. 
                  Stop words should be in one line, space separated.
      -s          Enable stemming
    """


def ensure_unicode(_str):
    data = _str
    
    enc_candidates = ['ascii', 'latin1']
    for best_enc in enc_candidates:
      try:
        data = data.encode(best_enc)
      except:
        pass
      else:
        break # best encoding found, exit the loop
        
    # print 'Encoding: ',best_enc
    
    try:
      # if input resembled (best_enc) 
      # to latin1 but it was utf-8
      # it will break here
      data = unicode(data, 'utf-8')
    except:
      # re-encode the original input
      # as utf-8
      data = _str.encode('utf-8')
      data = unicode(data, 'utf-8')
    else:
      pass # all good, do nothing
    
    # return the dat ain Unicode
    return data


# regular expressions
rdoc        = re.compile(r"<DOC>(.+?)</DOC>", re.MULTILINE | re.IGNORECASE | re.DOTALL)
rdocid      = re.compile(r"<DOCID>(.+?)</DOCID>", re.DOTALL | re.IGNORECASE)
rdate       = re.compile(r"<DATE>(.+?)</DATE>", re.DOTALL | re.IGNORECASE)
rcategories = re.compile(r"<CATEGORIES>(.+?)</CATEGORIES>", re.DOTALL | re.IGNORECASE)
rtaxonomy   = re.compile(r"<TAXONOMY>(.+?)</TAXONOMY>", re.DOTALL | re.IGNORECASE)
rtitle      = re.compile(r"<TITLE>(.+?)</TITLE>", re.DOTALL | re.MULTILINE  | re.IGNORECASE)
rcontent    = re.compile(r"<CONTENT>(.+?)</CONTENT>", re.DOTALL | re.MULTILINE  | re.IGNORECASE)
rpath       = re.compile(r"<PATH>(.+?)</PATH>", re.DOTALL | re.MULTILINE  | re.IGNORECASE)


def nyt_index(workdir, indexdir, _min_size, _rem_stopwords, _enable_stemming):
    # Setup WHOOSH index
    # Quick introduction to WHOOSH: 
    # http://packages.python.org/Whoosh/quickstart.html
    
    if exists_in(indexdir):
        print "A Whoosh index already exists in dir %s. Continuing will destroy the index. Please remove first and try again." % indexdir
        return
    
    if _enable_stemming:
        my_analyzer = StemmingAnalyzer(stoplist = _rem_stopwords, minsize = _min_size)
    else:
        my_analyzer = StandardAnalyzer(stoplist = _rem_stopwords, minsize = _min_size)
        
    schema = Schema(id=ID(stored=True), path=ID(stored=True), pubdate=ID(stored=True), descriptors=KEYWORD, taxonomy=KEYWORD, title=TEXT(stored=True,analyzer=my_analyzer, vector=Frequency(my_analyzer)), content=TEXT(analyzer=my_analyzer, vector=Frequency(my_analyzer)))
    ix     = create_in(indexdir, schema)
    writer = ix.writer()
    
    for nyt_year in glob.iglob(workdir+"/[0-9]*"):
        print nyt_year
        if not path.isfile(nyt_year): continue
        
        # read the entire file in memory
        # approx 800MB
        f = codecs.open(nyt_year, 'r', 'utf-8')
        fc = f.read()
        f.close()
        
        for match in rdoc.finditer(fc):
            article = match.group(1)
            
            docid = rdocid.search(article).group(1)
            print docid
            docdate = rdate.search(article).group(1)
            docpath = rpath.search(article).group(1)
            
            docategories = u''
            if rcategories.search(article):
                docategories = rcategories.search(article).group(1)
                
            doctaxonomy = u''
            if rtaxonomy.search(article):
                doctaxonomy = rtaxonomy.search(article).group(1)
                
            doctitle = u''
            if rtitle.search(article):
                doctitle = rtitle.search(article).group(1)
                
            doccontent = u''
            if rcontent.search(article):
                doccontent = rcontent.search(article).group(1)
            
            """ Index the article """
            writer.add_document(id=docid, path=docpath, pubdate=docdate, descriptors=docategories, taxonomy=doctaxonomy, title=doctitle, content=doccontent)
            
    writer.commit(NO_MERGE)
    


def main(argv):
    """ Initialization """
    workdir = ''
    indexdir = ''
    fstopwords = ''
    enable_stemming = False
    min_size = 2
    stopwords = None
    
    
    try:
        opts, args = getopt.getopt(argv, "hw:i:r:sm:")
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    
    
    for opt, arg in opts:
        if opt == "-h":
            usage()
            sys.exit()
        elif opt == "-w":
            workdir = arg
        elif opt == "-i":
            indexdir = arg
        elif opt == "-r":
            fstopwords = arg
        elif opt == "-s":
            enable_stemming = True
    # iterate over the directories
    
    if workdir == '' or indexdir == '':
        usage()
        sys.exit(2)
    
    # check if the working directory exists
    if not path.isdir(workdir):
        print "*** ERROR: working dir doesn't exist; was set to:"
        print "           %s" % workdir
        sys.exit(2)
      
    # check if the output directory exists
    if not path.isdir(indexdir):
        print "*** ERROR: index dir doesn't exist; was set to:"
        print "           %s" % indexdir
        sys.exit(2)
        
    # check if stopwords list file exists
    if fstopwords and not path.exists(fstopwords):
        print "*** ERROR: stopwords file doesn't exist; was set to:"
        print "           %s" % fstopwords
        sys.exit(2)
    
    # Give out information of what will happen
    print 'Starting ...'
    print '  working dir: %s' % workdir
    print '  index  dir: %s' % indexdir
    print   
    
    if fstopwords:
        fhstopwords = codecs.open(fstopwords, 'r', 'utf-8')
        stopwords = fhstopwords.read().split(' ')
        fhstopwords.close()
        
        print '  stopwords: %d from %s' % (len(stopwords), fstopwords)
    
    """ Read in the files and index them """
    nyt_index(workdir, indexdir, min_size, stopwords, enable_stemming)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
