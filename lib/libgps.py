import sys, os, datetime, re, dircache

######################################################
# purpose: various functions to support manipulating gps data and
# building of kml files from different formats using a couple of
# simple custom classes.
######################################################


######################################################
#                     CUSTOM CLASSES                 
######################################################

class Point(object):
    ''' creates a point object with a long, lat, and arbitrary other
    metadata. if datetime is used, it is expected to be in a python
    datetime object. ignoring timezones for now.'''
    def __init__ (self,lat, long, **other_metadata):
        self.lat = lat
        self.long = long
        if not other_metadata:
            return
        for key in other_metadata:
            self.__setattr__(key, other_metadata[key])

class Picture(object):
    ''' datetime is expected to be UTC'''
    def __init__(self, filename, datetime, lat=None, long=None):
        self.filename = filename
        self.datetime = datetime
        if lat:
            self.lat = lat
        if long:
            self.long = long
        


######################################################
#                     API (ish)
######################################################

def get_pic_info(pic_files):
    ''' scans the binary image file for the date string. like a poor
    man's exif to get the date information. only tested with jpgs
    right now. returns a list of Picture objects with the datetime and
    file information.'''
    pictures = []
    for pic_file in pic_files:
        fp = open(pic_file)
        picture = fp.read()
        date = re.search(r'\d\d\d\d:\d\d:\d\d \d\d:\d\d:\d\d', picture)
        if date:
            date, time = date.group().split()
            year, month, day = date.split(':')
            hour, minute, second = time.split(':')
            dt = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
            pictures.append(Picture(pic_file, dt))
    for picture in pictures:
        picture.datetime = libgps.datetime_to_utc(picture.datetime, utc_offset)
    pictures.sort(cmp=_cmp_pic_datetimes)
    return pictures


def points_from_file(logfile, format, *metadata):
    ''' a wrapper function to pass the logfile and requested metadata
    onto a format-specific function for processing.'''
    if format.lower() in SUPPORTED_FORMATS:
        return SUPPORTED_FORMATS[format.lower()](logfile, *metadata)

######################################################
#                     UTILITY
######################################################

def _cmp_pic_datetimes(pic_a, pic_b):
    if pic_a.datetime < pic_b.datetime:
        return -1
    elif pic_a.datetime > pic_b.datetime:
        return 1
    else: return 0

def files_in_subdirs(d, *extensions):
    ''' returns a list of all files specified in the *formats
    argument, in directory d and its subdirectories. formats should be
    specified in lowercase.'''
    if not extensions:
        print 'method files_in_subdirs(): you must specify extension types to look for.'
        return
    files = []
    for dir, subdirs, filenames in os.walk(d):        
        for filename in filenames:
            if filename.rsplit('.',1)[1].lower() in extensions:
                files.append(dir + '/' + filename)
    return files

def datetime_to_utc(localtime, offset_from_utc):    
    ''' NOT FINISHED! does not account for month or year rollovers
    yet. convert the datetime object localtime to UTC. offset_from_utc
    is a positive or negative integer representing the number of hours
    ahead or behind of UTC the local time is'''
    num_days = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31,
                9: 30, 10: 31, 11: 30, 12: 31}
    new_day = new_month = new_year = False

    # each new value is comprised of: 
    # (current value + rollover (either 0, 1, -1) % time unit's length (month/day/year)
    new_hour = (localtime.hour - offset_from_utc) % 24
    new_day = (localtime.day + (localtime.hour - offset_from_utc)/24) % num_days[localtime.month]
    new_month = (localtime.month + ((localtime.hour - offset_from_utc)/
                                    24)/num_days[localtime.month]) % 12
    new_year = localtime.year + (localtime.month + ((localtime.hour - offset_from_utc)/
                                                    24)/num_days[localtime.month])/12
    # the day will only ever change by one. but months are different
    # lengths, so if a) the month was rolled BACK, and b) it has a
    # different length than the old month, the new day will actually
    # be the last *date* of the new_month.
    print new_month
    if new_month < localtime.month and num_days[new_month] != num_days[localtime.month]:
        new_day = num_days[new_month]

    print new_hour, new_day, new_month, new_year
    utc = localtime.replace(hour = new_hour, day = new_day, month = new_month, year = new_year)
    return utc


######################################################
#                     KML
######################################################


def kml_preamble():
    return '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://earth.google.com/kml/2.1">
  <Document>'''

def kml_postamble():
    return '''
</Document>
</kml>
'''

def linestring_begin(name=None):
    s = '<Placemark>'
    if name:
        s += '\n<name>'+name+'</name>'
    s += '''
    <LineString>
    <coordinates>
'''
    return s


######################################################
#                     NMEA FUNCTIONS
######################################################

class NmeaError(Exception):
    def __init__(self, value):
           self.parameter = value
    def __str__(self):
        return repr(self.parameter)

def nmea_validate_checksum(sentence, cksum):
    csum = 0
    for c in sentence:
        csum = csum ^ ord(c)
    return "%02X" % csum == cksum

def nmea_get_sentence(line, filename, position):    
    try:
        sentence, checksum = line.split('*') 
        sentence = sentence.strip('$')
        checksum = checksum.strip() # newlines and other nasties. 
    except ValueError, e:
        print >> sys.stderr, 'Invalid sentence: %s:%s %s' % (filename, position, e)
        return False
    try:
        if not nmea_validate_checksum(sentence, checksum):
            raise NmeaError('bad checksum. some bits musta gotten flipped.')
    except NmeaError, e:
        # note the error but keep going
        # print >> sys.stderr, 'NMEA Error: %s: %s %s' % (filename, linenum+1, e)
        return False
    return sentence

def nmea_make_3d_coord(x,x_direction, y, y_direction, height_asl):
    
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

def nmea_get_points(logfile, *metadata):
    ''' a mostly hard-coded hack of a function which returns a list of
    point objects containing location and datetime. currently does
    absolutely nothing with the metadata argument.'''

    date = '' #eg 191109 --> 19 Nov. 2009
    all_points = []
    for linenum, line in enumerate(logfile):    
        error_flag = False
        sentence = nmea_get_sentence(line, logfile, linenum+1)
        if not sentence: # error checks returns False on error
            continue
        name, body = sentence.split(',', 1)
        body = body.split(',')
        # in GPRMC, body[1] is the nav/ receiver fix. V is warning
        if name == 'GPRMC' and body[1] != 'V' and body[8] != date:
            date = body[8]
        elif name == 'GPGGA':
            # check if date has been set yet, and skip one point in
            # case it has not yet been set.
            if date == '':
                continue 
            lng = lat = height = time = None
            for field in 0,1,2,3,4,5,9:
                if body[field] is '':
                    #print >> sys.stderr, 'Invalid GPS GPGGA sentence: %s' % str(body)
                    error_flag = True
                    continue
            if error_flag:
                continue
            if body[5] == 0:
                print >> sys.stderr, 'Invalid GPS GPGGA fix: %s' % str(body)
                continue
            else:
                (lng, lat, height) = nmea_make_3d_coord(body[1], body[2], body[3], 
                                                    body[4], body[8])        
                time = body[0]
                day = date[0:2]
                month = date[2:4]
                year = '20'+date[4:6]
                hour = time[0:2]
                minute = time[2:4]
                second = time[4:6]                
                utc = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second)) 
                p = Point(lat, lng, height=height, datetime=utc)
                all_points.append(p)
    return all_points


######################################################
#                     GPX FUNCTIONS
######################################################

def gpx_get_points():
    print 'i am matt, and i like gpx. harass me if you want this to work.'


######################################################
# hands off here, bitches
######################################################

SUPPORTED_FORMATS = {
    'nmea': nmea_get_points,
    'gpx' : gpx_get_points,
}

NMEA_SUPPORTED_ITEMS = {
}
