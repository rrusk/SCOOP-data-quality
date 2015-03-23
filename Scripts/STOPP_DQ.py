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
        demo_no = int(mlist_row[0])  # casemgmt_note has demographic_no as varchar(20)!!!
        if demo_no in mdict:
            mdict[demo_no].append(mlist_row[1:])
        else:
            mdict[demo_no] = [mlist_row[1:]]
    return mdict


# creates a demographics dictionary with demographic_no as key and
# value = [year_of_birth, month_of_birth, date_of_birth, sex, patient_status]
def get_demographics(cursor):
    query = """SELECT d.demographic_no, d.year_of_birth, d.month_of_birth, d.date_of_birth, d.sex, d.patient_status
              FROM demographic d"""
    cursor.execute(query)
    result = cursor.fetchall()
    return create_dict_of_demographic_nos(result)


# creates a drugs dictionary with demographic_no as key and
# value = [ATC, DIN, rx_date, end_date, long_term, lastUpdateDate, prn, provider_no]
def get_drugs(cursor, archived=False):
    query = """select d.demographic_no, d.ATC, d.regional_identifier as DIN, d.rx_date, d.end_date, d.long_term,
               d.lastUpdateDate, d.prn, d.provider_no from drugs d where d.archived=%s"""
    cursor.execute(query, archived)
    result = cursor.fetchall()
    return create_dict_by_demographic_no(result)


# creates a problem dictionary with demographic_no as key and
# value = [icd9, start_date, update_date, status]
# filters out status 'D' and only accepts icd9 problem codes
def get_dxresearch(cursor):
    query = """select dx.demographic_no, dx.dxresearch_code as icd9, dx.start_date, dx.update_date, status from dxresearch dx
               where dx.status != 'D' and dx.coding_system='icd9'"""
    cursor.execute(query)
    result = cursor.fetchall()
    return create_dict_by_demographic_no(result)


# creates an encounters dictionary based on case management notes with demographic_no as key and
# value = [update_date, observation_date, provider_no, signing_provider]
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


# creates another type of encounters dictionary based on eCharts with demographic_no as key and
# value = [timeStamp, providerNo]
def get_echart(cursor):
    query = """SELECT e.demographicNo, e.timeStamp, e.providerNo FROM eChart e"""
    cursor.execute(query)
    result = cursor.fetchall()
    return create_dict_by_demographic_no(result)


# creates list of providers with values [provider_no, first_name, last_name]
def get_providers(cursor):
    query = """SELECT p.provider_no, p.first_name, p.last_name from provider p"""
    cursor.execute(query)
    result = cursor.fetchall()
    return result


# reads csv file containing study providers listed row by row using first_name|last_name
def get_study_provider_list(csv_file):
    provider_list = []
    home = os.path.expanduser("~")
    with open(os.path.join(home, "mysql", "db_config", csv_file), 'rb') as cf:
        reader = csv.reader(cf, delimiter='|')
        for cf_row in reader:
            provider_list.append((cf_row[0].strip(), cf_row[1].strip()))
    return provider_list


# uses the providers csv file to determine provider_no values for study practitioners
def get_provider_nums(provider_list, study_provider_list):
    pnums_list = []
    for p in study_provider_list:
        for provider in provider_list:
            if provider[1].strip() == p[0].strip() and provider[2].strip() == p[1].strip():
                pnums_list.append(provider[0].strip())
    return pnums_list


# calculates patient age at the ref_date which defaults to today
def calculate_age(byear, bmonth, bday, ref_date=None):
    if byear is None or bmonth is None or bday is None:
        return None
    sdate = ref_date
    if sdate is None:
        sdate = date.today()
    return sdate.year - int(byear) - ((sdate.month, sdate.day) < (int(bmonth), int(bday)))


# takes the encounter list for a specific demographic_no and checks for any encounters between
# start and end dates
def had_encounter(elist, estart, eend):
    for encounter in elist:
        if estart <= encounter[1].date() <= eend:
            return True
    return False


# takes the encounter list for a specific demographic_no and checks for any case management note
# encounters with a specific provider between start and end dates
def had_provider_encounter(elist, plist, estart, eend):
    if elist is None:
        return False
    for encounter in elist:
        for p_no in plist:
            if encounter[2] == p_no:
                if estart <= encounter[1].date() <= eend:
                    return True
    return False


# takes the encounter_list of a specific demographic_no and checks for an eChart encounter
# between start and end dates
def had_echart_encounter(elist, estart, eend):
    for encounter in elist:
        if estart <= encounter[0].date() <= eend:
            return True
    return False


# takes the drugs list for a specific demographic_no and checks whether any prescriptions were made
# between start and end dates indicating an encounter must have occurred
def had_rx_encounter(med_list, estart, eend):
    if med_list is None:
        return False
    for prescription_encounter in med_list:
        if estart <= prescription_encounter[2] <= eend:
            return True
    return False


# takes the drugs list for a specific demographic_no and checks whether any prescriptions were made
# between start and end dates indicating an encounter with a study provider must have occurred
def had_rx_provider_encounter(med_list, plist, estart, eend):
    if med_list is None:
        return False
    for prescription_encounter in med_list:
        for p_no in plist:
            if prescription_encounter[7] == p_no:
                if estart <= prescription_encounter[2] <= eend:
                    return True
    return False


# checks whether list has specific codes.  Uses prefix matching.
# Assumes code is first field in item_list
def has_code(item_list, codes):
    if item_list is None:
        return False
    prefix_list = [code.strip().upper() for code in codes]
    prefixes = tuple(prefix_list)
    for item in item_list:
        if item[0] is not None and item[0].strip().upper().startswith(prefixes):
            return True
    return False


# checks whether the medication list has a code corresponding to specific medications
# returns true if the medication is long term or hasn't yet reached its end date.
def has_current_target_medication(med_list, codes, med_end):  # med_start, med_end):
    prefix_list = [code.strip().upper() for code in codes]
    prefixes = tuple(prefix_list)
    for med in med_list:
        if med[0] is not None and med[0].strip().upper().startswith(prefixes):
            if (med[4] == 1) or (med[3] >= med_end):  # (med[2] <= med_end and med[3] >= med_start):
                return True
    return False


# used to tune script to specific database configuration settings
def read_config(filename):
    home = os.path.expanduser("~")

    with open(os.path.join(home, "mysql", "db_config", filename), "rb") as fh:
        return fh.readline().rstrip()


# Create a demographics dictionary of patients >= 65 years.
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
        if include and (65 <= calculate_age(dno[0], dno[1], dno[2], ref_date) <= 15000):
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

    # print "  Age of demographic_no = 17757: ",
    # d17757 = demo_dict[17757]
    # print(str(calculate_age(d17757[0], d17757[1], d17757[2], start)))
    # print("    17757: " + str(d17757))
    #
    print("Drugs:")
    all_drugs = get_drugs(cur)
    print("Size of drugs: " + str(len(all_drugs)))
    # drug_list = all_drugs[17757]
    # print(len(drug_list))
    # if len(drug_list) >= 14:
    # print("  Drug: " + str(drug_list[13]))
    # print("had target drug matching c03c: " + str(has_code(drug_list, [" C03C "])))
    # print(
    # "had target drug matching c03aa, c07a, c08, c09: " + str(
    # has_code(drug_list, ["C03AA", "C07A", "C08", "C09"])))
    #     print("had target drug matching in window c03aa, c07a, c08, c09: " + str(
    #         has_current_target_medication(drug_list, ["C03AA", "C07A", "C08", "C09"], start, end)))
    # #
    print("Problems:")
    all_problems = get_dxresearch(cur)
    print("Size of dxresearch: " + str(len(all_problems)))
    # problem_list = all_problems[17757]
    # print(len(problem_list))
    # if len(problem_list) > 0:
    #     print("  Problem: " + str(problem_list[0]))
    #     print("had target problem 401: " + str(has_code(problem_list, [" 401"])))
    #
    print("Encounters:")
    enc_dict = get_encounters(cur)
    print("Size of encounter list: " + str(len(enc_dict)))
    # encounter_list = enc_dict[17757]
    # print(len(encounter_list))
    #
    # print("eChart Encounters:")
    # echart_dict = get_echart(cur)
    # print("Size of eChart list: " + str(len(echart_dict)))
    # echart_list_17757 = echart_dict[17757]
    # print(len(echart_list_17757))
    # #
    # print("Had encounter in window:")
    # print("hadEncounter: " + str(had_encounter(encounter_list, start, end)))
    # print("had eChart Encounter: " + str(had_echart_encounter(echart_list_17757, start, end)))
    # drug_list = all_drugs[17757]
    # print("Number of drug prescriptions: " + str(len(drug_list)))
    # print("had rx Encounter: " + str(had_rx_encounter(drug_list, start, end)))

    print("Testing STOPP Rule A03:")
    dx_codes_a03 = ["401"]
    any_drugs_a03 = ["C03C"]
    notany_drugs_a03 = ["C03AA", "C07A", "C08", "C09"]
    elderly_dx_a03 = {}
    for key_a03 in elderly_patients:
        row_a03 = elderly_patients[key_a03]
        default = None
        if has_code(all_problems.get(key_a03, default), dx_codes_a03):
            elderly_dx_a03[key_a03] = row_a03
    print("Number of elderly with condition(s) " + str(dx_codes_a03) + ": " + str(len(elderly_dx_a03)))
    elderly_dx_enc_a03 = {}
    elderly_dx_drug_enc_a03 = {}
    for key_a03 in elderly_dx_a03:
        row_a03 = elderly_dx_a03[key_a03]
        default = None
        encounter_list_a03 = enc_dict.get(key_a03, default)
        drug_list_a03 = all_drugs.get(key_a03, default)
        if had_provider_encounter(encounter_list_a03, provider_nos, start, end) or had_rx_provider_encounter(
                drug_list_a03,
                provider_nos,
                start, end):
            elderly_dx_enc_a03[key_a03] = row_a03
            if drug_list_a03 is not None and has_current_target_medication(drug_list_a03, any_drugs_a03,
                                                                           end) and not has_current_target_medication(
                    drug_list_a03, notany_drugs_a03, end):
                elderly_dx_drug_enc_a03[key_a03] = row_a03
                print("matches all: " + str(key_a03))
    print("Number of elderly with condition(s) " + str(dx_codes_a03) + " seen by study provider in last 4 months: "
          + str(len(elderly_dx_enc_a03)))
    print("Number of elderly with condition(s) " + str(dx_codes_a03) + " on " + str(any_drugs_a03) + " and not on " +
          str(notany_drugs_a03) + " seen by study provider in last 4 months: " + str(len(elderly_dx_drug_enc_a03)))

    for key_a03 in elderly_dx_drug_enc_a03:
        row_a03 = elderly_dx_drug_enc_a03[key_a03]
        encounter_list_a03 = enc_dict.get(key_a03, default)
        drug_list_a03 = all_drugs.get(key_a03, default)
        print("key: " + str(key_a03))
        print("  problems: " + str(len(all_problems.get(key_a03, default))))
        print("  drugs: " + str(len(drug_list_a03)))
        print("  encounter: " + str(len(encounter_list_a03)))

    print("\n\nTesting STOPP Rule B07:")
    any_drugs_b07 = ["N03AE01", "N05BA02", "N05BA05", "N05BA01", "N05CD01", "N05CD03", "N05CD08", "N05CD02"]
    print("Number of elderly patients: " + str(len(elderly_patients)))
    elderly_enc_b07 = {}
    elderly_drug_enc_b07 = {}
    for key_b07 in elderly_patients:
        row_b07 = elderly_patients[key_b07]
        default = None
        encounter_list_b07 = enc_dict.get(key_b07, default)
        drug_list_b07 = all_drugs.get(key_b07, default)
        if had_provider_encounter(encounter_list_b07, provider_nos, start, end) or had_rx_provider_encounter(
                drug_list_b07,
                provider_nos,
                start, end):
            elderly_enc_b07[key_b07] = row_b07
            if drug_list_b07 is not None and has_current_target_medication(drug_list_b07, any_drugs_b07,
                                                                           end):
                elderly_drug_enc_b07[key_b07] = row_b07
                print("matches all: " + str(key_b07))
    print("Number of elderly patients seen by study provider in last 4 months: "
          + str(len(elderly_enc_b07)))
    print("Number of elderly patients on " + str(any_drugs_b07) +
          " seen by study provider in last 4 months: " + str(len(elderly_drug_enc_b07)))

    for key_b07 in elderly_drug_enc_b07:
        row_b07 = elderly_drug_enc_b07[key_b07]
        encounter_list_b07 = enc_dict.get(key_b07, default)
        drug_list_b07 = all_drugs.get(key_b07, default)
        print("key: " + str(key_b07))
        print("  drugs: " + str(len(drug_list_b07)))
        print("  encounter: " + str(len(encounter_list_b07)))

    print("\n\nTesting STOPP Rule B08:")
    notany_dx_codes_b08 = ["295", "297", "298"]
    any_drugs_b08 = ["N05A", "N06C"]
    elderly_notany_dx_b08 = {}
    elderly_drug_b08 = {}
    for key_b08 in elderly_patients:
        row_b08 = elderly_patients[key_b08]
        default = None
        drug_list_b08 = all_drugs.get(key_b08, default)
        if drug_list_b08 is not None and has_current_target_medication(drug_list_b08, any_drugs_b08, end):
            elderly_drug_b08[key_b08] = row_b08
    print("Number of elderly on " + str(any_drugs_b08) + ": " + str(len(elderly_drug_b08)))
    elderly_drug_enc_b08 = {}
    elderly_notany_dx_drug_enc_b08 = {}
    for key_b08 in elderly_drug_b08:
        row_b08 = elderly_drug_b08[key_b08]
        default = None
        encounter_list_b08 = enc_dict.get(key_b08, default)
        drug_list_b08 = all_drugs.get(key_b08, default)
        if had_provider_encounter(encounter_list_b08, provider_nos, start, end) or had_rx_provider_encounter(
                drug_list_b08,
                provider_nos,
                start, end):
            elderly_drug_enc_b08[key_b08] = row_b08
            if not has_code(all_problems.get(key_b08, default), notany_dx_codes_b08):
                elderly_notany_dx_drug_enc_b08[key_b08] = row_b08
                print("matches all: " + str(key_b08))
    print("Number of elderly patients on " + str(any_drugs_b08) +
          " seen by study provider in last 4 months: " + str(len(elderly_drug_enc_b08)))
    line2print = "Number of elderly without condition(s) " + str(
        notany_dx_codes_b08) + " seen by study provider in last 4 months: " + str(len(elderly_notany_dx_drug_enc_b08))
    print(line2print)

    for key_b08 in elderly_notany_dx_drug_enc_b08:
        row_b08 = elderly_notany_dx_drug_enc_b08[key_b08]
        encounter_list_b08 = enc_dict.get(key_b08, default)
        drug_list_b08 = all_drugs.get(key_b08, default)
        print("key: " + str(key_b08))
        if all_problems.get(key_b08, default) is None:
            print("  problems: None")
        else:
            print("  problems: " + str(len(all_problems.get(key_b08, default))))
        print("  drugs: " + str(len(drug_list_b08)))
        print("  encounter: " + str(len(encounter_list_b08)))

    print("\n\nTesting STOPP Rule I02:")
    any_drugs_i02 = ["N02A"]
    notany_drugs_i02 = ["A06A"]
    elderly_drug_i02 = {}
    for key_i02 in elderly_patients:
        row_i02 = elderly_patients[key_i02]
        default = None
        if has_code(all_drugs.get(key_i02, default), any_drugs_i02):
            elderly_drug_i02[key_i02] = row_i02
    print("Number of elderly on " + str(any_drugs_i02) + ": " + str(len(elderly_drug_i02)))
    elderly_drug_enc_i02 = {}
    elderly_drug_notany_drug_enc_i02 = {}
    for key_i02 in elderly_drug_i02:
        row_i02 = elderly_drug_i02[key_i02]
        default = None
        encounter_list_i02 = enc_dict.get(key_i02, default)
        drug_list_i02 = all_drugs.get(key_i02, default)
        if had_provider_encounter(encounter_list_i02, provider_nos, start, end) or had_rx_provider_encounter(
                drug_list_i02,
                provider_nos,
                start, end):
            elderly_drug_enc_i02[key_i02] = row_i02
            if not has_current_target_medication(drug_list_i02, notany_drugs_i02, end):
                elderly_drug_notany_drug_enc_i02[key_i02] = row_i02
                print("matches all: " + str(key_i02))
    print("Number of elderly on " + str(any_drugs_i02) + " seen by study provider in last 4 months: "
          + str(len(elderly_drug_enc_i02)))
    print("Number of elderly on " + str(any_drugs_i02) + " and not on " +
          str(notany_drugs_i02) + " seen by study provider in last 4 months: " + str(
        len(elderly_drug_notany_drug_enc_i02)))

    for key_i02 in elderly_drug_notany_drug_enc_i02:
        row_i02 = elderly_drug_notany_drug_enc_i02[key_i02]
        encounter_list_i02 = enc_dict.get(key_i02, default)
        drug_list_i02 = all_drugs.get(key_i02, default)
        print("key: " + str(key_i02))
        print("  drugs: " + str(len(drug_list_i02)))
        print("  encounter: " + str(len(encounter_list_i02)))

    print("\n\nTesting STOPP Rule X99:")
    dx_codes_X99 = ["401"]
    any_drugs_X99 = ["C03C"]
    notany_drugs_X99 = ["C03AA", "C07A", "C08", "C09"]
    elderly_dx_X99 = {}
    for key_X99 in elderly_patients:
        row_X99 = elderly_patients[key_X99]
        default = None
        if has_code(all_problems.get(key_X99, default), dx_codes_X99):
            elderly_dx_X99[key_X99] = row_X99
    print("Number of elderly with condition(s) " + str(dx_codes_X99) + ": " + str(len(elderly_dx_X99)))
    elderly_dx_enc_X99 = {}
    elderly_dx_drug_enc_X99 = {}
    for key_X99 in elderly_dx_X99:
        row_X99 = elderly_dx_X99[key_X99]
        default = None
        encounter_list_X99 = enc_dict.get(key_X99, default)
        drug_list_X99 = all_drugs.get(key_X99, default)
        if had_provider_encounter(encounter_list_X99, provider_nos, start, end) or had_rx_provider_encounter(
                drug_list_X99,
                provider_nos,
                start, end):
            elderly_dx_enc_X99[key_X99] = row_X99
            if drug_list_X99 is not None and has_current_target_medication(drug_list_X99, any_drugs_X99,
                                                                           end) and not has_current_target_medication(
                    drug_list_X99, notany_drugs_X99, end):
                elderly_dx_drug_enc_X99[key_X99] = row_X99
                print("matches all: " + str(key_X99))
    print("Number of elderly with condition(s) " + str(dx_codes_X99) + " seen by study provider in last 4 months: "
          + str(len(elderly_dx_enc_X99)))
    print("Number of elderly with condition(s) " + str(dx_codes_X99) + " on " + str(any_drugs_X99) + " and not on " +
          str(notany_drugs_X99) + " seen by study provider in last 4 months: " + str(len(elderly_dx_drug_enc_X99)))

    for key_X99 in elderly_dx_drug_enc_X99:
        row_X99 = elderly_dx_drug_enc_X99[key_X99]
        encounter_list_X99 = enc_dict.get(key_X99, default)
        drug_list_X99 = all_drugs.get(key_X99, default)
        print("key: " + str(key_X99))
        print("  problems: " + str(len(all_problems.get(key_X99, default))))
        print("  drugs: " + str(len(drug_list_X99)))
        print("  encounter: " + str(len(encounter_list_X99)))


except Mdb.Error as e:
    print("Error %d: %s" % (e.args[0], e.args[1]))
    sys.exit(1)

finally:
    if con:
        con.close()
