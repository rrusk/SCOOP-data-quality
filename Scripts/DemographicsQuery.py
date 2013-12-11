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

#    SELECT COUNT(d.demographic_no) AS Count
#    FROM demographic AS d
#    WHERE d.patient_status = 'AC' AND
#    CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) > DATE_SUB( NOW(), INTERVAL 10 YEAR ) AND
#    CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) <= DATE_SUB( NOW(), INTERVAL 0 YEAR ) AND
#    d.sex = 'M'

def query_string(lo, hi, gender):
    result = []
    result.append(" SELECT COUNT(d.demographic_no) AS Count FROM demographic AS d WHERE d.patient_status = 'AC' AND ")
    result.append(" CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) > DATE_SUB( NOW(), INTERVAL ")
    result.append(str(hi+1))
    result.append(" YEAR ) AND ")
    result.append(" CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) <= DATE_SUB( NOW(), INTERVAL ")
    result.append(str(lo))
    result.append(" YEAR) AND d.sex = '")
    result.append(str(gender))
    result.append("'")
    return ''.join(result);

def print_result(cursor, lo, hi, gender):
    cursor.execute(query_string(lo, hi, gender))
    print "%s" % cursor.fetchone()

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


    print("total_0-199 M/F/UN")
    print_result(cur, 0, 199, 'M')
    print_result(cur, 0, 199, 'F')
    print_result(cur, 0, 199, 'U')

    print("total_0-9 M/F/UN")
    print_result(cur, 0, 9, 'M')
    print_result(cur, 0, 9, 'F')
    print_result(cur, 0, 9, 'U')

    print("total_10-19 M/F/UN")
    print_result(cur, 10, 19, 'M')
    print_result(cur, 10, 19, 'F')
    print_result(cur, 10, 19, 'U')

    print("total_20-29 M/F/UN")
    print_result(cur, 20, 29, 'M')
    print_result(cur, 20, 29, 'F')
    print_result(cur, 20, 29, 'U')

    print("total_30-39 M/F/UN")
    print_result(cur, 30, 39, 'M')
    print_result(cur, 30, 39, 'F')
    print_result(cur, 30, 39, 'U')

    print("total_40-49 M/F/UN")
    print_result(cur, 40, 49, 'M')
    print_result(cur, 40, 49, 'F')
    print_result(cur, 40, 49, 'U')

    print("total_50-59 M/F/UN")
    print_result(cur, 50, 59, 'M')
    print_result(cur, 50, 59, 'F')
    print_result(cur, 50, 59, 'U')

    print("total_60-69 M/F/UN")
    print_result(cur, 60, 69, 'M')
    print_result(cur, 60, 69, 'F')
    print_result(cur, 60, 69, 'U')

    print("total_70-79 M/F/UN")
    print_result(cur, 70, 79, 'M')
    print_result(cur, 70, 79, 'F')
    print_result(cur, 70, 79, 'U')

    print("total_80-89 M/F/UN")
    print_result(cur, 80, 89, 'M')
    print_result(cur, 80, 89, 'F')
    print_result(cur, 80, 89, 'U')

    print("total_90-99 M/F/UN")
    print_result(cur, 90, 99, 'M')
    print_result(cur, 90, 99, 'F')
    print_result(cur, 90, 99, 'U')

    print("total_100-109 M/F/UN")
    print_result(cur, 100, 109, 'M')
    print_result(cur, 100, 109, 'F')
    print_result(cur, 100, 109, 'U')

    print("total_110-119 M/F/UN")
    print_result(cur, 110, 119, 'M')
    print_result(cur, 110, 119, 'F')
    print_result(cur, 110, 119, 'U')

    print("total_120-129 M/F/UN")
    print_result(cur, 120, 129, 'M')
    print_result(cur, 120, 129, 'F')
    print_result(cur, 120, 129, 'U')

except mdb.Error, e:

    print "Error %d: %s" % (e.args[0], e.args[1])
    sys.exit(1)

finally:

    if con:
        con.close()
    if f:
        f.close()