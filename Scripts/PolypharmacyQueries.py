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

without_prn = " AND dr.prn IN (0)"
with_prn = None
distinct = "DISTINCT"
not_distinct = None
whole_population = 'whole_population'
demographic_id = None

def target_group(pop=demographic_id):
    result = []
    result.append("SELECT")
    if pop is whole_population:
        result.append(" COUNT(")
    result.append(" d.demographic_no")
    if pop is whole_population:
        result.append(")")
    result.append(" FROM demographic AS d WHERE d.patient_status = 'AC' AND")
    result.append(" CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) <")
    result.append(" DATE_SUB( NOW(), INTERVAL 64 YEAR )")
    if pop is demographic_id:
        result.append(" AND d.demographic_no = %s")
    return ''.join(result)

def polypharmacy_string(without_prn_parm, distinct_parm):
    result = []
    result.append("SELECT dr.demographic_no FROM drugs AS dr WHERE dr.archived = 0")
    if without_prn_parm is without_prn:
        result.append(without_prn)
    result.append(" AND dr.regional_identifier IS NOT NULL AND dr.regional_identifier != '' ")
    result.append(" AND dr.ATC IS NOT NULL AND dr.ATC != ''")
    result.append(" AND rx_date <= NOW() AND")
    result.append(" (DATE_ADD(dr.rx_date, INTERVAL(DATEDIFF(dr.end_date,dr.rx_date)*1.2) DAY)) >= NOW()")
    result.append(" GROUP BY dr.demographic_no")
    result.append(" HAVING COUNT(")
    if distinct_parm is distinct:
        result.append(distinct)
    result.append(" dr.regional_identifier) >= %s")
    return ''.join(result)

def print_result(cur, prn, distinct_parm, num_drugs):
    if prn is with_prn:
        if distinct_parm is distinct:
            cur.execute(polypharmacy_string(with_prn, distinct), str(num_drugs))
        else:
            cur.execute(polypharmacy_string(with_prn, not_distinct), str(num_drugs))
    else:
        if distinct_parm is distinct:
            cur.execute(polypharmacy_string(without_prn, distinct), str(num_drugs))
        else:
            cur.execute(polypharmacy_string(without_prn, not_distinct), str(num_drugs))
    rows = cur.fetchall()

    demoids = []
    for row in rows:
        demoids.append(str(row[0]))

    polycount = []
    for demoid in demoids:
        cur.execute(target_group(), demoid) # prepared statement
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

    print "target population size:",
    cur.execute(target_group(whole_population))
    print cur.fetchone()[0]
    print
    print "5 meds, with prn, not distinct /"
    print "5 meds, without prn, not distinct /"
    print "5 meds, with prn, distinct /"
    print "5 meds, without prn, distinct /"
    print "10 meds, with prn, not distinct /"
    print "10 meds, without prn, not distinct /"
    print "10 meds, with prn, distinct /"
    print "10 meds, without prn, distinct"
    print
    start_time = time.time()
    print_result(cur, with_prn, not_distinct, 5)
    print_result(cur, without_prn, not_distinct, 5)
    print_result(cur, with_prn, distinct, 5)
    print_result(cur, without_prn, distinct, 5)
    print_result(cur, with_prn, not_distinct, 10)
    print_result(cur, without_prn, not_distinct, 10)
    print_result(cur, with_prn, distinct, 10)
    print_result(cur, without_prn, distinct, 10)
    print
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