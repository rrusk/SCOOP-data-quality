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

field_width = 5

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
    result.append(str(hi))
    result.append(" YEAR ) AND ")
    result.append(" CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) <= DATE_SUB( NOW(), INTERVAL ")
    result.append(str(lo))
    result.append(" YEAR) AND d.sex ")
    result.append(str(gender))
    return ''.join(result);

def print_result(cursor, lo, hi, gender):
    cursor.execute(query_string(lo, hi, gender))
    print "%s" % str(cursor.fetchone()[0]).rjust(field_width),

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

    print("Demographics")
    print('M'.rjust(field_width)),
    print('F'.rjust(field_width)),
    print('Other'.rjust(field_width)),
    print(' Age Range'.ljust(3*field_width))
    print_result(cur, 0, 130, " in ('M')")
    print_result(cur, 0, 130, " in ('F')")
    print_result(cur, 0, 130, " not in ('M','F')")
    print("[0, 130)")
    print("")

    for indx in range(0, 130, 10):
        print_result(cur, indx, indx+10, " in ('M')")
        print_result(cur, indx, indx+10, " in ('F')")
        print_result(cur, indx, indx+10, " not in ('M','F')")
        print("[" + str(indx) + ", " + str(indx+10) + ")")

except mdb.Error, e:

    print "Error %d: %s" % (e.args[0], e.args[1])
    sys.exit(1)

finally:

    if con:
        con.close()
    if f:
        f.close()