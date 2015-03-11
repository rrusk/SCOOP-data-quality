#!/usr/bin/python
# -*- coding: utf-8 -*-
# Script assumes that database connection information is stored in
# ~/mysql/db_config.  Change if needed.  Variables are initialized
# this way for compatibility with prior Bash script.
#
__author__ = 'rrusk'

import os
import sys
from datetime import date
import datetime

# if import MySQLdb fails (for Ubuntu 14.04.1) run 'sudo apt-get install python-mysqldb'
import MySQLdb as Mdb

con = None
f = None

field_width = 5


def get_demographics(cursor):
    query = """SELECT d.demographic_no, d.year_of_birth, d.month_of_birth, d.date_of_birth, d.sex, d.patient_status
              FROM demographic d"""
    cursor.execute(query)
    result = cursor.fetchall()
    return result


def get_drugs(cursor, demographic_no, archived=False):
    query = """select d.ATC, d.regional_identifier as DIN, d.rx_date, d.end_date, d.long_term, d.lastUpdateDate from drugs d
               where d.demographic_no=%s and d.archived=%s"""
    cursor.execute(query, (demographic_no, archived))
    result = cursor.fetchall()
    return result


def get_problems(cursor, demographic_no):
    query = """select dx.dxresearch_code as icd9, dx.start_date from dxresearch dx
               where dx.demographic_no=%s and dx.status != 'D' and dx.coding_system='icd9'"""
    cursor.execute(query, demographic_no)
    result = cursor.fetchall()
    return result


def get_encounters(cursor, demographic_no):
    query = """select cmn.update_date, cmn.observation_date, cmn.provider_no, cmn.signing_provider_no
               from casemgmt_note cmn
               where cmn.demographic_no = %s and cmn.provider_no!=-1
               and cmn.note_id =
               (select max(cmn2.note_id) from casemgmt_note cmn2 where cmn2.uuid = cmn.uuid)
               order by cmn.observation_date"""
    cursor.execute(query, demographic_no)
    result = cursor.fetchall()
    return result


def get_echart(cursor, demographic_no):
    query = """SELECT e.timeStamp, e.providerNo
              FROM eChart e where e.demographicNo = %s"""
    cursor.execute(query, demographic_no)
    result = cursor.fetchall()
    return result


def get_provider_no(cursor, first_name, last_name):
    query = """SELECT p.provider_no
              FROM provider p where p.first_name = %s and p.last_name = %s"""
    cursor.execute(query, (first_name, last_name))
    result = cursor.fetchall()
    return result


def calculate_age(byear, bmonth, bday):
    today = date.today()
    return today.year - int(byear) - ((today.month, today.day) < (int(bmonth), int(bday)))


def had_encounter(elist, estart, eend):
    for encounter in elist:
        if estart <= encounter[1].date() <= eend:
            return True
    return False


def had_echart_encounter(elist, estart, eend):
    for encounter in elist:
        if estart <= encounter[0].date() <= eend:
            return True
    return False


def read_config(filename):
    home = os.path.expanduser("~")

    with open(os.path.join(home, "mysql", "db_config", filename), "rb") as fh:
        return fh.readline().rstrip()


try:
    # configure database connection
    db_user = read_config("db_user")
    db_passwd = read_config("db_passwd")
    db_name = read_config("db_name")
    db_port = int(read_config("db_port"))

    # connect to database
    con = Mdb.connect(host='127.0.0.1', port=db_port, user=db_user, passwd=db_passwd, db=db_name)

    cur = con.cursor()

    print("Demographics")
    demo_list = get_demographics(cur)
    print("Number of patients: " + str(len(demo_list)))
    cnt = 0
    for row in demo_list:
        if calculate_age(row[1], row[2], row[3]) > 120:
            cnt += 1
    if cnt > 0:
        print("Number of patient > 120 years: " + str(cnt))

    print("Drugs")
    drug_list = get_drugs(cur, "17900")
    print(len(drug_list))

    print("Problems")
    drug_list = get_problems(cur, "17900")
    print(len(drug_list))

    print("Encounters")
    encounter_list = get_encounters(cur, "17900")
    print(len(encounter_list))

    print("eChart Encounters")
    echart_list = get_echart(cur, "17900")
    print(len(echart_list))

    print("Had encounter in window")
    start = datetime.date.fromordinal(datetime.date.today().toordinal()-121)
    end = datetime.date.fromordinal(datetime.date.today().toordinal()-1)
    print("hadEncounter: "+str(had_encounter(encounter_list, start, end)))
    print("had eChart Encounter: "+str(had_echart_encounter(echart_list, start, end)))

except Mdb.Error as e:
    print("Error %d: %s" % (e.args[0], e.args[1]))
    sys.exit(1)

finally:
    if con:
        con.close()
