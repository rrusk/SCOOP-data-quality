#!/usr/bin/python
# -*- coding: utf-8 -*-
# Script assumes that database connection information is stored in
# ~/mysql/db_config.  Change if needed.  Variables are initialized
# this way for compatibility with prior Bash script.
#
__author__ = 'rrusk'

import MySQLdb as mdb
import sys
import time

con = None
f = None

query1 = ("SELECT COUNT(DISTINCT d.demographic_no) AS 'Count' "
          "FROM demographic AS d "
          "INNER JOIN drugs AS dr ON d.demographic_no = dr.demographic_no "
          "WHERE d.patient_status = 'AC' AND "
          "CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) < "
          "DATE_SUB( NOW(), INTERVAL 64 YEAR )")

query2 = ("SELECT dr.demographic_no FROM drugs AS dr "
          "WHERE dr.archived = 0 AND dr.regional_identifier IS NOT NULL AND "
            "dr.regional_identifier != '' AND dr.ATC IS NOT NULL AND "
            "dr.ATC != '' AND rx_date <= NOW() AND "
            "(DATE_ADD(dr.rx_date, INTERVAL(DATEDIFF(dr.end_date,dr.rx_date)*1.2) DAY)) >= NOW() "
          "GROUP BY dr.demographic_no "
          "HAVING COUNT(DISTINCT dr.regional_identifier) >= 5")

try:
    from os.path import expanduser
    home = expanduser("~")

    # configure database connection
    f = open(home+'/mysql/db_config/db_user')
    db_user = f.readline().rstrip('\n')
    f.close()
    f = open(home+'/mysql/db_config/db_passwd')
    db_passwd = f.readline().rstrip('\n')
    f.close()
    f = open(home+'/mysql/db_config/db_name')
    db_name = f.readline().rstrip('\n')
    f.close()
    f = open(home+'/mysql/db_config/db_port')
    db_port = int(f.readline().rstrip('\n'))
    f.close()

    # connect to database
    con = mdb.connect(host='127.0.0.1', port=db_port, user=db_user, passwd=db_passwd, db=db_name)

    cur = con.cursor()
    cur.execute(query1)

    rows = cur.fetchall()

    cur.execute(query2)
    rows2 = cur.fetchall()

    for row in rows:
        print "%s" % row

    demoids = []
    for row2 in rows2:
        demoids.append(str(row2[0]))
    instring = ''.join(demoids)

    start_time = time.time()
    cur.execute(query1 + " AND d.demographic_no IN (" + query2 +")")
    rows3 = cur.fetchone()
    print "%s" % rows3
    print time.time() - start_time, "seconds"

except mdb.Error, e:

    print "Error %d: %s" % (e.args[0], e.args[1])
    sys.exit(1)

finally:

    if con:
        con.close()
    if f:
        f.close()