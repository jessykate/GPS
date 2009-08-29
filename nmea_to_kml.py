#!/usr/bin/python

#####################################################################
# convert data from nmea to a kml linestring, saving a kml file for
# each nmea file, in the same directory as the input file. needs to be
# cleaned up and generalized. some of these functions are now in
# libgps.
#####################################################################


import sys, exceptions, dircache, os

CURRENT_DATE = 0

class NmeaError(Exception):
    def __init__(self, value):
           self.parameter = value
    def __str__(self):
        return repr(self.parameter)

def validate_checksum(sentence, cksum):
    csum = 0
    for c in sentence:
        csum = csum ^ ord(c)
    return "%02X" % csum == cksum

def postgres_date(nmea_datestring):
    
    if len(nmea_datestring) != 6:
        raise NmeaError('Malformed date field')
    dd = nmea_datestring[0:2]
    mm = nmea_datestring[2:4]
    yy = nmea_datestring[4:6]
    return yy+mm+dd

def make_3d_coord(x,x_direction, y, y_direction, height_asl):
    
    # latitude format given : ddmm.mmm... 
    # latitude format wanted : dd.mmmmm... 
    latitude = int(float(x)/100) + (float(x) % 100)/60
    if x_direction == 'S':
        latitude = -latitude

    # longitude format given : dddmm.mmm... 
    # longitude format wanted : ddd.mmmmm... 
    longitude = int(float(y)/100.0) + (float(y) % 100)/60
    if y_direction == 'W':
        longitude = -longitude

    # careful with the order here. longitude, then latitude!
    return longitude, latitude, height_asl

def quote_field(field):
    # make sure the field has quotes as part of the string so it's
    # parsed properly by postgres.
    return "'%s'" % field

def coordinates(body):
    fields = '(utc, latlong, gps_fix, sats_in_view, horiz_error, alt_asl, height_wgs84, dgps_age, dgps_id)'    

    for field in 0,1,2,3,4,5,9:
        if body[field] is '':
            raise NmeaError('Missing key fields in NMEA GPGGA sentence')            

    # check the fix status. body[5] gives the fix quality. if this is
    # empty, we dont know if the reading is valid or not, so skip the
    # sentence altogether (essentially declaring it invalid). however,
    # sometimes there will be no fix, but relative position is still
    # being calculated. when there's no fix, the hdop and num sats
    # being tracked will be empty.
    if body[5] == 0:
        print >> sys.stderr, 'Invalid GPS GPGGA fix: %s' % body[5]
        return
    else:
        (long, lat, height) = make_3d_coord(body[1], body[2], body[3], body[4], body[8])        

    return '%s,%s,%s' % (long, lat, height)

def get_sentence(line, filename, position):    
    try:
        sentence, checksum = line.split('*') 
        sentence = sentence.strip('$')
        checksum = checksum.strip() # newlines and other nasties. 
    except ValueError, e:
        print >> sys.stderr, 'Invalid sentence: %s:%s %s' % (filename, position, e)
        return False
    try:
        if not validate_checksum(sentence, checksum):
            raise NmeaError('bad checksum. some bits musta gotten flipped.')
    except NmeaError, e:
        # note the error but keep going
        # print >> sys.stderr, 'NMEA Error: %s: %s %s' % (filename, linenum+1, e)
        return False
    return sentence

        
# ----------------------- main --------------------
try:
    LOGFILE_DIR = sys.argv[1]
    if LOGFILE_DIR[-1] != '/':
        LOGFILE_DIR += '/'
except:
    print 'argument error'
    print './nmea_to_kml path/to/logfile(s)'
    sys.exit()

for filename in dircache.listdir(LOGFILE_DIR):
    logfile = open(LOGFILE_DIR+filename)
    outfile = os.path.join(LOGFILE_DIR,filename[:filename.rfind('.')]+'.kml')
    if os.path.exists(outfile):
        print >> sys.stderr, 'file exist: %s. skipping' % outfile
        continue
    out = open(outfile, 'w')

    print >> out, '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://earth.google.com/kml/2.1">
  <Document>
    <Placemark>
      <name>Jessy's Path</name>
      <LineString>
       <coordinates>'''

    for linenum, line in enumerate(logfile):    
        sentence = get_sentence(line, filename, linenum+1)
        if sentence: # error checks returns False on error
            name, body = sentence.split(',', 1)
            body = body.split(',')
            if name == 'GPGGA':
                try:
                    print >> out, coordinates(body)
                except ValueError, e:
                    print >> sys.stderr, 'ValueError on line %s of file %s: %s' % (linenum+1, filename, e)
                    exit()
                except NmeaError, e:
                    # note the error but keep going
                    print >> sys.stderr, '\n>>>> NMEA Error: %s:%s %s' % (filename, linenum+1, e)
                    print >> sys.stderr, '>>>> Continuing\n'
    
    print >> out, '''    </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml> '''

    # make sure the write buffer is flushed
    out.flush() 
    out.close()
