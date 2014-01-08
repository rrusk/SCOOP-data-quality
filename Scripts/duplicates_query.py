#!/usr/bin/python
# -*- coding: utf-8 -*-
# Script assumes that database connection information is stored in
# ~/mysql/db_config.  Change if needed.  Variables are initialized
# this way for compatibility with prior Bash script.
#
__author__ = 'drusk and rrusk'

import collections
import hashlib
import os
import sys

import MySQLdb as mdb

query1 = """SELECT demographic_no, hin, last_name, first_name, year_of_birth, month_of_birth,
                          date_of_birth, sex, patient_status
                   FROM demographic"""

query2 = """SELECT demographic_no, last_name, first_name, year_of_birth, month_of_birth,
                          date_of_birth, patient_status
                   FROM demographic"""

query3 = """SELECT demographic_no, hin, patient_status
                   FROM demographic"""

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


def get_patients(con, query):
    patients = collections.defaultdict(list)

    cur = con.cursor()
    cur.execute(query)

    for record in cur.fetchall():
        hasher = hashlib.sha224()

        for item in record[1:-1]:
            if item is None:
                continue
            
            hasher.update(str(item))

        hashkey = hasher.hexdigest()
        #print hashkey

        patients[hashkey].append((record[0], record[-1]))

    return patients


def main():
    con = get_connection()

    try:
        patients = get_patients(con, query1)
        patients2 = get_patients(con, query2)
        patients3 = get_patients(con, query3)
    except mdb.Error as e:
        print "Error %d: %s" % (e.args[0], e.args[1])
        sys.exit(1)
    finally:
        if con:
            con.close()

    print "Total hashkeys based on hin, last name, first name, birth date and gender: %d" % len(patients)

    for hashkey, patient_info in patients.iteritems():
        if len(patient_info) > 1:
            print "Collision for hin, last name, first name, birth date and gender: %s." % hashkey
            for i, patient in enumerate(patient_info):
                print " %d: demographic_no: %s, patient_status: %s" % (i, patient[0], patient[1])


    print "\n\nTotal hashkeys based on last name, first name and birth date: %d" % len(patients2)

    for hashkey, patient_info in patients2.iteritems():
        if len(patient_info) > 1:
            print "Collision for last name, first name and birth date: %s." % hashkey
            for i, patient in enumerate(patient_info):
                print " %d: demographic_no: %s, patient_status: %s" % (i, patient[0], patient[1])

    print "\n\nTotal hashkeys based on hin: %d" % len(patients3)

    for hashkey, patient_info in patients3.iteritems():
        if len(patient_info) > 1:
            print "Collision for hin: %s." % hashkey
            for i, patient in enumerate(patient_info):
                print " %d: demographic_no: %s, patient_status: %s" % (i, patient[0], patient[1])


if __name__ == "__main__":
    main()
