
import MySQLdb
import sys
from collections import defaultdict


# All sorts of RBTODO.  Just a 

"""Classes that hold annotation metadata"""

# Annotation types
ANNO_ANNOTATION = 1
ANNO_SYNAPSE = 2
ANNO_SEED = 3

# list of database table names.  Move to annproj?
anno_dbtables = { 'annotation':'annotations',\
                  'kvpairs':'kvpairs',\
                  'synapse':'synapses',\
                  'seed':'seeds',\
                  'synapse_segment':'synapse_segments',\
                  'synapse_seed':'synapse_seeds' }



###############  Annotation  ##################

class Annotation:
  """Metdata common to all annotations."""

  def __init__ ( self ):
    """Initialize the fields to zero or null"""

    # metadata fields
    self.annid = 0 
    self.status = 0 
    self.confidence = 0.0 
    self.kvpairs = defaultdict(list)


  def store ( self, annotype, annodb ):
    """Store the annotation to the annotations database"""

    sql = "INSERT INTO %s VALUES ( %s, %s, %s, %s )"\
            % ( anno_dbtables['annotation'], self.annid, annotype, self.confidence, self.status )

    cursor = annodb.conn.cursor ()
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error inserting annotation %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise

  
    if len(self.kvpairs) != 0:
      kvclause = ','.join(['(' + str(self.annid) +',\'' + k + '\',\'' + v +'\')' for (k,v) in self.kvpairs.iteritems()])  
      sql = "INSERT INTO %s VALUES %s" % ( anno_dbtables['kvpairs'], kvclause )

      try:
        cursor.execute ( sql )
      except MySQLdb.Error, e:
        print "Error inserting annotation %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
        raise

    annodb.conn.commit()


  def update ( self, annotype, annodb ):
    """Update the annotation in the annotations database"""

    sql = "UPDATE %s SET  anno_type=%s, confidence=%s, status=%s WHERE annoid = %s"\
            % ( anno_dbtables['annotation'], annotype, self.confidence, self.status, self.annid)

    cursor = annodb.conn.cursor ()
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error updating annotation %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise

    # Get the old kvpairs and identify new kvpairs
    sql = "SELECT * FROM %s WHERE annoid = %s" % ( anno_dbtables['kvpairs'], self.annid )
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error retrieving kvpairs %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise
    kvresult = cursor.fetchall()

    kvupdate = {}

    for kv in kvresult:
      # for key values already stored
      if self.kvpairs.has_key( kv[1] ): 
        # update if they are new
        if self.kvpairs[kv[1]] != kv[2]:
          kvupdate[kv[1]] = self.kvpairs[kv[1]]
        # ignore if they are the same
        del(self.kvpairs[kv[1]])

    # Update changed keys
    if len(kvupdate) != 0:
      for (k,v) in kvupdate.iteritems():
        sql = "UPDATE %s SET kv_value='%s' WHERE annoid=%s AND kv_key='%s'" % ( anno_dbtables['kvpairs'], v, self.annid, k )
        cursor.execute ( sql )
        
    # insert new kv pairs
    if len(self.kvpairs) != 0:
      kvclause = ','.join(['(' + str(self.annid) +',\'' + k + '\',\'' + v +'\')' for (k,v) in self.kvpairs.iteritems()])  
      sql = "INSERT INTO %s VALUES %s" % ( anno_dbtables['kvpairs'], kvclause )

      try:
        cursor.execute ( sql )
      except MySQLdb.Error, e:
        print "Error inserting annotation %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
        raise

    annodb.conn.commit()
    print "Commited on base class"


  def retrieve ( self, annid, annodb ):
    """Retrieve the annotation by annid"""

    sql = "SELECT * FROM %s WHERE annoid = %s" % ( anno_dbtables['annotation'], annid )

    cursor = annodb.conn.cursor ()
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error retrieving annotation %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise
    ( self.annid, annotype, self.confidence, self.status ) = cursor.fetchone()

    sql = "SELECT * FROM %s WHERE annoid = %s" % ( anno_dbtables['kvpairs'], annid )

    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error retrieving kvpairs %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise
    kvpairs = cursor.fetchall()
    for kv in kvpairs:
      self.kvpairs[kv[1]] = kv[2]

    return annotype



###############  Synapse  ##################

class AnnSynapse (Annotation):
  """Metadata specific to synapses"""

  def __init__(self ):
    """Initialize the fields to zero or null"""

    self.weight = 0.0 
    self.synapse_type = 0 
    self.seeds = []
    self.segments = []

    # Call the base class constructor
    Annotation.__init__(self)

  def store ( self, annodb ):
    """Store the synapse to the annotations databae"""

    sql = "INSERT INTO %s VALUES ( %s, %s, %s )"\
            % ( anno_dbtables['synapse'], self.annid, self.synapse_type, self.weight )

    cursor = annodb.conn.cursor ()
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error inserting synapse %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise

    # synapse_seeds
    seedsclause= ','.join ( [ '(' + str(self.annid) + ',' + str(v) + ')' for v in self.seeds ] )
    sql = "INSERT INTO %s VALUES %s"\
            % ( anno_dbtables['synapse_seed'], seedsclause )

    cursor = annodb.conn.cursor ()
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error inserting synapse seeds %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise

    # synapse_segments
    segmentsclause= ','.join ( [ '(' + str(self.annid) + ',' + str(v[0]) + ',' + str(v[1]) + ')' for v in self.segments ] )
    sql = "INSERT INTO %s VALUES %s"\
            % ( anno_dbtables['synapse_segment'], segmentsclause )

    cursor = annodb.conn.cursor ()
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error inserting synapse segments %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise

    # and call store on the base classs
    Annotation.store ( self, ANNO_SYNAPSE, annodb )

    annodb.conn.commit()


  def update ( self, annodb ):
    """Update the synapse in the annotations databae"""

    sql = "UPDATE %s SET synapse_type=%s, weight=%s WHERE annoid=%s "\
            % (anno_dbtables['synapse'], self.synapse_type, self.weight, self.annid)

    cursor = annodb.conn.cursor ()
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error updating synapse %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise

    annodb.conn.commit()


    # udpate synapse_seeds
    sql = "DELETE from %s WHERE annoid=%s;" % (anno_dbtables['synapse_seed'], self.annid) 
    cursor.execute(sql)

    seedsclause= ','.join ( [ '(' + str(self.annid) + ',' + str(v) + ')' for v in self.seeds ] )
    sql = "INSERT INTO %s VALUES %s"\
            % ( anno_dbtables['synapse_seed'], seedsclause )

    cursor = annodb.conn.cursor ()
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error updating synapse seeds %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise

    # udpate synapse_segments
    sql = "DELETE from %s WHERE annoid=%s;" % (anno_dbtables['synapse_segment'], self.annid) 
    cursor.execute(sql)

    segmentsclause= ','.join ( [ '(' + str(self.annid) + ',' + str(v[0]) + ',' + str(v[1]) + ')' for v in self.segments ] )
    sql = "INSERT INTO %s VALUES %s"\
            % ( anno_dbtables['synapse_segment'], segmentsclause )

    cursor = annodb.conn.cursor ()
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error inserting synapse segments %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise

    # and call update on the base classs
    Annotation.update ( self, ANNO_SYNAPSE, annodb )

    annodb.conn.commit()



  def retrieve ( self, annid, annodb ):
    """Retrieve the synapse by annid"""

    # Call the base class retrieve
    annotype = Annotation.retrieve ( self, annid, annodb )

    # verify the annotation object type
    # RBTODO make an exception
    assert ( annotype == ANNO_SYNAPSE )

    sql = "SELECT synapse_type, weight FROM %s WHERE annoid = %s" % ( anno_dbtables['synapse'], annid )

    cursor = annodb.conn.cursor ()
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error retrieving synapse %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise
    ( self.synapse_type, self.weight ) = cursor.fetchone()

    sql = "SELECT seed FROM %s WHERE annoid = %s" % ( anno_dbtables['synapse_seed'], annid )
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error retrieving synapse seeds %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise
    seedtuples = cursor.fetchall()
    self.seeds = [x[0] for x in seedtuples]

    sql = "SELECT segmentid, segment_type FROM %s WHERE annoid = %s" % ( anno_dbtables['synapse_segment'], annid )
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error retrieving synapse segments %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise
    segmenttuples = cursor.fetchall()
    self.segments = [ [x[0],x[1]] for x in segmenttuples ]


###############  Seed  ##################

class AnnSeed (Annotation):
  """Metadata specific to seeds"""

  def __init__ (self):
    """Initialize the fields to zero or null"""

    self.parent=0        # parent seed
    self.position=[]
    self.cubelocation=0  # some enumeration
    self.source=0        # source annotation id

    # Call the base class constructor
    Annotation.__init__(self)

  def store ( self, annodb ):
    """Store the seed to the annotations databae"""

    if self.position == []:
      storepos = [ 'NULL', 'NULL', 'NULL' ]
    else:
      storepos = self.position
      
    sql = "INSERT INTO %s VALUES ( %s, %s, %s, %s, %s, %s, %s )"\
            % ( anno_dbtables['seed'], self.annid, self.parent, self.source, self.cubelocation, storepos[0], storepos[1], storepos[2])

    cursor = annodb.conn.cursor ()
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error inserting seed %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise

    # and call store on the base classs
    Annotation.store ( self, ANNO_SEED, annodb )

    annodb.conn.commit()

  def update ( self, annodb ):
    """Update the seed to the annotations databae"""

    if self.position == []:
      storepos = [ 'NULL', 'NULL', 'NULL' ]
    else:
      storepos = self.position
      
    sql = "UPDATE %s SET parentid=%s, sourceid=%s, cube_location=%s, positionx=%s, positiony=%s, positionz=%s where annoid = %s"\
            % ( anno_dbtables['seed'], self.parent, self.source, self.cubelocation, storepos[0], storepos[1], storepos[2], self.annid)

    cursor = annodb.conn.cursor ()
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error inserting seed %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise

    # and call update on the base classs
    Annotation.update ( self, ANNO_SEED, annodb )

    annodb.conn.commit()


  def retrieve ( self, annid, annodb ):
    """Retrieve the seed by annid"""

    # Call the base class retrieve
    Annotation.retrieve ( self, annid, annodb )

    sql = "SELECT parentid, sourceid, cube_location, positionx, positiony, positionz FROM %s WHERE annoid = %s" % ( anno_dbtables['seed'], annid )
      
    cursor = annodb.conn.cursor ()
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      print "Error retrieving seed %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
      raise

    # need to initialize position to prevent index error
    self.position = [0,0,0]
    (self.parent, self.source, self.cubelocation, self.position[0], self.position[1], self.position[2]) = cursor.fetchone()


#
#  getAnnotation returns an annotation object
#
def getAnnotation ( annid, annodb, options=None ): 
  """Return an annotation object by identifier"""

  # First, what type is it.  Look at the annotation table.
  sql = "SELECT anno_type FROM %s WHERE annoid = %s" % ( anno_dbtables['annotation'], annid )
  cursor = annodb.conn.cursor ()
  try:
    cursor.execute ( sql )
  except MySQLdb.Error, e:
    print "Error reading id %d: %s. sql=%s" % (e.args[0], e.args[1], sql)
    raise
  
  sqlresult = cursor.fetchone()
  if sqlresult == None:
    return None
  else:
    type = sqlresult[0]

  # switch on the type of annotation
  if type == ANNO_SYNAPSE:
    syn = AnnSynapse()
    syn.retrieve(annid, annodb)
    return syn

  elif type == ANNO_SEED:
    seed = AnnSeed()
    seed.retrieve(annid, annodb)
    return seed

  elif type == ANNO_ANNOTATION:
    raise ANNOError ( "Found type ANNO_ANNOTATION. Should not store/fetch base type." )
  else:
    # not a type that we recognize
    raise ANNOError ( "Unrecognized annotation type %s" % type )


#
#  putAnnotation 
#
def putAnnotation ( anno, annodb, options=None ): 
  """Return an annotation object by identifier"""

  # if annid == 0, create a new identifier
  if anno.annid == 0 or anno.annid == None:
    anno.annid = annodb.nextID()
    anno.store(annodb) 
  # for updates, make sure the annotation exists and is of the right type
  elif  'update' in options:
    oldanno = getAnnotation ( anno.annid, annodb )
    if  oldanno == None or oldanno.__class__ != anno.__class__:
      raise ANNOError ( "During update no annotation found at id %d" % anno.annid  )
   # update the annotation
    else:
      anno.update(annodb)
  # Write the user chosen annotation id
  else:
    annodb.setID ( anno.annid )
    anno.store(annodb)
 