#!/usr/bin/python
# -*- coding: utf-8 -*-
# Script assumes that database connection information is stored in
# ~/mysql/db_config.  Change if needed.  Variables are initialized
# this way for compatibility with prior Bash script.
#
__author__ = 'rrusk'

import os
import sys
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


def calculate_age(byear, bmonth, bday, ref_date):
    # today = date.today()
    sdate = ref_date
    # return today.year - int(byear) - ((today.month, today.day) < (int(bmonth), int(bday)))
    return sdate.year - int(byear) - ((sdate.month, sdate.day) < (int(bmonth), int(bday)))


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


def had_rx_encounter(elist, estart, eend):
    for encounter in elist:
        if estart <= encounter[2] <= eend:
            return True
    return False


def read_config(filename):
    home = os.path.expanduser("~")

    with open(os.path.join(home, "mysql", "db_config", filename), "rb") as fh:
        return fh.readline().rstrip()


def mdict(mlist):
    d = {}
    for item in mlist:
        d[item[0]] = item
    return d


# Oscar's default year_of_birth is '0001' so consider age > 150 invalid
# ref_date is date on which age is to be calculated
def age_over(ddict, ref_date, check_status=True):
    dcnt = 0
    for dkey in ddict:
        dno = ddict[dkey]
        include = True
        if check_status and dno[5] != 'AC':
            include = False
        if include and (65 <= calculate_age(dno[1], dno[2], dno[3], ref_date) <= 150):
            dcnt += 1
    return dcnt


try:
    # configure database connection
    db_user = read_config("db_user")
    db_passwd = read_config("db_passwd")
    db_name = read_config("db_name")
    db_port = int(read_config("db_port"))

    start = datetime.date.fromordinal(datetime.date.today().toordinal() - 121)
    end = datetime.date.fromordinal(datetime.date.today().toordinal() - 1)

    # connect to database
    con = Mdb.connect(host='127.0.0.1', port=db_port, user=db_user, passwd=db_passwd, db=db_name)

    cur = con.cursor()

    print("Demographics")
    demo_dict = mdict(get_demographics(cur))
    print("Number of patients: " + str(len(demo_dict)))
    cnt = 0
    for key in demo_dict:
        row = demo_dict[key]
        if calculate_age(row[1], row[2], row[3], start) > 120:
            cnt += 1
            print(str(row))
    if cnt > 0:
        print("Number of patient > 120 years: " + str(cnt))

    print("Number of patients >= 65: " + str(age_over(demo_dict, start)) + " at start")
    d17900d = demo_dict[17900]
    print("17900: " + str(d17900d))
    print "Age of demo_no=17900:",
    print(str(calculate_age(d17900d[1], d17900d[2], d17900d[3], start)))

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

    print("hadEncounter: " + str(had_encounter(encounter_list, start, end)))
    print("had eChart Encounter: " + str(had_echart_encounter(echart_list, start, end)))
    drug_list = get_drugs(cur, "17900")
    print("Number of drug prescriptions: " + str(len(drug_list)))
    print("had rx Encounter: " + str(had_rx_encounter(drug_list, start, end)))

except Mdb.Error as e:
    print("Error %d: %s" % (e.args[0], e.args[1]))
    sys.exit(1)

finally:
    if con:
        con.close()
