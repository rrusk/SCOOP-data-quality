#!/usr/bin/python
# -*- coding: utf-8 -*-
# Script assumes that database connection information is stored in
# ~/mysql/db_config.  Change if needed.  Variables are initialized
# this way for compatibility with prior Bash script.
#
__author__ = 'rrusk'

import collections
import hashlib
import os
import sys

import MySQLdb as mdb


def read_config(filename):
    home = os.path.expanduser("~")

    with open(os.path.join(home, "mysql", "db_config", filename), "rb") as fh:
        return fh.readline().rstrip()


def get_connection():
    # configure database connection
    db_user = read_config("db_user")
    db_passwd = read_config("db_passwd")
    db_name = read_config("db_name")
    db_port = int(read_config("db_port"))

    # connect to database
    return mdb.connect(host='127.0.0.1', port=db_port, user=db_user, passwd=db_passwd, db=db_name)


def get_patients(con):
    patients = collections.defaultdict(list)

    cur = con.cursor()
    cur.execute("""SELECT demographic_no, last_name, first_name, year_of_birth, month_of_birth,
                          date_of_birth, sex, patient_status
                   FROM demographic""")

    for record in cur.fetchall():
        hasher = hashlib.sha224()

        for item in record[:-1]:
            hasher.update(str(item))

        hashkey = hasher.hexdigest()
        print hashkey

        patients[hashkey].append((record[0], record[-1]))

    return patients


def main():
    con = get_connection()

    try:
        patients = get_patients(con)
    except mdb.Error as e:
        print "Error %d: %s" % (e.args[0], e.args[1])
        sys.exit(1)
    finally:
        if con:
            con.close()

    print "Total hashkeys: %d" % len(patients)

    for hashkey, patient_info in patients.iteritems():
        if len(patient_info) > 1:
            print "Collision for hashkey: %s." % hashkey
            for i, patient in enumerate(patient_info):
                print " %d: Demographic id: %s, Patient status: %s" % (i, patient[0], patient[1])


if __name__ == "__main__":
    main()
