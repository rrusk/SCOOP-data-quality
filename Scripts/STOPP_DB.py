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
# import datetime
from datetime import datetime, date
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
        if trow[0] in tdict:
            #  warn about values that are actually different
            if tdict[trow[0]] != trow[1:]:
                print("WARNING: key (" + str(trow[0])),
                print("\thas multiple values ")
                print('\t' + str(tdict[trow[0]]))
                print('\t' + str(trow[1:]))
            continue  # only take first row with this key
        else:
            tdict[trow[0]] = trow[1:]
    return tdict


# get total sum of elements in dictionary containing values that are lists
def sum_dict_values(the_dict):
    item_cnt = 0
    for the_key in the_dict:
        item_cnt += len(the_dict[the_key])
    return item_cnt


# create dict of active providers with key provider_no and value [first_name, last_name].
def get_active_providers_dict(cursor):
    query = """SELECT p.provider_no, p.first_name, p.last_name from provider p where status='1' order by p.last_name"""
    cursor.execute(query)
    result = cursor.fetchall()
    return create_dict(result)


# get dict of scheduletemplatecodes with code as key and [duration, description] as value
def get_schedule_template_code_dict(cursor):
    query = """select code, duration, description, id from scheduletemplatecode order by code"""
    cursor.execute(query)
    result = cursor.fetchall()
    return create_dict(result)


# get dictionary of schedule templates with (name, provider_no) as key and [summary, timecode] as value
def get_schedule_template_dict(cursor):
    query = """select name, provider_no, summary, timecode from scheduletemplate"""
    cursor.execute(query)
    result = cursor.fetchall()
    st_dict = {}
    for st_item in result:
        if (st_item[0], st_item[1]) in st_dict:
            if st_dict[(st_item[0], st_item[1])][0] != st_item[2] or st_dict[(st_item[0], st_item[1])][1] != st_item[3]:
                #  warn about values that are actually different
                print("WARNING: key (" + str(st_item[0]) + ',' + str(st_item[1]) + ')'),
                print("\thas multiple values ")
                print('\t' + str(st_dict[(st_item[0], st_item[1])]))
                print('\t' + str(st_item[2:]))
            continue  # only take first row with this key
        else:
            st_dict[(st_item[0], st_item[1])] = st_item[2:]
    return st_dict


# test whether the timecode strings in scheduletemplate are valid
def validate_all_timecode_strings(schedule_template_dict, schedule_template_code_dict):
    result = True
    defaultv = None
    cnt_valid = 0
    cnt_invalid = 0
    cnt_missing_codes = 0
    minutes_per_day = 24. * 60
    for st_item in schedule_template_dict:
        total_min = 0
        timecode_str = schedule_template_dict[st_item][1]
        slotduration = None
        warning = False
        if timecode_str is not None or len(timecode_str) != 0:
            slotduration = minutes_per_day / len(timecode_str)
            for char in timecode_str:
                if char == '_':
                    total_min += slotduration
                else:
                    value = schedule_template_code_dict.get(char, defaultv)
                    if value and value[0] != '':
                        total_min += slotduration  # int(value[0])
                    else:
                        total_min += slotduration  # assume unrecognized or absent codes occupy one time slot
                        warning = True
        else:
            print("ERROR: timecode string is empty")
            result = False
        if total_min != minutes_per_day:
            sys.stdout.write("INVALID TIMECODE STRING [" + str(st_item)),
            print("]: Totals " + str(total_min) + " rather then " + str(minutes_per_day))
            print(str(timecode_str))
            cnt_invalid += 1
            result = False
        elif warning:
            sys.stdout.write("WARNING: UNKNOWN CODES IN TIMECODE STRING [" + str(st_item)),
            print("]: (will assume unknown codes have " + str(slotduration) + " min durations)")
            print(str(timecode_str))
            cnt_missing_codes += 1
        else:
            # print("VALID TIMECODE STRING FOR " + str(st_item) + ":")
            # print(str(timecode_str))
            cnt_valid += 1
    print("scheduletemplate entries:")
    print(" Valid: " + str(cnt_valid) + " Invalid: " + str(cnt_invalid)),
    print(" Valid with unknown codes assumed one timeslot in duration: " + str(cnt_missing_codes))
    return result


# test whether specific timecode string in scheduletemplate is valid
def is_valid_timecode_string(timecode_str, schedule_template_code_dict):
    result = True
    defaultv = None
    total_min = 0
    warning = False
    if timecode_str is None or len(timecode_str) == 0:
        return False
    minutes_per_day = 24. * 60
    slotduration = minutes_per_day / len(timecode_str)
    for char in timecode_str:
        if char == '_':
            total_min += slotduration
        else:
            value = schedule_template_code_dict.get(char, defaultv)
            if value and value[0] != '':
                total_min += slotduration  # int(value[0])
            else:
                total_min += slotduration  # assume unrecognized or absent codes occupy one time slot
                warning = True
    if total_min != minutes_per_day:
        sys.stdout.write("INVALID TIMECODE STRING [" + str(timecode_str)),
        print("]: Totals " + str(total_min) + " rather then " + str(minutes_per_day))
        print(str(timecode_str))
        result = False
    elif warning:
        sys.stdout.write("WARNING: UNKNOW CODES IN TIMECODE STRING [" + str(timecode_str)),
        print("]: (will assume unknown codes have " + str(slotduration) + "min durations)")
        print(str(timecode_str))
    return result


# get dictionary of schedule template name values indexed by (provider_no, date)
def get_scheduledate_dict(cursor):
    # for reasons unknown some rows are duplicated in the scheduledate table (except for primary key) so the
    # dictionary can be shorter than complete list of rows
    query = """
        select sdate, provider_no, hour, available, id from scheduledate
        where status='A' order by sdate, provider_no;
        """
    cursor.execute(query)
    result = cursor.fetchall()
    s_dict = {}
    for s_item in result:
        if (s_item[0], s_item[1]) in s_dict:
            if s_dict[(s_item[0], s_item[1])][0] != s_item[2] or s_dict[(s_item[0], s_item[1])][1] != s_item[3]:
                #  warn about values that are actually different asisde from their id
                print("WARNING: key (" + str(s_item[0]) + ',' + str(s_item[1]) + ')'),
                print("\thas multiple values ")
                print('\t' + str(s_dict[(s_item[0], s_item[1])]))
                print('\t' + str(s_item[2:]))
            continue  # only take first row with this key since Oscar EMR limits queries to 1 returned value
        else:
            s_dict[(s_item[0], s_item[1])] = s_item[2:]
    return s_dict


# get dictionary of appointments with key provide, day and values [start_time, end_time, appointment_no]
# that are not "no-show" or "cancelled"
def get_appointment_dict(cursor):
    query = """
        select provider_no, appointment_date, start_time, end_time, appointment_no from appointment
        where status!='N' and status!='C' order by appointment_date, start_time;
        """
    cursor.execute(query)
    result = cursor.fetchall()
    app_dict = {}
    for app_item in result:
        if (app_item[0], app_item[1]) in app_dict:
            app_dict[(app_item[0], app_item[1])].append(app_item[2:])
        else:
            app_dict[(app_item[0], app_item[1])] = [app_item[2:]]
    return app_dict


# check appointment dictionary for existing booking at specified datetime and duration
def check_availability(app_dict, provider_no, ref_datetime, duration):
    available_default = None
    the_date = ref_datetime.date()
    next_app_list = app_dict.get((provider_no, the_date), available_default)
    if next_app_list is None:
        print("NO APPOINTMENTS FOR provider_no=" + str(provider_no) + " on " + str(the_date))
        # for key in app_dict:
        #     print("Format is " + str(app_dict[key]))
        #     break
        return True
    start_time = ref_datetime
    end_time = start_time + relativedelta(minutes=+(duration - 1))
    ref_date = datetime.combine(ref_datetime, datetime.min.time())  # 0:00AM on date checked
    booked = False

    # print("ref_date: " + str(ref_date))
    # print("start_time: " + str(start_time))
    # print("end_time: " + str(end_time))
    for app in next_app_list:
        seconds_start = app[0].total_seconds()
        seconds_end = app[1].total_seconds()
        app_start = ref_date + relativedelta(seconds=+seconds_start)
        app_end = ref_date + relativedelta(seconds=+seconds_end)
        # print("checking app_start: " + str(app_start))
        # print("checking app_end: " + str(app_end))
        # print("seconds_start: " + str(seconds_start) + " for " + str(app[0]))
        # print("seconds_end: " + str(seconds_end) + " for " + str(app[1]))
        #
        # TODO inefficient; since appointment is ordered by start_time this can be optimized further
        if end_time < app_start or start_time > app_end:
            continue
        # print("found app_start: " + str(app_start) + " less than end_time: " + str(end_time))
        # print("found app_end: " + str(app_end) + " greater than start_time: " + str(start_time))
        booked = True
        break

    if booked:
        return False
    return True


def find_next_available_appointments(sd_dict, st_dict, stc_dict, app_dict, ref_datetime, provider_no, duration=15,
                                     num_appointments=3):
    next_app_list = []
    sd_default = None
    sd = sd_dict.get((ref_datetime.date(), provider_no), sd_default)
    if sd is None:
        print("WARNING: no schedule for provider_no=" + str(provider_no) + " on " + str(ref_datetime))
        return None
    st_name = sd[0]  # hour field of scheduledate corresponds to name of scheduletemplate
    if st_name.startswith('P:'):
        template = st_dict.get((st_name, "Public"), default)
    else:
        template = st_dict.get((st_name, provider_no), default)
    if not template:
        print("ERROR: Missing template " + str(scheduledate_dict[item][0]) + " in find_next_available_appointments")
        return None
    timecodestr = template[1]
    if not is_valid_timecode_string(timecodestr, stc_dict):
        return None

    # check which slots are available between the start and end times
    ref_date = datetime.combine(ref_datetime, datetime.min.time())
    print("timecodestr [" + str(st_name) + "]:" + str(timecodestr))

    slotduration = (24. * 60) / len(timecodestr)
    total_min = -slotduration

    for char in timecodestr:
        if char == '_':
            total_min += slotduration
        else:
            value = stc_dict.get(char, sd_default)
            if value and value[0] != '':
                total_min += slotduration  # int(value[0])
            else:
                total_min += slotduration  # assume unrecognized or absent codes have duration 15 minutes
            start_app = ref_date + relativedelta(minutes=+total_min)
            end_app = ref_date + relativedelta(minutes=+(total_min + duration - 1))
            if start_app < ref_datetime:
                print("skipping at " + str(start_app))
                continue
            if check_availability(app_dict, provider_no, start_app, duration):
                next_app_list.append((start_app, end_app))
                if len(next_app_list) >= num_appointments:
                    break
            else:
                pass
                # print("conflict at: " + str(start_app) + " " + str(end_app))
    return next_app_list


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

        # end = datetime.date.fromordinal(datetime.date.today().toordinal() - 1)  # yesterday
        end = date.fromordinal(date.today().toordinal() - 1)  # yesterday
        # start = end + relativedelta(months=-4)  # four months ago

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
        # print()
        # print("scheduletemplatecode:")
        # print('c duration\tdescription')
        # for item in stc:
        #     print(str(item) + ' ' + str(stc[item][0]) + '\t' + str(stc[item][1]))
        #
        # print("ERRORS: " + str(err_cnt))

        # get schedule template dictionary
        stdict = get_schedule_template_dict(cur)
        # for item in stdict:
        #     print(str(item) + " ->\t" + str(stdict[item][2]))

        validate_all_timecode_strings(stdict, stc)

        # from scheduleDate get name of scheduletemplate
        scheduledate_dict = get_scheduledate_dict(cur)
        print("length of schedule dict: " + str(len(scheduledate_dict)))

        # check for missing scheduletemplates
        cnt_missing_template = 0
        default = None
        missing_template_dict = {}
        for item in scheduledate_dict:
            templatename = scheduledate_dict[item][0]
            clinic_provider_no = item[1]
            if templatename.startswith('P:'):
                tresult = stdict.get((templatename, "Public"), default)
                if not tresult:
                    missing_template_dict[(templatename, "Public")] = "missing"
            else:
                tresult = stdict.get((templatename, clinic_provider_no), default)
                if not tresult:
                    missing_template_dict[(templatename, clinic_provider_no)] = "missing"
            if not tresult:
                cnt_missing_template += 1
                # print("WARNING: Missing template: " + str(scheduledate_dict[item][0]))
        print(str(cnt_missing_template) + " scheduledate rows with missing templates")
        if cnt_missing_template > 0:
            print("The following template name, provider number combinations are missing:")
            for tname in missing_template_dict:
                print('\t' + str(tname))

        # load appointment dictionary
        appointment_dict = get_appointment_dict(cur)
        print("length of appointment dict: " + str(len(appointment_dict)))
        print("items in appointment dict: " + str(sum_dict_values(appointment_dict)))

        the_datetime = datetime(2014, 4, 1, 0, 0, 0)
        print("the_datetime: " + str(the_datetime))
        availability_result = check_availability(appointment_dict, '110', the_datetime, 15)
        print("availability: " + str(availability_result))

        for provider_num in provider_nos:
            # provider_num = '101'
            the_datetime = datetime(2014, 4, 1, 0, 0, 0)
            num_apps = 0
            days = 0
            apps_list = []
            while days < max_days_to_search:
                app_list = find_next_available_appointments(scheduledate_dict, stdict, stc, appointment_dict,
                                                            the_datetime, provider_num)
                if app_list is not None and len(app_list) > 0:
                    apps_list += app_list
                    num_apps += len(app_list)
                    # print("apps_list:")
                    # for item in app_list:
                    #    print(str(item))
                if num_apps >= 3:
                    break
                days += 1
                the_datetime = the_datetime + relativedelta(days=+1)
            print("apps_list:")
            for item in apps_list:
                print(str(item))
            print("Days to 3rd next appointment = " + str(days) + " for " + str(provider_num))

    except Mdb.Error as e:
        print("Error %d: %s" % (e.args[0], e.args[1]))
        sys.exit(1)

    finally:
        if con:
            con.close()
