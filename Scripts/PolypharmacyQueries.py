#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'rrusk'

import _mysql
import sys

try:
    from os.path import expanduser
    home = expanduser("~")

    f = open(home+'/mysql/db_name')
    db_name = f.readline()
    f.close()
    f = open(home+'/mysql/passwd')
    passwd = f.readline()
    f.close()

    con = _mysql.connect('127.0.0.1', 'oscarb', passwd, db_name)

    con.query("SELECT VERSION()")
    result = con.use_result()

    print "MySQL version: %s" % \
        result.fetch_row()[0]

except _mysql.Error, e:

    print "Error %d: %s" % (e.args[0], e.args[1])
    sys.exit(1)

finally:

    if con:
        con.close()
    if f:
        f.close()