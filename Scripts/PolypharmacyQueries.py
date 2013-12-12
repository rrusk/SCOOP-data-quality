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

polypharmacy = ("SELECT dr.demographic_no FROM drugs AS dr "
          "WHERE dr.archived = 0 AND dr.regional_identifier IS NOT NULL AND "
            "dr.regional_identifier != '' AND dr.ATC IS NOT NULL AND "
            "dr.ATC != '' AND rx_date <= NOW() AND "
            "(DATE_ADD(dr.rx_date, INTERVAL(DATEDIFF(dr.end_date,dr.rx_date)*1.2) DAY)) >= NOW() "
          "GROUP BY dr.demographic_no "
          "HAVING COUNT(DISTINCT dr.regional_identifier) >= ")

polypharmacy_nonunique = ("SELECT dr.demographic_no FROM drugs AS dr "
          "WHERE dr.archived = 0 AND dr.regional_identifier IS NOT NULL AND "
            "dr.regional_identifier != '' AND dr.ATC IS NOT NULL AND "
            "dr.ATC != '' AND rx_date <= NOW() AND "
            "(DATE_ADD(dr.rx_date, INTERVAL(DATEDIFF(dr.end_date,dr.rx_date)*1.2) DAY)) >= NOW() "
          "GROUP BY dr.demographic_no "
          "HAVING COUNT(dr.regional_identifier) >= ")

polypharmacy_without_prn = ("SELECT dr.demographic_no FROM drugs AS dr "
          "WHERE dr.archived = 0 AND dr.prn IN (0) AND dr.regional_identifier IS NOT NULL AND "
            "dr.regional_identifier != '' AND dr.ATC IS NOT NULL AND "
            "dr.ATC != '' AND rx_date <= NOW() AND "
            "(DATE_ADD(dr.rx_date, INTERVAL(DATEDIFF(dr.end_date,dr.rx_date)*1.2) DAY)) >= NOW() "
          "GROUP BY dr.demographic_no "
          "HAVING COUNT(DISTINCT dr.regional_identifier) >= ")


polypharmacy_nonunique_without_prn = ("SELECT dr.demographic_no FROM drugs AS dr "
          "WHERE dr.archived = 0 AND dr.prn IN (0) AND dr.regional_identifier IS NOT NULL AND "
            "dr.regional_identifier != '' AND dr.ATC IS NOT NULL AND "
            "dr.ATC != '' AND rx_date <= NOW() AND "
            "(DATE_ADD(dr.rx_date, INTERVAL(DATEDIFF(dr.end_date,dr.rx_date)*1.2) DAY)) >= NOW() "
          "GROUP BY dr.demographic_no "
          "HAVING COUNT(dr.regional_identifier) >= ")


target_group = ("SELECT d.demographic_no FROM demographic AS d WHERE d.patient_status = 'AC' AND "
          "CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) < "
          "DATE_SUB( NOW(), INTERVAL 64 YEAR ) AND d.demographic_no = ")

without_prn = "without_prn"
with_prn = "with_prn"
unique = 'unique'
not_unique = 'not_unique'

def print_result(cur, num_drugs, prn, unq):
    if prn is with_prn:
        if unq is unique:
            cur.execute(polypharmacy + str(num_drugs))
        else:
            cur.execute(polypharmacy_nonunique + str(num_drugs))
    else:
        if unq is unique:
            cur.execute(polypharmacy_without_prn + str(num_drugs))
        else:
            cur.execute(polypharmacy_nonunique_without_prn + str(num_drugs))
    rows = cur.fetchall()

    demoids = []
    for row in rows:
        demoids.append(str(row[0]))

    polycount = []
    for demoid in demoids:
        cur.execute(target_group + demoid)
        rows = cur.fetchall()
        for row in rows:
            polycount.append(row)
    print len(polycount),

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

    print "5 meds, with prn, nonunique /"
    print "5 meds, without prn, nonunique /"
    print "5 meds, with prn, unique /"
    print "5 meds, without prn, unique /"
    print "10 meds, with prn, nonunique /"
    print "10 meds, without prn, nonunique /"
    print "10 meds, with prn, unique /"
    print "10 meds, without prn, unique"

    start_time = time.time()
    print_result(cur, 5, with_prn, not_unique)
    print_result(cur, 5, without_prn, not_unique)
    print_result(cur, 5, with_prn, unique)
    print_result(cur, 5, without_prn, unique)
    print_result(cur, 10, with_prn, not_unique)
    print_result(cur, 10, without_prn, not_unique)
    print_result(cur, 10, with_prn, unique)
    print_result(cur, 10, without_prn, unique)
    print
    print time.time() -  start_time, "seconds"

except mdb.Error, e:

    print "Error %d: %s" % (e.args[0], e.args[1])
    sys.exit(1)

finally:

    if con:
        con.close()
    if f:
        f.close()