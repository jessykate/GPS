#!/usr/bin/python

#####################################################################
# purpose: builds a kml file containing a LineString from all points on
# the user-specified date. 
#####################################################################


import psycopg2, sys, exceptions

conn = psycopg2.connect("dbname=gis_test2")
cur = conn.cursor()

the_date = '' # YYYY-MM-DD
timezone = -7 # PST, no daylight savings
detail = 10

try:
    the_date = "'%s'" % sys.argv[1]
except:
    print 'error: you need to give a date. format: YYYY-MM-DD'
    exit()


# print header info (careful-- no newline at the top, it will cause an
# error.
print '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://earth.google.com/kml/2.1">
  <Document>
    <name>GPS Path for %s</name>
    <description>Daily GPS Path</description>

    <Style id="redLine">
      <LineStyle>
        <color>ff0000ff</color>
        <width>4</width>
      </LineStyle>
    </Style>

    <Placemark>
      <name>Jessy's Path on %s</name>
      <styleUrl>#redLine</styleUrl> ''' % (the_date, the_date)

query = """select askml(makeline(foo.latlong)) from (select pk, latlong, utc,
the_date from gprmc where the_date = %s and pk %% %d = 0 order by utc)
as foo"""  % (the_date, detail)

cur.execute(query)
for record in cur.fetchall():
    print record[0]


print '''
    </Placemark>
  </Document>
</kml> '''

