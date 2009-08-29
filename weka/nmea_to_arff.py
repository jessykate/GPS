#!/usr/bin/python

##########################################################
# creates one weka arff file with points from ALL nmea files in the
# input directory
##########################################################

import os, sys, dircache
import lib.libgps as libgps

try:
    LOGFILE_DIR = sys.argv[1]
    if LOGFILE_DIR[-1] != '/':
        LOGFILE_DIR += '/'
except:
    print 'argument error!'
    print 'usage: ./nmea_to_arff.py path/to/logfile(s)'
    print '\teg. ./nmea_to_arff.py gps/logfiles/june27/'
    sys.exit()

outfile = os.path.join(LOGFILE_DIR,'all_coords.arff')
if os.path.exists(outfile):
    print >> sys.stderr, '\tFile exist: %s.\n' % outfile
    sys.exit()
out = open(outfile, 'w')

print >> out, '''
% 1. Title: GPS Data Points
%
@RELATION coordinates

@ATTRIBUTE longitude  NUMERIC
@ATTRIBUTE latitude   NUMERIC
@ATTRIBUTE datetime  date "yyyy-MM-dd'T'HH:mm:ss"

@data
'''


for filename in dircache.listdir(LOGFILE_DIR):
    if os.path.isdir(LOGFILE_DIR+filename):
        continue
    if filename[filename.rfind('.')+1:].lower() != 'txt':
        continue
    print 'now processing:', filename
    logfile = open(LOGFILE_DIR+filename)

    # returned points are cleaned for basic validity
    points = libgps.points_from_file(logfile, 'NMEA', 'date', 'time')

    if not points:
        #out.close()
        #os.remove(outfile)
        continue

    for point in points:
        print >> out, '%s,%s,"%s"' % (point.long, point.lat, point.datetime.isoformat())

out.flush() 
out.close()



    
