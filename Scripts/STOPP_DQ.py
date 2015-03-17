#!/usr/bin/python
# -*- coding: utf-8 -*-
# Script assumes that database connection information is stored in
# ~/mysql/db_config.  Change if needed.  Variables are initialized
# this way for compatibility with prior Bash script.
#
__author__ = 'rrusk'

import os
import sys
import csv
import datetime
from datetime import date

# if import MySQLdb fails (for Ubuntu 14.04.1) run 'sudo apt-get install python-mysqldb'
import MySQLdb as Mdb

con = None
f = None


def create_dict_of_demographic_nos(mlist):
    mdict = {}
    for mrow in mlist:
        mdict[mrow[0]] = mrow[1:]
    return mdict


def create_dict_by_demographic_no(mlist):
    mdict = {}
    for mlist_row in mlist:
        if mlist_row[0] in mdict:
            mdict[mlist_row[0]].append(mlist_row[1:])
        else:
            mdict[mlist_row[0]] = [mlist_row[1:]]
    return mdict


def get_demographics(cursor):
    query = """SELECT d.demographic_no, d.year_of_birth, d.month_of_birth, d.date_of_birth, d.sex, d.patient_status
              FROM demographic d"""
    cursor.execute(query)
    result = cursor.fetchall()
    return create_dict_of_demographic_nos(result)


def get_drugs(cursor, archived=False):
    query = """select d.demographic_no, d.ATC, d.regional_identifier as DIN, d.rx_date, d.end_date, d.long_term,
               d.lastUpdateDate, d.prn, d.provider_no from drugs d where d.archived=%s"""
    cursor.execute(query, archived)
    result = cursor.fetchall()
    return create_dict_by_demographic_no(result)


def get_dxresearch(cursor):
    query = """select dx.demographic_no, dx.dxresearch_code as icd9, dx.start_date, dx.update_date, status from dxresearch dx
               where dx.status != 'D' and dx.coding_system='icd9'"""
    cursor.execute(query)
    result = cursor.fetchall()
    return create_dict_by_demographic_no(result)


def get_encounters(cursor):
    query = """select cmn.demographic_no, cmn.update_date, cmn.observation_date, cmn.provider_no, cmn.signing_provider_no
               from casemgmt_note cmn
               where cmn.provider_no!=-1
               and cmn.note_id =
               (select max(cmn2.note_id) from casemgmt_note cmn2 where cmn2.uuid = cmn.uuid)
               order by cmn.observation_date"""
    cursor.execute(query)
    result = cursor.fetchall()
    return create_dict_by_demographic_no(result)


def get_echart(cursor, demographic_no):
    query = """SELECT e.timeStamp, e.providerNo
              FROM eChart e where e.demographicNo = %s"""
    cursor.execute(query, demographic_no)
    result = cursor.fetchall()
    return result


def get_providers(cursor):
    query = """SELECT p.provider_no, p.first_name, p.last_name from provider p"""
    cursor.execute(query)
    result = cursor.fetchall()
    return result


def get_study_provider_list(csv_file):
    provider_list = []
    home = os.path.expanduser("~")
    with open(os.path.join(home, "mysql", "db_config", csv_file), 'rb') as cf:
        reader = csv.reader(cf, delimiter='|')
        for cf_row in reader:
            provider_list.append((cf_row[0].strip(), cf_row[1].strip()))
    return provider_list


def get_provider_nums(provider_list, study_provider_list):
    pnums_list = []
    for p in study_provider_list:
        for provider in provider_list:
            if provider[1].strip() == p[0].strip() and provider[2].strip() == p[1].strip():
                pnums_list.append(provider[0].strip())
    return pnums_list


def calculate_age(byear, bmonth, bday, ref_date=None):
    if byear is None or bmonth is None or bday is None:
        return None
    sdate = ref_date
    if sdate is None:
        sdate = date.today()
    return sdate.year - int(byear) - ((sdate.month, sdate.day) < (int(bmonth), int(bday)))


def had_encounter(elist, estart, eend):
    for encounter in elist:
        if estart <= encounter[1].date() <= eend:
            return True
    return False


def had_provider_encounter(elist, plist, estart, eend):
    if elist is None:
        return False
    for encounter in elist:
        for p_no in plist:
            if encounter[3] == p_no:
                if estart <= encounter[1].date() <= eend:
                    return True
    return False


def had_echart_encounter(elist, estart, eend):
    for encounter in elist:
        if estart <= encounter[0].date() <= eend:
            return True
    return False


def had_rx_encounter(elist, estart, eend):
    if elist is None:
        return False
    for encounter in elist:
        if estart <= encounter[2] <= eend:
            return True
    return False


def had_rx_provider_encounter(med_list, plist, estart, eend):
    if med_list is None:
        return False
    for prescription_encounter in med_list:
        for p_no in plist:
            if prescription_encounter[7] == p_no:
                if estart <= prescription_encounter[2] <= eend:
                    return True
    return False


# assumes code is first field in item_list
def has_code(item_list, codes):
    prefix_list = [code.strip().upper() for code in codes]
    prefixes = tuple(prefix_list)
    if item_list is None:
        return False
    for item in item_list:
        if item[0] is not None and item[0].strip().upper().startswith(prefixes):
            return True
    return False


def has_current_target_medication(med_list, codes, med_start, med_end):
    prefix_list = [code.strip().upper() for code in codes]
    prefixes = tuple(prefix_list)
    for med in med_list:
        if med[0] is not None and med[0].strip().upper().startswith(prefixes):
            if (med[4] == 1) or (med_start <= med[2] <= med_end):
                # print("med: " + str(med))
                return True
    return False


def read_config(filename):
    home = os.path.expanduser("~")

    with open(os.path.join(home, "mysql", "db_config", filename), "rb") as fh:
        return fh.readline().rstrip()


# Oscar's default year_of_birth is '0001' so consider age > 150 invalid
# ref_date is date on which age is to be calculated
# Currently, Oscar E2E exports only include patients with 'AC' status.
def elderly(ddict, ref_date, check_status=True):
    result = {}
    for dkey in ddict:
        dno = ddict[dkey]
        include = True
        if check_status and dno[4] != 'AC':
            include = False
        if include and (65 <= calculate_age(dno[0], dno[1], dno[2], ref_date) <= 150):
            result[dkey] = dno
    return result


try:
    # configure database connection
    db_user = read_config("db_user")
    db_passwd = read_config("db_passwd")
    db_name = read_config("db_name")
    db_port = int(read_config("db_port"))

    study_providers = get_study_provider_list("providers.csv")

    print("provider_list " + str(study_providers))

    start = datetime.date.fromordinal(datetime.date.today().toordinal() - 121)
    end = datetime.date.fromordinal(datetime.date.today().toordinal() - 1)

    # connect to database
    con = Mdb.connect(host='127.0.0.1', port=db_port, user=db_user, passwd=db_passwd, db=db_name)

    cur = con.cursor()

    print("Providers:")
    providers = get_providers(cur)
    provider_nos = get_provider_nums(providers, study_providers)
    print("provider_nos: " + str(provider_nos))

    print("Demographics:")
    demo_dict = get_demographics(cur)
    print("  Number of patients: " + str(len(demo_dict)))
    cnt = 0
    for key in demo_dict:
        row = demo_dict[key]
        if calculate_age(row[0], row[1], row[2], start) > 120:
            cnt += 1
            print("  Patient > 120 years: " + str(row))
    if cnt > 0:
        print("  Number of patient > 120 years: " + str(cnt))

    elderly_patients = elderly(demo_dict, start)
    print("  Number of patients >= 65 on " + str(start) + ": " + str(len(elderly(demo_dict, start))))

    print "  Age of demographic_no = 17900: ",
    d17900 = demo_dict[17900]
    print(str(calculate_age(d17900[0], d17900[1], d17900[2], start)))
    print("    17900: " + str(d17900))
    #
    print("Drugs:")
    all_drugs = get_drugs(cur)
    print("Size of drugs: " + str(len(all_drugs)))
    # drug_list = all_drugs[17900]
    # print(len(drug_list))
    # if len(drug_list) >= 16:
    # print("  Drug: " + str(drug_list[15]))
    # print("had target drug: " + str(has_code(drug_list, [" c07ab "])))
    #
    print("Problems:")
    all_problems = get_dxresearch(cur)
    print("Size of dxresearch: " + str(len(all_problems)))
    # problem_list = get_problems(all_problems, 17900)
    # print(len(problem_list))
    # if len(problem_list) > 0:
    # print("  Problem: " + str(problem_list[0]))
    # print("had target problem: " + str(has_code(problem_list, [" V5861"])))
    #
    print("Encounters:")
    enc_dict = get_encounters(cur)
    print("Size of encounter list: " + str(len(enc_dict)))
    # encounter_list = enc_dict["17900"]
    # print(len(encounter_list))
    #
    # print("eChart Encounters:")
    # echart_list = get_echart(cur, "17900")
    # print(len(echart_list))
    #
    # print("Had encounter in window:")
    # print("hadEncounter: " + str(had_encounter(encounter_list, start, end)))
    # print("had eChart Encounter: " + str(had_echart_encounter(echart_list, start, end)))
    # drug_list = all_drugs[17900]
    # print("Number of drug prescriptions: " + str(len(drug_list)))
    # print("had rx Encounter: " + str(had_rx_encounter(drug_list, start, end)))

    print("Testing STOPP Rule A03:")
    dx_codes = ["401"]
    any_drugs = ["C03C"]
    notany_drugs = ["C03AA", "C07A", "C08", "C09"]
    elderly_dx = {}
    for key in elderly_patients:
        row = elderly_patients[key]
        default = None
        if has_code(all_problems.get(key, default), dx_codes):
            # has_code(get_problems(all_problems, row[0]), dx_codes):
            elderly_dx[key] = row
    print("Number of elderly with condition(s) " + str(dx_codes) + ": " + str(len(elderly_dx)))
    elderly_dx_enc = {}
    elderly_dx_drug_enc = {}
    for key in elderly_dx:
        row = elderly_dx[key]
        default = None
        encounter_list = enc_dict.get(key, default)
        drug_list = all_drugs.get(key, default)
        if had_provider_encounter(encounter_list, provider_nos, start, end) or had_rx_provider_encounter(drug_list,
                                                                                                         provider_nos,
                                                                                                         start, end):
            elderly_dx_enc[key] = row
            if drug_list is not None and has_current_target_medication(drug_list, any_drugs, start,
                                                                       end) and not has_current_target_medication(
                    drug_list, notany_drugs, start, end):
                elderly_dx_drug_enc[key] = row
                print("matches all: " + str(key))
    print("Number of elderly with condition(s) " + str(dx_codes) + " seen by study provider in last 4 months: "
          + str(len(elderly_dx_enc)))
    print("Number of elderly with condition(s) " + str(dx_codes) + " on " + str(any_drugs) + " and not on " +
          str(notany_drugs) + " seen by study provider in last 4 months: " + str(len(elderly_dx_drug_enc)))

    for key in elderly_dx_drug_enc:
        row = elderly_dx_drug_enc[key]
        encounter_list = enc_dict.get(key, default)
        drug_list = all_drugs.get(key, default)
        print("key: " + str(key))
        # print("drugs: " + str(drug_list))
        #print("encounter: " + str(encounter_list))


except Mdb.Error as e:
    print("Error %d: %s" % (e.args[0], e.args[1]))
    sys.exit(1)

finally:
    if con:
        con.close()
