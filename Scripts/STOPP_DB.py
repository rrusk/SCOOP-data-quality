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
# from datetime import date
# import collections

# if import MySQLdb fails (for Ubuntu 14.04.1) run 'sudo apt-get install python-mysqldb'
import MySQLdb as Mdb

# if import dateutil.relativedelta fails run 'sudo apt-get install python-dateutil'
from dateutil.relativedelta import relativedelta

con = None
f = None


# create dictionary on second item in tuple
def create_dict_2nd(tlist):
    tdict = {}
    for trow in tlist:
        tdict[trow[1]] = trow[2:]
    return tdict


# creates list of providers with values [provider_no, first_name, last_name]
def get_providers(cursor):
    query = """SELECT p.provider_no, p.first_name, p.last_name from provider p order by p.last_name"""
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
        providers = get_providers(cur)
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
        stc_query = """
        select * from scheduletemplatecode order by code;
        """
        stc = get_query_results(cur, stc_query)
        print"\nscheduletemplatecode:"
        print('c description\tduration')
        for item in stc:
            print(str(item[0])+' '+str(item[1])+'\t'+str(item[2]))

        print("ERRORS: " + str(err_cnt))

        # from scheduleDate get name of scheduletemplate
        st_name_query = """
        select sdate, provider_no, hour from scheduledate where status='A' and hour!=''
        order by sdate, provider_no;
        """
        st_name = get_query_results(cur, st_name_query)
        print("length of scheduleDate: " + str(len(st_name)))
        print(str(st_name[0]))

        # get scheduletemplate
        st_query = """
        select * from scheduletemplate;
        """
        st = get_query_results(cur, st_query)
        stdict = create_dict_2nd(st)
        for item in stdict:
            print(str(item)+" ->\t"+str(stdict[item][1]))

        print
        print(str(st_name[0][0]), str(st_name[0][1]), str(stdict[st_name[0][2]][1]))

        # check for missing scheduletemplates
        cnt_missing_template = 0
        default = None
        for item in st_name:
            tresult = stdict.get(item[2], default)
            if not tresult:
                cnt_missing_template += 1
        print "\t", str(cnt_missing_template), " missing templates"

    except Mdb.Error as e:
        print("Error %d: %s" % (e.args[0], e.args[1]))
        sys.exit(1)

    finally:
        if con:
            con.close()
