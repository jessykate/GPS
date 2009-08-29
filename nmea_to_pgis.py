#!/usr/bin/python

#####################################################################
# purpose: parse sentences from nmea files into a postgis (spatially
# enabled) database. mostly mirrors the fields in the nmea sentences,
# and currently only stores GPRMC and GPGGA.
#####################################################################


import psycopg2, sys, exceptions, dircache
conn = psycopg2.connect("dbname=gis_test2")
cur = conn.cursor()

LOGFILE_DIR = "/home/jessy/lifelogging/gps/logfiles/subset/"
CURRENT_DATE = 0

class NmeaError(Exception):
    def __init__(self, value):
           self.parameter = value
    def __str__(self):
        return repr(self.parameter)


def print_debugging(sentence, *args):
    print '----------- %s ----------' % sentence
    for info in args:
        print info
    print ''

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

def make_wkt_point(x,x_direction, y, y_direction):
    POINT_SRID = 4326

    
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
    return "PointFromText('POINT(%s %s)', %s)" % (longitude,latitude, POINT_SRID)    

def quote_field(field):
    # make sure the field has quotes as part of the string so it's
    # parsed properly by postgres.
    return "'%s'" % field

def add_gpgga(body):
    # note this function might truncate milliseconds on the utc
    # field... double check if you care.

    fields = '(utc, latlong, gps_fix, sats_in_view, horiz_error, alt_asl, height_wgs84, dgps_age, dgps_id)'    

    for field in 0,1,2,3,4,5,9:
        if body[field] is '':
            raise NmeaError('Missing key fields in NMEA GPGGA sentence')            

    utc = quote_field(body[0])
    latlong = make_wkt_point(body[1], body[2], body[3], body[4])

    # check units on the altitude and height of geoid column
    # which are stored in body[9] and body[11]
    if body[9].upper() != 'M' or body[11].upper() != 'M':
        print 'warning: non standard unit found on altitude or height of geoid column. values were "%s" and "%s", respectively.' % (body[9], body[11])
        answer = raw_input("continue? (q to abort): ")
        if answer == 'q':
            exit()

    # check the fix status. body[5] gives the fix quality. if this is
    # empty, we dont know if the reading is valid or not, so skip the
    # sentence altogether (essentially declaring it invalid). however,
    # sometimes there will be no fix, but relative position is still
    # being calculated. when there's no fix, the hdop and num sats
    # being tracked will be empty.
    for field in (6,7):
        if body[field] is '':
            body[field] = 'NULL'

    # check the dgps fields. if dgps is not being used, make the fields NULL.
    if body[12] is '':
        body[12] = 'NULL'
        body[13] = 'NULL'

    data = (utc, latlong) + tuple(body[5:8]) + (body[8],) + (body[10],) + tuple(body[12:])
    values = ','.join([str(i) for i in data])

    query = 'INSERT INTO gpgga ' + fields + ' VALUES (%s)' % values

    if DEBUG:
        print_debugging('gpgga', fields, body, query)

    cur.execute(query)
    conn.commit()    
    
def add_gprmc(body):
    fields = '(utc, status, latlong, speed_knots, angle_true, the_date, mag_var, mode)'
    
    # basic existence checking on key fields:
    for field in 0,1,2,3,4,5,8: 
        if body[field] is '':
            raise NmeaError('Missing key fields in NMEA GPRMC sentence')    
        
    utc = quote_field(body[0])
    # body[1] gives the sentence status. A = valid/ok, V =
    # warning/invalid. for now, keeping them either way.
    status = quote_field(body[1])

    the_date = quote_field(postgres_date(body[8]))

    mode = quote_field(body[-1])
    latlong = make_wkt_point(body[2], body[3], body[4], body[5])

    # body[6], body[7] are likely to be empty if the sentence is invalid. 
    for field in 6,7:
        if body[field] is '':
            body[field] = 'NULL'

    # if magnetic variation value exists, check the direction. if it
    # doesnt, set the field to null.
    if body[9]: 
        if body[10] == 'W':
            body[9] = -body[9]
    else: body[9] = 'NULL'
        
    data = (utc, status, latlong) + tuple(body[6:8]) + (the_date, body[9], mode)
    values = ','.join([str(i) for i in data])

    query = 'INSERT INTO gprmc ' + fields + ' VALUES (%s)' % values
    if DEBUG:
        print_debugging('gprmc', fields, body, query)
    cur.execute(query)
    conn.commit()    
    

def add_gpgsa(body):
    pass

def add_gpgsv(body):
    pass

def add_record(name, body):
    if name == 'GPGGA':
        add_gpgga(body)
    elif name == 'GPRMC':        
        add_gprmc(body)
    else: 
        return    
    
# ----------------------- main --------------------

# -f filename.txt
# -p path/to/nmea/files
# -d database_name
# --debug=true

try:
    if sys.argv[1].lower() == 'debug':
        DEBUG = True
    else: DEBUG = False
except:
    DEBUG = False


#filename = 'JESSY_833001089_20090121_142838.TXT'
#filename = 'test_sentences.txt'

for filename in dircache.listdir(LOGFILE_DIR):
    print filename
    logfile = open(LOGFILE_DIR+filename)
    linenum = 0
    for line in logfile:    
        linenum +=1
        try:
            sentence, checksum = line.split('*') 
            sentence = sentence.strip('$')
            checksum = checksum.strip() # newlines and other nasties. 
        except ValueError, e:
            print 'Invalid sentence: %s:%s %s' % (filename, linenum, e)
            continue
        try:
            if not validate_checksum(sentence, checksum):
                raise NmeaError('bad checksum. some bits musta gotten flipped.')
        except NmeaError, e:
            # note the error but keep going
            print '\n>> NMEA Error: %s:%s %s' % (filename, linenum, e)
            print '>> Continuing\n'
            continue
        # split into name and words
        name, body = sentence.split(',', 1)
        body = body.split(',')
        try:
            add_record(name, body)
        except ValueError, e:
            print 'ValueError on line %s of file %s: %s' % (linenum, filename, e)
            exit()
        except psycopg2.ProgrammingError, e:
            print 'ProgrammingError on line %s of file %s: %s' % (linenum, filename, e)
            exit()
        except NmeaError, e:
            # note the error but keep going
            print '\n>>>> NMEA Error: %s:%s %s' % (filename, linenum, e)
            print '>>>> Continuing\n'
    
