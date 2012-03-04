"""
Reads in a file of the format:
<DESCRIPTOR><TAB><DESCRIPTOR_TYPE_ID>

and inserts it to the database:
nytimes_corpus @ u003453

author: Manos Tsagkias <e.tsagkias@uva.nl>
date: 26 Jan 2010
"""
import sys, getopt, pg, codecs
from os import path

def usage():
    print """
    Tools for New York Times Corpus by LDC
    by Manos Tsagkias <e.tsagkias@uva.nl>
    
    Insert NY Times descriptors into database:
    nytimes_corpus@u003454
    
    Usage summary:
      -h          print usage summary
      -i <FILE>   input descriptors file format:
                  <DESCRIPTOR><TAB><DESCRIPTOR_TYPE_ID>
    
    <DESCRIPTOR_TYPE_ID> can take any of the values:
    Human descriptors:
    10 -- Biographical categories
    11 -- Descriptors
    12 -- Locations
    13 -- Names
    14 -- Organizations
    15 -- People
    16 -- Titles
    
    Computer generated descriptors:
    50 -- General online descriptors
    51 -- Online descriptors
    52 -- Online locations
    53 -- Online organizations
    54 -- Online people
    55 -- Online titles
    all descriptors are validated by humans
    """

def truncate_group_tables():
    """ Check how many articles are in articles2groups tables.
        If group_types is truncated, groups will be truncated,
        and articles2groups will be truncated too.
    """
    res = db.query('SELECT count(*) FROM articles2groups')
    if res.ntuples() and int(res.getresult()[0][0]) > 0:
        print '*** WARNING'
        print '*** %d articles will be deassigned grom their topics if you continue.'
        choice =  raw_input('Do you want to proceed? [Y/n] ')
        if choice.lower() == 'n':
            print 
            print 'Operation aborted due to user request.'
            return
            
    """ Truncate group_types and groups"""
    db.query('TRUNCATE TABLE group_types CASCADE')
    
    print 'Tables: group_types, groups, and article2groups truncated'
    
def nyt_insert_descriptor_types():
    """ Descriptor types are constant:
        Human descriptors:
        10 -- Biographical categories
        11 -- Descriptors
        12 -- Locations
        13 -- Names
        14 -- Organizations
        15 -- People
        16 -- Titles
    
        Computer generated descriptors:
        50 -- General online descriptors
        51 -- Online descriptors
        52 -- Online locations
        53 -- Online organizations
        54 -- Online people
        55 -- Online titles
    """
    
    db.query('''INSERT INTO group_types (group_type_id, group_type) VALUES (%d, '%s')''' % (10, 'Biographical categories'))
    db.query('''INSERT INTO group_types (group_type_id, group_type) VALUES (%d, '%s')''' % (11, 'Descriptors'))
    db.query('''INSERT INTO group_types (group_type_id, group_type) VALUES (%d, '%s')''' % (12, 'Locations'))
    db.query('''INSERT INTO group_types (group_type_id, group_type) VALUES (%d, '%s')''' % (13, 'Names'))
    db.query('''INSERT INTO group_types (group_type_id, group_type) VALUES (%d, '%s')''' % (14, 'Organizations'))
    db.query('''INSERT INTO group_types (group_type_id, group_type) VALUES (%d, '%s')''' % (15, 'People'))
    db.query('''INSERT INTO group_types (group_type_id, group_type) VALUES (%d, '%s')''' % (16, 'Titles'))
    
    db.query('''INSERT INTO group_types (group_type_id, group_type) VALUES (%d, '%s')''' % (50, 'General online descriptors'))
    db.query('''INSERT INTO group_types (group_type_id, group_type) VALUES (%d, '%s')''' % (51, 'Online descriptors'))
    db.query('''INSERT INTO group_types (group_type_id, group_type) VALUES (%d, '%s')''' % (52, 'Online locations'))
    db.query('''INSERT INTO group_types (group_type_id, group_type) VALUES (%d, '%s')''' % (53, 'Online organizations'))
    db.query('''INSERT INTO group_types (group_type_id, group_type) VALUES (%d, '%s')''' % (54, 'Online people'))
    db.query('''INSERT INTO group_types (group_type_id, group_type) VALUES (%d, '%s')''' % (55, 'Online titles'))
    
    print 'group_types tables filled.'


def nyt_parse_descriptors(infile):
    try:
        f = codecs.open(infile, 'r', 'utf-8')
    except:
        print 'Cannot open the file for reading. Either the file is not UTF-8, or check the permissions.'
        return
        
    # total_recs come from
    # wc -l /scratch/tsagias/acl2010-tracking/descriptors.out
    total_recs = 858689
    for i, line in enumerate(f):
        out = 'Processing %d / %d\r' % (i, total_recs)
        print out # + '\b' * len(out)
        
        """ Skip lines beginning with #, it's a comment"""
        if line[0] == '#': continue
        
        """ Split the line at <TAB>"""
        descriptor, descriptor_type = line.split("\t")
        
        """ Insert the line to the groups_type table """
        db.query('''
        INSERT INTO groups
        (group_name, group_type_id)
        VALUES
        ('%s', %d)
        ''' % (pg.escape_string(descriptor.encode('utf-8')), int(descriptor_type)))
        
        
    f.close()


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
    truncate_group_tables()
    
    """ Insert group_types (descriptor types) """
    nyt_insert_descriptor_types()
    
    """ Read in the files """
    nyt_parse_descriptors(infile)
    
# end of main()


if __name__ == "__main__":
    """ Connect to the database """
    db = pg.connect('nytimes_corpus', 'u003453.science.uva.nl', 5432, None, None, 'tsagias', '251313');
    
    sys.exit(main(sys.argv[1:]))
