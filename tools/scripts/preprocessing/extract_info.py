#!/usr/bin/python

"""
Extracts 
  topics
  title
  lead
  body
  publication date
  guid
  
from the NYT corpus, found at:
/home/ilps/NYT

the script is based on the JAVA nytools
and the perl module: Text::Corpus::NewYorkTimes::Document

-----
Author: Manos Tsagkias <e.tsagkias@uva.nl>
Date:   21 Jan 2010
"""
import sys, getopt, glob, re, codecs
from os import path
from datetime import datetime as dt
from lxml import etree


def usage():
    print """
    Parser for New York Times Corpus by LDC
    by Manos Tsagkias <e.tsagkias@uva.nl>
    
    Usage summary:
      -h          print usage summary
      -i <DIR>    root directory for NYT corpus
      -o <DIR>    output directory
      -a          enable output of article<->topic associations 
                  used for DB import
      -d          generate a descriptor file
                  used to import descriptors in DB
      
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


"""
Parse NYT Corpus documents

The collection's directory structure is of the form:
YEAR/MONTH/DAY/article_id.xml

and one article per file
"""
def nyt_parse(workdir, outputdir, _generate_articleassociation, _generate_descriptors):
    # assign a timestamp for the current run
    run_timestamp = dt.today().strftime("%A, %d %B %Y %I:%M%p")
    
    # setup once the Xpath expressions
    # Article Body
    xpath_body = etree.XPath('/nitf/body/body.content/block[@class="full_text"]/p')
    
    # Descriptors
    xpath_categories = []
    # 2.2.3 biographic categories
    xpath_categories.append(etree.XPath('/nitf/head/docdata/identified-content/classifier[@class="indexing_service" and @type="biographical_categories"]'))
    # 2.2.15 descriptors
    xpath_categories.append(etree.XPath('/nitf/head/docdata/identified-content/classifier[@class="indexing_service" and @type="descriptor"]'))
    # 2.2.22 locations
    xpath_categories.append(etree.XPath('/nitf/head/docdata/identified-content/location[@class="indexing_service"]'))
    # 2.2.23 names
    xpath_categories.append(etree.XPath('/nitf/head/docdata/identified-content/classifier[@class="indexing_service" and @type="names"]'))
    # 2.2.34 organizations
    xpath_categories.append(etree.XPath('/nitf/head/docdata/identified-content/org[@class="indexing_service"]'))
    # 2.2.36 people
    xpath_categories.append(etree.XPath('/nitf/head/docdata/identified-content/person[@class="indexing_service"]'))
    # 2.2.45 titles
    xpath_categories.append(etree.XPath('/nitf/head/docdata/identified-content/object.title[@class="indexing_service"]'))
    
    # 2.2.17 general online descriptors
    xpath_categories.append(etree.XPath('/nitf/head/docdata/identified-content/classifier[@class="online_producer" and @type="general_descriptor"]'))
    # 2.2.26 online descriptors
    xpath_categories.append(etree.XPath('/nitf/head/docdata/identified-content/classifier[@class="online_producer" and @type="descriptor"]'))
    # 2.2.29 online locations
    xpath_categories.append(etree.XPath('/nitf/head/docdata/identified-content/location[@class="online_producer"]'))
    # 2.2.30 online organizations
    xpath_categories.append(etree.XPath('/nitf/head/docdata/identified-content/org[@class="online_producer"]'))
    # 2.2.31 online people
    xpath_categories.append(etree.XPath('/nitf/head/docdata/identified-content/person[@class="online_producer"]'))
    # 2.2.33 online titles
    xpath_categories.append(etree.XPath('/nitf/head/docdata/identified-content/object.title[@class="online_producer"]'))
    
    # Taxonomic classifiers
    xpath_taxonomy = etree.XPath('/nitf/head/docdata/identified-content/classifier[@class="online_producer" and @type="taxonomic_classifier"]')
    
    # Publication date
    xpath_pubdate              = etree.XPath('/nitf/head/pubdata/@date.publication')
    # Article Title
    xpath_title                = etree.XPath('/nitf/body[1]/body.head/hedline/hl1')
    # Article GUID
    xpath_guid                 = etree.XPath('/nitf/head/docdata/doc-id/@id-string')
    
    # Regular expression to remove LEAD from lead paragraph
    rlead = re.compile(r"^\s*LEAD\s*:*\s*", re.DOTALL | re.UNICODE | re.IGNORECASE)
    
    # Hold descriptor types for future use
    descriptors = {}
    
    
    # Open a file to store 
    # Topic <-> Article associations with publication date
    if _generate_articleassociation:
        fh_topics = codecs.open(path.join(outputdir, 'articles2topics.out'), 'w', 'utf-8')
        fh_topics.write('# generated by extract_info.py on %s\n' % run_timestamp)
        fh_topics.write('#\n')
        fh_topics.write('# Format:\n')
        fh_topics.write('# <DESCRIPTORS><TAB><TAXONOMY><TAB><ARTICLE_GUID><TAB><PUBDATE>\n')
        fh_topics.write('#\n')
        fh_topics.write('# <DESCRIPTORS> and <TAXONOMY> values are separated by semicolon (;)\n')
        fh_topics.write('# only articles with parsable dates are included\n')
    
    # iterate the working directory for files
    doc = []
    for nyt_month_dir in glob.iglob(path.join(workdir, "[0-9]*")):
        # print nyt_month_dir
        if not path.isdir(nyt_month_dir): continue
        df = codecs.open(path.join(outputdir, nyt_month_dir.split('/')[-1]), 'w', 'utf-8')

        for nyt_day_dir in glob.iglob(path.join(nyt_month_dir,"[0-9]*")):
            print 'Working on %s' % nyt_day_dir
            # print nyt_day_dir
            if not path.isdir(nyt_month_dir): continue
            for nyt_article in glob.iglob(path.join(nyt_day_dir, "[0-9]*.xml")):
                # print 'Working on %s' % nyt_article
                try:
                    f = etree.parse(nyt_article)
                except:
                    continue
                
                
                """"""
                """ ARTICLE BODY"""
                """"""
                i = 0
                bodytext = []
                leadParagraphReoccurs = False
                for i, node in enumerate(xpath_body(f)):
                    # print node.text.encode('utf-8')
                    if i == 0:
                        leadParagraph = rlead.sub('', node.text)
                        bodytext.append(leadParagraph)
                    
                    if leadParagraphReoccurs == False and rlead.search(node.text):
                        leadParagraphReoccurs = True
                        continue
                    
                    bodytext.append(node.text)
                bodytext = ensure_unicode('\n'.join(set(bodytext)))
                                        
                # print bodytext.encode('utf-8')[:255]
                
                
                """"""
                """ ARTICLE TITLE """
                """"""
                titletext = []
                for node in xpath_title(f):
                    titletext.append(node.text)
                titletext = ensure_unicode('\n'.join(set(titletext)))
                # print titletext.encode('utf-8')
                
                
                """"""
                """ PUBLICATION DATE """
                """"""
                datetext = ''
                for node in xpath_pubdate(f):
                    if re.match(r"[0-9]{8}T[0-9]{6}", node):
                        datetext = node
                        break
                datetext = ensure_unicode(datetext)
                # if datetext:
                #     print 'PUBLICATION DATE: %s' % datetext
                # else:
                #     print '*** NO DATE COULD BE DERIVED from: %s' % node.text
                
                
                """"""
                """ CATEGORIES """
                """"""
                categoriestext = []
                for i, xpath_descriptor in enumerate(xpath_categories):
                    for node in xpath_descriptor(f):
                        if not node.text: continue
                        
                        d = node.text.lower().replace('\n', '')
                            
                        if i < 7: 
                            add = 10
                        else: 
                            add = 43
                        descriptors[d] = add + i
                        categoriestext.append(d)
                categoriestext = ensure_unicode(';'.join(set(categoriestext)))
                # print 'TOPICS: %s' % categoriestext
                
                
                """"""
                """ TAXONOMY """
                """"""
                taxonomytext = []
                for node in xpath_taxonomy(f):
                    taxonomytext.append(node.text.replace('\n', ''))
                taxonomytext = ensure_unicode(';'.join(set(taxonomytext)))
                
                
                """"""
                """ ARTICLE GUID """
                """"""
                guidtext = xpath_guid(f)[0]
                
                
                """"""
                """ BUILD THE DOCUMENT TRECFORMAT """
                """"""
                doc = []
                doc.append("<DOC>\n")
                doc.append("<DOCID>%s</DOCID>\n" % guidtext)
                doc.append("<DATE>%s</DATE>\n" % datetext)
                doc.append("<PATH>%s</PATH>\n" % nyt_article)
                doc.append("<CATEGORIES>%s</CATEGORIES>\n" % categoriestext)
                doc.append("<TAXONOMY>%s</TAXONOMY>\n" % taxonomytext)
                doc.append("<TITLE>%s</TITLE>\n" % titletext)
                doc.append("<CONTENT>%s</CONTENT>\n" % bodytext)
                doc.append("</DOC>\n")
                
                df.writelines(doc)
                
                """ Update the topic<->article association """
                if datetext and _generate_articleassociation:
                    fh_topics.write('%s\t%s\t%s\t%s\n' % (categoriestext, taxonomytext, guidtext, datetext))
            # end of article loop
        # end of day loop
    # end of month loop
    df.close()

    if _generate_articleassociation:
        fh_topics.close()
    
    """ Store descriptors in file """
    if _generate_descriptors:
        fh_descriptor = codecs.open(path.join(outputdir,'descriptors.out'), 'w', 'utf-8')
        fh_descriptor.write('# generated by extract_info.py on %s\n' % run_timestamp)
        fh_descriptor.write('#\n')
        fh_descriptor.write('# Format:\n')
        fh_descriptor.write('# <DESCRIPTOR><TAB><TYPE_ID>\n')
        fh_descriptor.write('#\n')
        fh_descriptor.write('# Human descriptors:\n')
        fh_descriptor.write('# 10 -- Biographical categories\n')
        fh_descriptor.write('# 11 -- Descriptors\n')
        fh_descriptor.write('# 12 -- Locations\n')
        fh_descriptor.write('# 13 -- Names\n')
        fh_descriptor.write('# 14 -- Organizaations\n')
        fh_descriptor.write('# 15 -- People\n')
        fh_descriptor.write('# 16 -- Titles\n')
        fh_descriptor.write('#\n')
        fh_descriptor.write('# Co mputer generated descriptors:\n')
        fh_descriptor.write('# 50 -- General online descriptors\n')
        fh_descriptor.write('# 51 -- Online descriptors\n')
        fh_descriptor.write('# 52 -- Online locations\n')
        fh_descriptor.write('# 53 -- Online organizations\n')
        fh_descriptor.write('# 54 -- Online people\n')
        fh_descriptor.write('# 55 -- Online titles\n')
        fh_descriptor.write('# all descriptors are validated by humans\n')
    
        for k, v in descriptors.iteritems():
            fh_descriptor.write('%s\t%d\n' % (k, v))
        fh_descriptor.close()
# end of nyt_parse()


def main(argv):
    """ Initialization """
    workdir = ''
    outputdir = ''
    generate_articleassociationfile = False
    generate_descriptorfile = False
    
    try:
        opts, args = getopt.getopt(argv, "hi:o:ad")
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    
    
    for opt, arg in opts:
        if opt == "-h":
            usage()
            sys.exit()
        elif opt == "-i":
            workdir = arg
        elif opt == "-o":
            outputdir = arg
        elif opt == "-a":
            generate_articleassociationfile = True
        elif opt == "-d":
            generate_descriptorfile = True
    # iterate over the directories
    
    if workdir == '' or outputdir == '':
        usage()
        sys.exit(2)
    
    # check if the working directory exists
    if not path.isdir(workdir):
        print "*** ERROR: working dir doesn't exist; set as:"
        print "           %s" % workdir
        sys.exit(2)
      
    # check if the output directory exists
    if not path.isdir(outputdir):
        print "*** ERROR: output dir doesn't exist; set as:"
        print "           %s" % outputdir
        sys.exit(2)
    
    # Give out information of what will happen
    print 'Starting ...'
    print '  working dir: %s' % workdir
    print '  output  dir: %s' % outputdir
    print   
    
    if generate_articleassociationfile:
        print '  topic<->article associations: %s' % path.join(outputdir, 'articles2topics.out')
    if generate_descriptorfile:
        print '  descriptor types: %s' % path.join(outputdir, 'descriptors.out')
    print
    
    """ Read in the files """
    nyt_parse(workdir, outputdir, generate_articleassociationfile, generate_descriptorfile)
    
# end of main()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
