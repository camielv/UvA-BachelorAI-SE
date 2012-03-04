"""
Reads in a file of the format:
<DESCRIPTORS><TAB><TAXONOMY><TAB><ARTICLE_GUID><TAB><PUBDATE>
where <DESCRIPTORS> and <TAXONOMY> values are separated by semicolon (;)

author: Manos Tsagkias <e.tsagkias@uva.nl>
date: 26 Jan 2010
"""
import sys, getopt, pg, codecs, collections
from os import path

def usage():
    print """
    Tools for New York Times Corpus by LDC
    by Manos Tsagkias <e.tsagkias@uva.nl>
    
    Insert NY Times articles and their topic associations into database:
    nytimes_corpus@u003454
    
    Usage summary:
      -h          print usage summary
      -i <FILE>   input articles file format:
                  <DESCRIPTORS><TAB><TAXONOMY><TAB><ARTICLE_GUID><TAB><PUBDATE>
    
    where <DESCRIPTORS> and <TAXONOMY> values are separated by semicolon (;)
    """

def truncate_article_tables():
    """ Check how many articles are in articles tables.
        If articles is truncated, articles2groups will be truncated.
    """
    res = db.query('SELECT count(*) FROM articles')
    if res.ntuples() and int(res.getresult()[0][0]) > 0:
        print '*** WARNING'
        print '*** %d articles will be removed (articles table) and deassigned from their topics (articles2groups table).'
        choice =  raw_input('Do you want to proceed? [Y/n] ')
        if choice.lower() == 'n':
            print 
            print 'Operation aborted due to user request.'
            return
            
    """ Truncate group_types and groups"""
    db.query('TRUNCATE TABLE articles CASCADE')
    
    print 'Tables: articles, and article2groups tables truncated'


def nyt_parse_articles(infile):
    descriptor2article = collections.defaultdict(lambda: list())
    taxonomy2article = collections.defaultdict(lambda: list())
    
    try:
        f = codecs.open(infile, 'r', 'utf-8')
    except:
        print 'Cannot open the file for reading. Either the file is not UTF-8, or check the permissions.'
        return
        
    # total_recs come from
    # wc -l /scratch/tsagias/acl2010-tracking/articles2topics.out
    total_recs = 1859122
    for i, line in enumerate(f):
        out = 'Processing %d / %d\r' % (i, total_recs)
        print out + '\b' * len(out)
        
        """ Skip lines beginning with #, it's a comment"""
        if line[0] == '#': continue
        
        """ Split the line at <TAB>"""
        descriptors, taxonomy, article_id, article_pubdate = line.split("\t")
        
        """ DESCRIPTORS: split them in ;"""
        descriptors = descriptors.split(';')
        
        """ TAXONOMIES: split them in ;"""
        taxonomies = taxonomy.split(';')
        
        """ Assign articles to descriptors and taxonomies """
        for d in descriptors:
            descriptor2article[d.strip()].append(article_id)
            
        for t in taxonomies:
            taxonomy2article[t.strip()].append(article_id)
            
        # """ Add article to the database """
        # db.query('''
        # INSERT INTO articles
        # (article_id, pubdate)
        # VALUES
        # (%d, '%s')
        # ''' % (int(article_id), article_pubdate))
    f.close()
    
    """ Assign articles to descriptors """
    # print 'Sending article<->descriptors associations ..'
    # for k, v in descriptor2article.iteritems():
    #     descriptor_id = db.query('''
    #     SELECT group_id 
    #     FROM groups
    #     WHERE group_name = E'%s'
    #     ''' % pg.escape_string(k.strip().encode('utf-8')))
    #     
    #     if not descriptor_id.ntuples(): 
    #         print '** NOT FOUND Descriptor: %s' % k
    #         continue
    #     else:
    #         descriptor_id = descriptor_id.getresult()[0][0]
    #     
    #     for i in v:
    #         db.query('''
    #         INSERT INTO articles2groups
    #         (article_id, group_id)
    #         VALUES
    #         (%d, %d)
    #         ''' % (int(i), int(descriptor_id)))
    # print 'done'
    
    """ Assign articles to taxonomy """
    print 'Building taxonomy ..'
    for k, v in taxonomy2article.iteritems():
        print 'Processing taxonomy %s (%d articles)' % (k, len(v))
        """ Split the taxonomy by /"""
        t = k.split('/')
        
        parent_id = 'NULL'
        for i, rec in enumerate(t):
            sql_taxonomy_name = pg.escape_string(rec.strip().encode('utf-8'))
            
            # if not sql_taxonomy_name:
            #     print '*** Taxonomy name empty. Skipping ..'
            #     continue
                
            # check if we have the taxonomy already
            if parent_id == 'NULL':
                q = '''
                SELECT taxonomy_id
                FROM taxonomy
                WHERE lower(taxonomy_name) = E'%s'
                AND taxonomy_parent_id IS NULL
                ''' % (sql_taxonomy_name.lower())
            else:
                q = '''
                SELECT taxonomy_id
                FROM taxonomy
                WHERE lower(taxonomy_name) = E'%s'
                AND taxonomy_parent_id = %s
                ''' % (sql_taxonomy_name.lower(), str(parent_id))
                
            rtaxonomy_id = db.query(q)
            if rtaxonomy_id.ntuples() > 0:
                parent_id = rtaxonomy_id.getresult()[0][0]
                print '*** NOTICE: Taxonomy %s already inserted as %s' % (sql_taxonomy_name, parent_id)
                continue
            
            # if you don't, insert the new taxonomy
            db.query('''
            INSERT INTO taxonomy
            (taxonomy_name, taxonomy_parent_id)
            VALUES (E'%s', %s)
            ''' % (sql_taxonomy_name, str(parent_id)))
                
            # get taxonomy id
            parent_id = db.query('''
            SELECT currval('taxonomy_taxonomy_id_seq')
            ''').getresult()[0][0]
        
        for rec in set(v):
            db.query('''
            INSERT INTO articles2taxonomy
            (article_id, taxonomy_id)
            VALUES
            (%d, %s)
            ''' % (int(rec), int(parent_id)))
    print 'done'
# end of nyt_parse_articles()


def main(argv):
    """ Initialization """
    infile = ''
    
    try:
        opts, args = getopt.getopt(argv, "hi:")
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    
    
    for opt, arg in opts:
        if opt == "-h":
            usage()
            sys.exit()
        elif opt == "-i":
            infile = arg
    # iterate over the directories
    
    if infile == '':
        usage()
        sys.exit(2)
    
    # check if the working directory exists
    if not path.isfile(infile):
        print "*** ERROR: descriptors file doesn't exist; set as:"
        print "           %s" % infile
        sys.exit(2)
      
    # Give out information of what will happen
    print 'Starting ...'
    print '  descriptors file: %s' % infile
    print '  target database: nytimes_corpus@u003453'
    print
    
    """ Truncate tables """
    # truncate_article_tables()
    
    """ Read in the files """
    nyt_parse_articles(infile)
    
# end of main()


if __name__ == "__main__":
    """ Connect to the database """
    db = pg.connect('nytimes_corpus', 'u003453.science.uva.nl', 5432, None, None, 'tsagias', '251313');
    
    sys.exit(main(sys.argv[1:]))
