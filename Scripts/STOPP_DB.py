#!/usr/bin/python
# -*- coding: utf-8 -*-
# Script assumes that database connection information is stored in
# ~/mysql/db_config.  Change if needed.  Variables are initialized
# this way for compatibility with prior Bash script.
#
# Determination of 3rd next appointment similar that used in Oscar EMR code in
# src/main/webapp/appointment/appointmentsearch.jsp and
# src/main/java/org/oscarehr/appointment/web/NextAppointmentSearchHelper.java
#
import sys

__author__ = 'rrusk'

import os
import csv
import datetime
# from datetime import date
# import collections

# if import MySQLdb fails (for Ubuntu 14.04.1) run 'sudo apt-get install python-mysqldb'
import MySQLdb as Mdb

# if import dateutil.relativedelta fails run 'sudo apt-get install python-dateutil'
from dateutil.relativedelta import relativedelta

con = None
f = None
max_days_to_search = 180


# create dictionary on first item in tuple
def create_dict(tlist):
    tdict = {}
    for trow in tlist:
        tdict[trow[0]] = trow[1:]
    return tdict


# create dict of active providers with key provider_no and value [first_name, last_name].
def get_active_providers_dict(cursor):
    query = """SELECT p.provider_no, p.first_name, p.last_name from provider p where status='1' order by p.last_name"""
    cursor.execute(query)
    result = cursor.fetchall()
    return create_dict(result)


# get dict of scheduletemplatecodes with code as key and [duration, description] as value
def get_schedule_template_code_dict(cursor):
    query = """select code, duration, description from scheduletemplatecode order by code"""
    cursor.execute(query)
    result = cursor.fetchall()
    return create_dict(result)


# get dictionary of schedule templates with name as key and [provider_no, summary, timecode] as value
def get_schedule_template_dict(cursor):
    query = """select name, provider_no, summary, timecode from scheduletemplate"""
    cursor.execute(query)
    result = cursor.fetchall()
    s_dict = {}
    for s_item in result:
        if s_item[0] == '':
            s_dict['empty'] = s_item[1:]
        elif s_item[0] is None:
            s_dict['null'] = s_item[1:]
        else:
            s_dict[s_item[0]] = s_item[1:]
    return s_dict


# test whether the timecode strings in scheduletemplate are valid
def validate_timecode_strings(schedule_template_dict, schedule_template_code_dict):
    result = True
    defaultv = None
    cnt_valid = 0
    cnt_invalid = 0
    cnt_missing_codes = 0
    for st_item in schedule_template_dict:
        timecode_str = schedule_template_dict[st_item][2]
        total_min = 0
        warning = False
        for char in timecode_str:
            if char == '_':
                total_min += 15
            else:
                value = schedule_template_code_dict.get(char, defaultv)
                if value and value[0] != '':
                    total_min += int(value[0])
                else:
                    total_min += 15  # assume unrecognized or absent codes have duration 15 minutes
                    warning = True
        if total_min != 24 * 60:
            print("INVALID TIMECODE STRING FOR " + str(st_item) + ": Totals " + str(total_min) + " rather then 1440")
            print(str(timecode_str))
            cnt_invalid += 1
            result = False
        elif warning:
            print("WARNING: INVALID CODES IN TIMECODE STRING FOR " + str(st_item)),
            print(": (Assuming missing codes have 15 min durations)")
            print(str(timecode_str))
            cnt_missing_codes += 1
        else:
            print("VALID TIMECODE STRING FOR " + str(st_item) + ":")
            print(str(timecode_str))
            cnt_valid += 1
    print("Valid: " + str(cnt_valid) + " Invalid: " + str(cnt_invalid)),
    print(" Valid with missing codes: " + str(cnt_missing_codes))
    return result


# get dictionary of schedule template name values indexed by (provider_no, date)
def get_schedule_dict(cursor):
    # for reasons unknown some rows are duplicated in the scheduledate table (except for primary key) so the
    # dictionary can be shorter than complete list of rows
    query = """
        select distinct sdate, provider_no, hour, available from scheduledate
        where status='A' and hour!='' and hour is not NULL
        order by sdate, provider_no;
        """
    cursor.execute(query)
    result = cursor.fetchall()
    s_dict = {}
    for s_item in result:
        s_dict[(s_item[0], s_item[1])] = s_item[2:]
    return s_dict


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
    for s in study_provider_list:
        for p in provider_list:
            if provider_list[p][0].strip() == s[0].strip() and provider_list[p][1].strip() == s[1].strip():
                pnums_list.append(p.strip())
    return pnums_list


# used to tune script to specific database configuration settings
def read_config(filename):
    home = os.path.expanduser("~")

    with open(os.path.join(home, "mysql", "db_config", filename), "rb") as fh:
        return fh.readline().rstrip()


# general query used for test purposes
def get_query_results(cursor, query):
    cursor.execute(query)
    return cursor.fetchall()


if __name__ == '__main__':
    try:
        # configure database connection
        db_user = read_config("db_user")
        db_passwd = read_config("db_passwd")
        db_name = read_config("db_name")
        db_port = int(read_config("db_port"))

        study_providers = get_study_provider_list("providers.csv")

        print("provider_list: " + str(study_providers))

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
        providers = get_active_providers_dict(cur)

        provider_nos = get_provider_nums(providers, study_providers)
        print("provider_nums: " + str(provider_nos))

        # get STOPP DSS users
        stopp_user_query = """
        select distinct p.provider_no, p.first_name, p.last_name, g.dateStart from provider p
        inner join dsGuidelineProviderMap as gpm on p.provider_no=gpm.provider_no
        inner join dsGuidelines g on g.uuid=gpm.guideline_uuid
        and g.author='stopp' and g.status='A';
        """
        stopp_users = get_query_results(cur, stopp_user_query)
        if len(stopp_users) == 0:
            print("STOPP DSS users: None")
        else:
            print("STOPP DSS Users:")
            print("pno\tfname\tlname\t\tsince")
            print("---\t-----\t-----\t\t-----")
            for su in stopp_users:
                print(str(su[0]) + '\t' + str(su[1]) + '\t' + str(su[2]) + '\t\t' + str(su[3]))

        # get scheduletemplatecode
        stc = get_schedule_template_code_dict(cur)
        print"\nscheduletemplatecode:"
        print('c duration\tdescription')
        for item in stc:
            print(str(item) + ' ' + str(stc[item][0]) + '\t' + str(stc[item][1]))

        print("ERRORS: " + str(err_cnt))

        # get schedule template dictionary
        stdict = get_schedule_template_dict(cur)
        # for item in stdict:
        #     print(str(item) + " ->\t" + str(stdict[item][2]))

        validate_timecode_strings(stdict, stc)

        # from scheduleDate get name of scheduletemplate
        st_name_dict = get_schedule_dict(cur)
        print("length of schedule dict: " + str(len(st_name_dict)))

        # check for missing scheduletemplates
        cnt_missing_template = 0
        default = None
        for item in st_name_dict:
            tresult = stdict.get(st_name_dict[item][0], default)
            if not tresult:
                cnt_missing_template += 1
                print("WARNING: Missing template: " + str(st_name_dict[item][0]))
        print "\t", str(cnt_missing_template), " missing templates"

    except Mdb.Error as e:
        print("Error %d: %s" % (e.args[0], e.args[1]))
        sys.exit(1)

    finally:
        if con:
            con.close()
