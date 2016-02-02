# Copyright 2014 Open Connectome Project (http://openconnecto.me)
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import redis
import blosc
import hashlib
from sets import Set
from operator import add, sub, mul, div, mod

import ndlib

SUPERCUBESIZE = [4,4,4]

import logging
logger=logging.getLogger("neurodata")


"""Helpers function to do cube I/O in across multiple DBs.
    This uses the state and methods of spatialdb"""

class RedisKVIO:

  def __init__ ( self, db ):
    """Connect to the S3 backend"""
    
    self.db = db
    self.client = redis.StrictRedis(host=self.db.proj.getDBHost(), port=6379, db=0)
    self.pipe = self.client.pipeline(transaction=False)
    
  def close ( self ):
    """Close the connection"""
    pass
    # self.cluster.shutdown()

  def startTxn ( self ):
    """Start a transaction. Ensure database is in multi-statement mode."""
    pass
    
    
  def commit ( self ): 
    """Commit the transaction. Moved out of __del__ to make explicit."""
    pass
    
  def rollback ( self ):
    """Rollback the transaction. To be called on exceptions."""
    pass
  
  def generateKeys(self, ch, resolution, zidx_list, timestamp):
    """Generate a key for Redis"""
    
    import types
    key_list = []
    if isinstance(timestamp, types.ListType):
      for tvalue in timestamp:
        key_list.append( '{}_{}_{}_{}_{}'.format(self.db.proj.getProjectName(), ch.getChannelName(), resolution, tvalue, zidx_list[0]) )
    else:
      for zidx in zidx_list:
        if timestamp == None:
          key_list.append( '{}_{}_{}_{}'.format(self.db.proj.getProjectName(), ch.getChannelName(), resolution, zidx) )
        else:
          key_list.append( '{}_{}_{}_{}_{}'.format(self.db.proj.getProjectName(), ch.getChannelName(), resolution, timestamp, zidx) )

    return key_list

  def getCube(self, ch, zidx, resolution, update=False, timestamp=None):
    """Retrieve a single cube from the database"""
    
    rows = self.client.mget( self.generateKeys(ch, resolution, [zidx], timestamp) )  
    if rows[0]:
      return rows[0]
    else:
      return None

  def getCubes(self, ch, listofidxs, resolution, neariso=False, timestamp=None):
    """Retrieve multiple cubes from the database"""
    
    rows = self.client.mget( self.generateKeys(ch, resolution, listofidxs, timestamp) )
    for idx, row in zip(listofidxs, rows):
      yield ( idx, row )
  
  def getTimeCubes(self, ch, idx, listoftimestamps, resolution):
    """Retrieve multiple cubes from the database"""
    
    rows = self.client.mget( self.generateKeys(ch, resolution, [idx], listoftimestamps) )
    for idx, timestamp, row in zip([idx]*len(listoftimestamps), listoftimestamps, rows):
      yield ( idx, timestamp, row )
 
  def putCube(self, ch, zidx, resolution, cubestr, update=False, timestamp=None):
    """Store a single cube into the database"""
    
    key_list = self.generateKeys(ch, resolution, [zidx], timestamp=timestamp)
    self.client.mset( dict(zip(key_list, [cubestr])) )
  
  def putCubes(self, ch, listofidxs, resolution, listofcubes, update=False, timestamp=None):
    """Store multiple cubes into the database"""
    
    key_list = self.generateKeys(ch, resolution, listofidxs, timestamp=timestamp)
    self.client.mset( dict(zip(key_list, listofcubes)) )