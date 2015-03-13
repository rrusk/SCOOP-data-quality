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
from datetime import date

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


def get_drugs(cursor, archived=False):
    query = """select d.demographic_no, d.ATC, d.regional_identifier as DIN, d.rx_date, d.end_date, d.long_term,
               d.lastUpdateDate, d.prn from drugs d where d.archived=%s"""
    cursor.execute(query, archived)
    result = cursor.fetchall()
    drugs_dict = {}
    for d_row in result:
        if d_row[0] in drugs_dict:
            drugs_dict[d_row[0]].append(d_row[1:])
        else:
            drugs_dict[d_row[0]] = [d_row[1:]]
    return drugs_dict


def get_dxresearch(cursor):
    query = """select dx.demographic_no, dx.dxresearch_code as icd9, dx.start_date, dx.update_date, status from dxresearch dx
               where dx.status != 'D' and dx.coding_system='icd9'"""
    cursor.execute(query)
    result = cursor.fetchall()
    return result


def get_encounters(cursor):
    query = """select cmn.demographic_no, cmn.update_date, cmn.observation_date, cmn.provider_no, cmn.signing_provider_no
               from casemgmt_note cmn
               where cmn.provider_no!=-1
               and cmn.note_id =
               (select max(cmn2.note_id) from casemgmt_note cmn2 where cmn2.uuid = cmn.uuid)
               order by cmn.observation_date"""
    cursor.execute(query)
    result = cursor.fetchall()
    encounter_dict = {}
    for d_row in result:
        if d_row[0] in encounter_dict:
            encounter_dict[d_row[0]].append(d_row[1:])
        else:
            encounter_dict[d_row[0]] = [d_row[1:]]
    return encounter_dict


# def get_encounters2(cursor, demographic_no):
#     query = """select cmn.update_date, cmn.observation_date, cmn.provider_no, cmn.signing_provider_no
#                from casemgmt_note cmn
#                where cmn.demographic_no = %s and cmn.provider_no!=-1
#                and cmn.note_id =
#                (select max(cmn2.note_id) from casemgmt_note cmn2 where cmn2.uuid = cmn.uuid)
#                order by cmn.observation_date"""
#     cursor.execute(query, demographic_no)
#     result = cursor.fetchall()
#     return result


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


def calculate_age(byear, bmonth, bday, ref_date=None):
    sdate = ref_date
    if sdate is None:
        sdate = date.today()
    return sdate.year - int(byear) - ((sdate.month, sdate.day) < (int(bmonth), int(bday)))


def get_problems(plist, demographic_no):
    result = []
    for problem in plist:
        if problem[0] == demographic_no:
            result.append(problem[1:])
    return result


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


# assumes code is first field in item_list
def has_code(item_list, codes):
    prefix_list = [code.strip().upper() for code in codes]
    prefixes = tuple(prefix_list)
    for item in item_list:
        if item[0].strip().upper().startswith(prefixes):
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
# Currently, Oscar E2E exports only include patients with 'AC' status.
def elderly(ddict, ref_date, check_status=True):
    result = {}
    for dkey in ddict:
        dno = ddict[dkey]
        include = True
        if check_status and dno[5] != 'AC':
            include = False
        if include and (65 <= calculate_age(dno[1], dno[2], dno[3], ref_date) <= 150):
            result[dno[0]] = dno
    return result


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

    print("Demographics:")
    demo_dict = mdict(get_demographics(cur))
    print("  Number of patients: " + str(len(demo_dict)))
    cnt = 0
    for key in demo_dict:
        row = demo_dict[key]
        if calculate_age(row[1], row[2], row[3], start) > 120:
            cnt += 1
            print("  Patient > 120 years: " + str(row))
    if cnt > 0:
        print("  Number of patient > 120 years: " + str(cnt))

    print("  Number of patients >= 65 on " + str(start) + ": " + str(len(elderly(demo_dict, start))))

    print "  Age of demographic_no = 17900: ",
    d17900 = demo_dict[17900]
    print(str(calculate_age(d17900[1], d17900[2], d17900[3], start)))
    print("    17900: " + str(d17900))

    print("Drugs:")
    all_drugs = get_drugs(cur)
    drug_list = all_drugs[17900]
    print(len(drug_list))
    if len(drug_list) >= 16:
        print("  Drug: " + str(drug_list[15]))
    print("had target drug: " + str(has_code(drug_list, [" c07ab "])))

    print("Problems:")
    all_problems = get_dxresearch(cur)
    print("Size of dxresearch: " + str(len(all_problems)))
    problem_list = get_problems(all_problems, 17900)
    print(len(problem_list))
    if len(problem_list) > 0:
        print("  Problem: " + str(problem_list[0]))
    print("had target problem: " + str(has_code(problem_list, [" V5861"])))

    print("Encounters:")
    enc_dict = get_encounters(cur)
    print(len(enc_dict))
    encounter_list = enc_dict["17900"]
    print(len(encounter_list))

    print("eChart Encounters:")
    echart_list = get_echart(cur, "17900")
    print(len(echart_list))

    print("Had encounter in window:")

    print("hadEncounter: " + str(had_encounter(encounter_list, start, end)))
    print("had eChart Encounter: " + str(had_echart_encounter(echart_list, start, end)))
    drug_list = all_drugs[17900]
    print("Number of drug prescriptions: " + str(len(drug_list)))
    print("had rx Encounter: " + str(had_rx_encounter(drug_list, start, end)))

    print("Testing STOPP Rule A03:")
    dx_codes = ["401"]
    any_drugs = ["C03C"]
    notany_drugs = ["C03AA", "C07A", "C08", "C09"]
    elderly_dict = elderly(demo_dict, start)
    elderly_dx = {}
    for key in elderly_dict:
        row = elderly_dict[key]
        if has_code(get_problems(all_problems, row[0]), dx_codes):
            elderly_dx[row[0]] = row
    print("Number of elderly with condition(s) " + str(dx_codes) + ": " + str(len(elderly_dx)))
    elderly_dx_enc = {}
    for key in elderly_dx:
        row = elderly_dx[key]
        encounter_list = enc_dict[str(row[0])]
        if had_encounter(encounter_list, start, end):
            elderly_dx_enc[row[0]] = row
    print("Number of elderly with condition(s) " + str(dx_codes) + " seen in last 4 months: "
          + str(len(elderly_dx_enc)))


except Mdb.Error as e:
    print("Error %d: %s" % (e.args[0], e.args[1]))
    sys.exit(1)

finally:
    if con:
        con.close()
