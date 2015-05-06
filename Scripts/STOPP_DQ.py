#!/usr/bin/python
# -*- coding: utf-8 -*-
# Script assumes that database connection information is stored in
# ~/mysql/db_config.  Change if needed.  Variables are initialized
# this way for compatibility with prior Bash script.
#
import sys

__author__ = 'rrusk'

import os
import csv
import datetime
from datetime import date
import collections
# from collections import defaultdict

# if import MySQLdb fails (for Ubuntu 14.04.1) run 'sudo apt-get install python-mysqldb'
import MySQLdb as Mdb

# if import dateutil.relativedelta fails run 'sudo apt-get install python-dateutil'
from dateutil.relativedelta import relativedelta

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


# def create_med_dict(mlist):
# mdict = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
#     for mlist_row in mlist:
#         mdict[mlist_row[0]][mlist_row[2]] = [mlist_row[1:]]
#     return mdict
#

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
               d.lastUpdateDate, d.prn, d.provider_no, d.BN, d.GN from drugs d where d.archived=%s
               order by d.demographic_no asc, DIN asc, d.BN asc, d.GN asc, d.rx_date desc"""
    cursor.execute(query, archived)
    result = cursor.fetchall()
    return create_dict_by_demographic_no(result)


# # creates a drugs dictionary with demographic_no, DIN as key and
# # value = [ATC, DIN, rx_date, end_date, long_term, lastUpdateDate, prn, provider_no]
# def get_drugs2(cursor, archived=False):
#     query = """select d.demographic_no, d.ATC, d.regional_identifier as DIN, d.rx_date, d.end_date, d.long_term,
#                d.lastUpdateDate, d.prn, d.provider_no, d.BN, d.GN from drugs d where d.archived=%s
#                order by d.demographic_no asc, DIN asc, d.rx_date desc, d.BN, d.GN, d.long_term desc"""
#     cursor.execute(query, archived)
#     result = cursor.fetchall()
#     return create_med_dict(result)
#

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
               where cmn.note_id =
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


# # get elderly patients with active status who were 65 years as of 4 months ago yesterday using direct SQL query
# def get_elderly_count_4months_ago(cursor):
#     query = """SELECT COUNT(d.demographic_no) AS Count FROM demographic AS d
#                WHERE d.patient_status = 'AC' AND d.year_of_birth is not NULL
#                AND d.month_of_birth is not NULL AND d.date_of_birth is not NULL
#                AND d.month_of_birth >= 1 AND d.month_of_birth <= 12
#                AND d.date_of_birth >= 1 AND d.date_of_birth <= 31
#                AND CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) <=
#                DATE_SUB( DATE_SUB(DATE_SUB(NOW(), INTERVAL 1 DAY), INTERVAL 4 MONTH), INTERVAL 65 YEAR);"""
#     cursor.execute(query)
#     result = cursor.fetchall()
#     return int(result[0][0])


# general query used for test purposes
def get_query_results(cursor, query):
    cursor.execute(query)
    return cursor.fetchall()


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


# checks if birthdate is potentially valid
def is_impossible_birthdate(byear, bmonth, bday):
    if byear is None or bmonth is None or bday is None or int(bmonth) < 1 or int(bmonth) > 12 or int(bday) < 1 or int(
            bday) > 31:
        return False
    return True


# checks whether string in format like 'YYYY-MM-DD' is a valid date
# A date like '2003-12-23' is valid but '2003-12-00' is not valid.
def is_valid_date(date_text):
    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
        return False


# calculates patient age at the ref_date which defaults to today
def calculate_age(byear, bmonth, bday, ref_date=None):
    if not is_impossible_birthdate(byear, bmonth, bday):
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
        if estart <= encounter[1].date() <= eend:
            for p_no in plist:
                if encounter[2] == p_no:
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
# between start and end dates indicating an encounter with a study provider must have occurred
def had_rx_provider_encounter(med_list, plist, estart, eend):
    if med_list is None:
        return False
    for prescription_encounter in med_list:
        if estart <= prescription_encounter[2] <= eend:
            for p_no in plist:
                if prescription_encounter[7] == p_no:
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


# check whether patient has active status
def is_active(demographic_dict, demographic_no):
    default = None
    result = demographic_dict.get(demographic_no, default)
    if result is None:
        print("demographic_no missing from demographics: " + str(demographic_no))
        return False
    else:
        return result[4] == 'AC'


# checks whether the medication list has a code corresponding to specific medications
# returns true if the medication is long term or hasn't yet reached its end date.
# Expects medications sorted by DIN so that only the long-term flag of only the most
# recent medication by DIN is checked (for consistency with Oscar E2E export)
def has_current_target_medication(med_list, codes, med_end):  # med_start, med_end):
    prefix_list = [code.strip().upper() for code in codes]
    prefixes = tuple(prefix_list)
    previous_din = None
    for med in med_list:
        if med[2] > med_end:
            continue  # ignore medications prescribed after reference date
        if med[0] is not None and med[0].strip().upper().startswith(prefixes):
            previous_din = med[0]
            if (med[4] == 1) or (med[2] <= med_end <= med[3]):
                return True
            elif med[2] <= med_end <= med[3]:
                return True
    return False


def is_prn(med):
    if med[6] == 1:
        return True
    return False


def is_long_term(med):
    if med[4] == 1:
        return True
    return False


def is_coded(med):
    if med[0] == '' or med[0] == ' ' or med[0] == '   ' or med[0] is None or 'null' in med[0] \
            or med[1] == '' or med[1] is None or ' ' in med[1] or 'null' in med[1]:
        return False
    return True


# Checks whether the medication is long-term or hasn't reached its end date
# Applies a duration multipler.
def is_current_medication(med, ref_date, duration_multiplier=1.0, prn_multiplier=1.0):
    # print("ref_date: " + str(ref_date))
    # print("med[2]: " + str(med[2]))
    #
    # Protects against NULL rx_date, end_date.
    if med[2] is None or med[3] is None:
        return False
    # If ref_date is before medication start date return false; this tests whether
    # the prescription was made after the study reference date.
    if med[2] > ref_date:
        return False
    med_start = med[2]
    med_end = med[3]
    multiplier = duration_multiplier
    if is_prn(med):
        multiplier = prn_multiplier
    try:
        tdelta = med_end - med_start
    except ValueError:
        print "DEBUG: ", str(med)
        return False
    med_end_mod = med_start + datetime.timedelta(seconds=multiplier * tdelta.total_seconds())
    # if long-term or between med start and end dates return true
    if is_long_term(med) or (ref_date <= med_end_mod):
        return True
    return False


# used to tune script to specific database configuration settings
def read_config(filename):
    home = os.path.expanduser("~")

    with open(os.path.join(home, "mysql", "db_config", filename), "rb") as fh:
        return fh.readline().rstrip()


def active_patients(ddict):
    result = {}
    for dkey in ddict:
        if is_active(ddict, dkey):
            result[dkey] = ddict[dkey]
    return result


# Create a demographics dictionary of patients >= 65 years.
# Oscar's default year_of_birth is '0001' so consider age > 150 invalid
# ref_date is date on which age is to be calculated
# Currently, Oscar E2E exports only include patients with 'AC' status.
def elderly(ddict, ref_date, check_status=True):
    result = {}
    for dkey in ddict:
        dno = ddict[dkey]
        include = True
        if check_status and not is_active(ddict, dkey):
            include = False
        if include and (65 <= calculate_age(dno[0], dno[1], dno[2], ref_date) <= 150):
            result[dkey] = dno
    return result


# Create a drugs dictionary for active patients.
# Currently, Oscar E2E exports only include patients with 'AC' status.
def relevant_drugs(demographic_dict, drug_dict):
    result = {}
    for dkey in drug_dict:
        if is_active(demographic_dict, dkey):
            result[dkey] = drug_dict[dkey]
    return result


def calculated_active_patients(end_date, patient_dict, encounter_dict, med_dict=None):
    result = {}
    start24monthsago = end_date + relativedelta(months=-24)
    default = None
    for dkey in patient_dict:
        if is_active(patient_dict, dkey):
            edict = encounter_dict.get(dkey, default)
            mlist = None
            if med_dict:
                mlist = med_dict.get(dkey, default)
            if (edict and had_encounter(edict, start24monthsago, end_date)) or \
                    (mlist and had_rx_encounter(mlist, start24monthsago, end_date)):
                result[dkey] = patient_dict[dkey]
    return result


def print_stats(problem_dict, drug_dict, encounter_dict, numerator_dict):
    ordered_dict = collections.OrderedDict(sorted(numerator_dict.items()))
    for key in ordered_dict:
        default = None
        encounter_list = encounter_dict.get(key, default)
        drug_list = drug_dict.get(key, default)
        print("key: " + str(key)),
        if problem_dict is None:
            print("\t  problems: NA"),
        elif problem_dict.get(key, default) is None:
            print("\t  problems: 0"),
        else:
            print("\t  problems: " + str(len(problem_dict.get(key, default)))),
        print("\t  drugs: " + str(len(drug_list))),
        if encounter_list is None:
            print("\t  encounter: 0")
        else:
            print("\t  encounter: " + str(len(encounter_list)))


# Denominator includes elderly patients with dxcodes from anyproblem_list.
# Numerator includes patients selected from denominator with any drug from anydrug_list and
# no drug from notanydrug_list.
def d_anyproblem_n_anydrug_notanydrug(patient_dict, problem_dict, drug_dict, encounter_dict, anyproblem_list,
                                      anydrug_list,
                                      notanydrug_list, provider_list, study_start, study_end):
    elderly_dx = {}
    for key in patient_dict:
        row = patient_dict[key]
        default = None
        if has_code(problem_dict.get(key, default), anyproblem_list):
            elderly_dx[key] = row
    print("Number of elderly with condition(s) " + str(anyproblem_list) + ": " + str(len(elderly_dx)))
    denominator_dict = {}
    numerator_dict = {}
    for key in elderly_dx:
        row = elderly_dx[key]
        default = None
        encounter_list = encounter_dict.get(key, default)
        drug_list = drug_dict.get(key, default)
        if had_provider_encounter(encounter_list, provider_list, study_start, study_end) or had_rx_provider_encounter(
                drug_list,
                provider_list,
                study_start, study_end):
            denominator_dict[key] = row
            if drug_list is not None and has_current_target_medication(drug_list, anydrug_list,
                                                                       study_end) and not has_current_target_medication(
                    drug_list, notanydrug_list, study_end):
                numerator_dict[key] = row
    print("Number of elderly with condition(s) " + str(anyproblem_list) + " seen by study provider in last 4 months: "
          + str(len(denominator_dict)))
    print("Number of elderly with condition(s) " + str(anyproblem_list) + " on " + str(anydrug_list) + " and not on " +
          str(notanydrug_list) + " seen by study provider in last 4 months: " + str(len(numerator_dict)))
    print_stats(problem_dict, drug_dict, encounter_dict, numerator_dict)


# Denominator includes elderly patients.
# Numerator includes patients selected from denominator with any drug from anydrug_list.
def d_n_anydrug(patient_dict, drug_dict, encounter_dict, anydrug_list, provider_list, study_start, study_end):
    print("Number of elderly patients: " + str(len(patient_dict)))
    denominator_dict = {}
    numerator_dict = {}
    for key in patient_dict:
        row = patient_dict[key]
        default = None
        encounter_list = encounter_dict.get(key, default)
        drug_list = drug_dict.get(key, default)
        if had_provider_encounter(encounter_list, provider_list, study_start, study_end) or had_rx_provider_encounter(
                drug_list,
                provider_list,
                study_start, study_end):
            denominator_dict[key] = row
            if drug_list is not None and has_current_target_medication(drug_list, anydrug_list, study_end):
                numerator_dict[key] = row
    print("Number of elderly patients seen by study provider in last 4 months: " + str(len(denominator_dict)))
    print("Number of elderly patients on " + str(anydrug_list) +
          " seen by study provider in last 4 months: " + str(len(numerator_dict)))
    print_stats(None, drug_dict, encounter_dict, numerator_dict)


# Denominator includes elderly patients with any drug from anydrug_list.
# Numerator includes patients selected from denominator with no problem from notanyproblem_list.
def d_anydrug_n_notanyproblem(patient_dict, problem_dict, drug_dict, encounter_dict, anydrug_list, notanyproblem_list,
                              provider_list, study_start, study_end):
    elderly_drug = {}
    for key in patient_dict:
        row = patient_dict[key]
        default = None
        drug_list = drug_dict.get(key, default)
        if drug_list is not None and has_current_target_medication(drug_list, anydrug_list, study_end):
            elderly_drug[key] = row
    print("Number of elderly on " + str(anydrug_list) + ": " + str(len(elderly_drug)))
    demoninator_dict = {}
    numerator_dict = {}
    for key in elderly_drug:
        row = elderly_drug[key]
        default = None
        encounter_list = encounter_dict.get(key, default)
        drug_list = drug_dict.get(key, default)
        if had_provider_encounter(encounter_list, provider_list, study_start, study_end) or had_rx_provider_encounter(
                drug_list,
                provider_list,
                study_start, study_end):
            demoninator_dict[key] = row
            if not has_code(problem_dict.get(key, default), notanyproblem_list):
                numerator_dict[key] = row
    print("Number of elderly patients on " + str(anydrug_list) +
          " seen by study provider in last 4 months: " + str(len(demoninator_dict)))
    print("Number of elderly on " + str(anydrug_list) + " without condition(s) " + str(notanyproblem_list)),
    print(" seen by study provider in last 4 months: " + str(len(numerator_dict)))
    print_stats(problem_dict, drug_dict, encounter_dict, numerator_dict)


# Denominator includes elderly patients with any drug from anydrug_list.
# Numerator includes patients selected from denominator with no drug from notanydrug_list.
def d_anydrug_n_notanydrug(patient_dict, problem_dict, drug_dict, encounter_dict, anydrug_list, notanydrug_list,
                           provider_list, study_start, study_end):
    elderly_drug = {}
    for key in patient_dict:
        row = patient_dict[key]
        default = None
        if has_code(drug_dict.get(key, default), anydrug_list):
            elderly_drug[key] = row
    print("Total number of elderly: " + str(len(patient_dict)))
    print("Number of elderly on " + str(anydrug_list) + ": " + str(len(elderly_drug)))
    denominator_dict = {}
    numerator_dict = {}
    for key in elderly_drug:
        row = elderly_drug[key]
        default = None
        encounter_list = encounter_dict.get(key, default)
        drug_list = drug_dict.get(key, default)
        if has_current_target_medication(drug_list, anydrug_list, study_end) and (had_provider_encounter(
                encounter_list, provider_list, study_start, study_end) or had_rx_provider_encounter(
                drug_list,
                provider_list,
                study_start, study_end)):
            denominator_dict[key] = row
            print("DEBUG den:", str(row))
            if not has_current_target_medication(drug_list, notanydrug_list, study_end):
                print("DEBUG num:", str(row))
                numerator_dict[key] = row
    print("Number of elderly on " + str(anydrug_list) + " seen by study provider in last 4 months: "
          + str(len(denominator_dict)))
    print("Number of elderly on " + str(anydrug_list) + " and not on " +
          str(notanydrug_list) + " seen by study provider in last 4 months: " + str(
        len(numerator_dict)))
    print_stats(problem_dict, drug_dict, encounter_dict, numerator_dict)


def sum_dict_values(the_dict):
    item_cnt = 0
    for the_key in the_dict:
        item_cnt += len(the_dict[the_key])
    return item_cnt


if __name__ == '__main__':
    try:
        # configure database connection
        db_user = read_config("db_user")
        db_passwd = read_config("db_passwd")
        db_name = read_config("db_name")
        db_port = int(read_config("db_port"))

        study_providers = get_study_provider_list("providers.csv")

        print("provider_list " + str(study_providers))

        end = datetime.date.fromordinal(datetime.date.today().toordinal() - 1)  # yesterday
        start = end + relativedelta(months=-4)  # four months ago

        # connect to database
        con = Mdb.connect(host='127.0.0.1', port=db_port, user=db_user, passwd=db_passwd, db=db_name)

        cur = con.cursor()

        err_cnt = 0

        def error_message(method_name, expected, actual, error_cnt):
            print("ERROR in " + str(method_name) + "!!!")
            print("Expected " + str(expected) + " but got " + str(actual))
            return error_cnt + 1

        # get provider numbers
        providers = get_providers(cur)
        provider_nos = get_provider_nums(providers, study_providers)
        print("provider_nums: " + str(provider_nos))

        # test get_demographics
        all_patients_dict = get_demographics(cur)
        demo_query = "select count(demographic_no) from demographic;"
        number = get_query_results(cur, demo_query)[0][0]
        if len(all_patients_dict) != int(number):
            err_cnt = error_message("get_demographics", number, len(all_patients_dict), err_cnt)

        # test active_patients
        active_patients_dict = active_patients(all_patients_dict)
        ac_demo_query = "select count(demographic_no) from demographic where patient_status='AC';"
        number = get_query_results(cur, ac_demo_query)[0][0]
        if len(active_patients_dict) != int(number):
            err_cnt = error_message("active_patients", number, len(active_patients_dict), err_cnt)

        # set up tests of is_valid_birthdate, calculate_age, elderly
        cnt_ac_patients_over150 = 0
        cnt_impossible_birthdates = 0
        cnt_invalid_dates = 0
        for d_key in all_patients_dict:
            d_row = all_patients_dict[d_key]
            if not is_impossible_birthdate(d_row[0], d_row[1], d_row[2]):
                cnt_impossible_birthdates += 1
            if not is_valid_date(str(d_row[0]) + '-' + str(d_row[1]) + '-' + str(d_row[2])):
                cnt_invalid_dates += 1
            if calculate_age(d_row[0], d_row[1], d_row[2], start) > 150:
                if is_active(all_patients_dict, d_key):
                    cnt_ac_patients_over150 += 1

        # test is_valid_birthdate
        if cnt_impossible_birthdates > 0:
            print("WARN: number of impossible birthdate records: " + str(cnt_impossible_birthdates))
        if cnt_invalid_dates > 0:
            print("WARN: number of invalid birthdate records: " + str(cnt_invalid_dates))
        invalid_birthdate_query = """
          select count(*) from demographic
          where year_of_birth is NULL or month_of_birth is NULL or date_of_birth is NULL or
          month_of_birth < 1 or month_of_birth > 12 or date_of_birth<1 or date_of_birth>31;
          """
        number = get_query_results(cur, invalid_birthdate_query)[0][0]
        if cnt_impossible_birthdates != int(number):
            err_cnt = error_message("is_valid_birthdate", number, cnt_impossible_birthdates, err_cnt)

        # test calculate_age
        too_old_query = """
          SELECT COUNT(d.demographic_no) AS Count FROM demographic AS d
          WHERE d.patient_status='AC' AND d.year_of_birth is not NULL and d.month_of_birth is not NULL
          AND d.date_of_birth is not NULL AND
          CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) <= DATE_SUB(NOW(), INTERVAL 150 YEAR);
          """
        number = get_query_results(cur, too_old_query)[0][0]
        if cnt_ac_patients_over150 != int(number):
            err_cnt = error_message("calculate_age", number, cnt_ac_patients_over150, err_cnt)

        # test elderly (number of elderly on start date which was 4 months ago)
        elderly_patients_dict = elderly(all_patients_dict, start)
        cnt_elderly = len(elderly(all_patients_dict, start))
        cnt_elderly_query = """
               SELECT COUNT(d.demographic_no) AS Count FROM demographic AS d
               WHERE d.patient_status = 'AC' AND d.year_of_birth is not NULL
               AND d.month_of_birth is not NULL AND d.date_of_birth is not NULL
               AND d.month_of_birth >= 1 AND d.month_of_birth <= 12
               AND d.date_of_birth >= 1 AND d.date_of_birth <= 31
               AND CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) <=
               DATE_SUB( DATE_SUB(DATE_SUB(NOW(), INTERVAL 1 DAY), INTERVAL 4 MONTH), INTERVAL 65 YEAR)
               AND CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) >
               DATE_SUB( DATE_SUB(DATE_SUB(NOW(), INTERVAL 1 DAY), INTERVAL 4 MONTH), INTERVAL 150 YEAR);
               """
        number = get_query_results(cur, cnt_elderly_query)[0][0]
        if cnt_elderly != int(number):
            err_cnt = error_message("elderly", number, cnt_elderly, err_cnt)

        # test get_drugs
        all_drugs_dict = get_drugs(cur)
        # query counts number of patients with medication list
        patient_drug_cnt_query = """
            select count(*) from (select distinct demographic_no from drugs where archived=0) x;
            """
        number = get_query_results(cur, patient_drug_cnt_query)[0][0]
        if len(all_drugs_dict) != int(number):
            err_cnt = error_message("get_drugs", number, len(all_drugs_dict), err_cnt)
        drug_cnt_query = "select count(*) from drugs where archived!=1;"
        number = get_query_results(cur, drug_cnt_query)[0][0]
        if sum_dict_values(all_drugs_dict) != number:
            err_cnt = error_message("sum_dict_values", number, sum_dict_values(all_drugs_dict), err_cnt)

        # test relevant_drugs (prescribed to patient with status 'AC')
        considered_drugs_dict = relevant_drugs(all_patients_dict, all_drugs_dict)
        ac_patient_drug_cnt = """
            select count(*) from (select distinct dr.demographic_no from drugs dr join demographic de
            on dr.demographic_no = de.demographic_no where de.patient_status='AC' and dr.archived=0) x;
            """
        number = get_query_results(cur, ac_patient_drug_cnt)[0][0]
        if len(considered_drugs_dict) != number:
            err_cnt = error_message("relevant_drugs", number, len(considered_drugs_dict), err_cnt)

        # set up test of is_long_term, is_prn, is_coded
        cnt_all = 0
        cnt_lt = 0
        cnt_prn = 0
        cnt_coded = 0
        for d_key in considered_drugs_dict:
            d_arr = considered_drugs_dict[d_key]
            for d_elem in d_arr:
                cnt_all += 1
                if is_long_term(d_elem):
                    cnt_lt += 1
                if is_prn(d_elem):
                    cnt_prn += 1
                if is_coded(d_elem):
                    cnt_coded += 1

        # another test of relevant_drugs
        test_query = """
            select count(*) from drugs dr join demographic de on dr.demographic_no=de.demographic_no
            where dr.archived!=1 and de.patient_status='AC';
            """
        number = get_query_results(cur, test_query)[0][0]
        if cnt_all != number:
            err_cnt = error_message("relevant_drugs", number, cnt_all, err_cnt)

        # test is_long_term
        test_query = """
            select count(*) from drugs dr join demographic de on dr.demographic_no=de.demographic_no
            where dr.archived!=1 and de.patient_status='AC' and dr.long_term=True;
            """
        number = get_query_results(cur, test_query)[0][0]
        if cnt_lt != number:
            err_cnt = error_message("is_long_term", number, cnt_lt, err_cnt)

        # test is_prn
        test_query = """
            select count(*) from drugs dr join demographic de on dr.demographic_no=de.demographic_no
            where dr.archived!=1 and de.patient_status='AC' and dr.prn=True;
            """
        number = get_query_results(cur, test_query)[0][0]
        if cnt_prn != number:
            err_cnt = error_message("is_long_term", number, cnt_prn, err_cnt)

        # test is_coded
        test_query = """
           select count(*) from drugs dr join demographic de on dr.demographic_no=de.demographic_no
           where dr.archived!=1 and de.patient_status='AC' and
           (ATC!='' and ATC is not NULL and ATC not like '%null') and
           (regional_identifier!='' and regional_identifier is not NULL and regional_identifier not like '%null');
            """
        number = get_query_results(cur, test_query)[0][0]
        if cnt_coded != number:
            err_cnt = error_message("is_coded", number, cnt_coded, err_cnt)

        # test get_dxresearch
        dx_dict = get_dxresearch(cur)
        # query counts number of patients with problem list
        test_query = """
            select count(*) from
            (select distinct demographic_no from dxresearch where status!='D' and coding_system='icd9') x;
            """
        number = get_query_results(cur, test_query)[0][0]
        if len(dx_dict) != int(number):
            err_cnt = error_message("get_dxresearch", number, len(dx_dict), err_cnt)
        test_query = "select count(*) from dxresearch where status!='D' and coding_system='icd9';"
        number = get_query_results(cur, test_query)[0][0]
        if sum_dict_values(dx_dict) != number:
            err_cnt = error_message("sum_dict_values", number, sum_dict_values(dx_dict), err_cnt)

        # test get_encounters
        all_encounters_dict = get_encounters(cur)
        test_query = """
            select count(*) from (select distinct cmn.demographic_no from casemgmt_note cmn
            where cmn.note_id = (select max(cmn2.note_id) from casemgmt_note cmn2 where cmn2.uuid = cmn.uuid)
            order by cmn.observation_date) x;
            """
        number = get_query_results(cur, test_query)[0][0]
        if len(all_encounters_dict) != number:
            err_cnt = error_message("get_encounters", number, len(all_encounters_dict), err_cnt)
        test_query = """
            select count(*) from (select cmn.demographic_no from casemgmt_note cmn
            where cmn.note_id = (select max(cmn2.note_id) from casemgmt_note cmn2 where cmn2.uuid = cmn.uuid)
            order by cmn.observation_date) x;
            """
        number = get_query_results(cur, test_query)[0][0]
        if sum_dict_values(all_encounters_dict) != number:
            err_cnt = error_message("get_encounters or sum_dict_values", number, len(all_encounters_dict), err_cnt)

        print("ERRORS: " + str(err_cnt))

    except Mdb.Error as e:
        print("Error %d: %s" % (e.args[0], e.args[1]))
        sys.exit(1)

    finally:
        if con:
            con.close()
