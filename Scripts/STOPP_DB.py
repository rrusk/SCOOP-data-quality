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
        print("]: (will assume unknown codes have " + str(slotduration) + " min durations)")
        print(str(timecode_str))
    return result


# get beginning and end of schedule from timecode
def get_timecode_start_stop(timecode):
    minutes_per_day = 24. * 60
    slotduration = minutes_per_day / len(timecode)
    total_min = -slotduration
    result = None
    for char in timecode:
        if char == '_':
            total_min += slotduration
        else:
            total_min += slotduration
            start_time = str(int(total_min) / 60) + ':' + str(int(total_min) % 60)
            result = "Start time: " + str(start_time)
            break
    total_min = minutes_per_day + slotduration
    for char in reversed(timecode):
        if char == '_':
            total_min -= slotduration
        else:
            total_min -= slotduration
            stop_time = str(int(total_min) / 60) + ':' + str(int(total_min) % 60)
            result += "\nStop time: " + str(stop_time)
            break
    return result


# get beginning and end of schedule from timecode
def show_timecode_start_stop(timecode):
    minutes_per_day = 24. * 60
    slotduration = minutes_per_day / len(timecode)
    total_min = -slotduration
    for char in timecode:
        total_min += slotduration
        print(char + " " + str(int(total_min) / 60) + ':' + str(int(total_min) % 60))


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
    #  Note, Oscar's code in src/main/webapp/appointment/appointmentsearch.jsp and
    #  src/main/java/org/oscarehr/appointment/web/NextAppointmentSearchHelper.java
    #  uses a database query similar to the following but with "status!='N' and status!='C'"
    query = """
        select provider_no, appointment_date, start_time, end_time, appointment_no from appointment
        where status!='C' order by appointment_date, start_time;
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
    # print("check: " + str(ref_datetime))
    available_default = None
    the_date = ref_datetime.date()
    next_app_list = app_dict.get((provider_no, the_date), available_default)
    if next_app_list is None:
        print("NO APPOINTMENTS FOR provider_no=" + str(provider_no) + " on " + str(the_date))
        # for key in app_dict:
        #     print("Format is " + str(app_dict[key]))
        #     break
        return True  # true because provider_no has templatecode set for that schedule date but no appointments yet
    start_time = ref_datetime
    end_time = start_time + relativedelta(minutes=+(duration - 1))
    ref_date = datetime.combine(ref_datetime, datetime.min.time())  # 0:00AM on date checked
    booked = False

    # print("ref_date: " + str(ref_date))
    # print("start_time: " + str(start_time))
    # print("end_time: " + str(end_time))
    # print("len(next_app_list): " + str(len(next_app_list)))
    for app in next_app_list:
        seconds_start = app[0].total_seconds()
        seconds_end = app[1].total_seconds()
        app_start = ref_date + relativedelta(seconds=+seconds_start)
        app_end = ref_date + relativedelta(seconds=+seconds_end)
        # print("checking app_start: " + str(app_start)),
        # print(", checking app_end: " + str(app_end))
        # print("seconds_start: " + str(seconds_start) + " for " + str(app[0]))
        # print("seconds_end: " + str(seconds_end) + " for " + str(app[1]))
        #
        # TODO inefficient; since appointment is ordered by start_time this can be optimized further
        if end_time < app_start or start_time > app_end:
            continue
        booked = True
        break

    if booked:
        return False
    # print("Open for " + str(start_time) + " " + str(end_time))
    return True


def find_next_available_appointments(sd_dict, st_dict, stc_dict, app_dict, ref_datetime, provider_no, duration=15,
                                     num_appointments=3):
    next_app_list = []
    sd_default = None
    sd = sd_dict.get((ref_datetime.date(), provider_no), sd_default)
    if sd is None:
        # print("WARNING: no schedule for provider_no=" + str(provider_no) + " on " + str(ref_datetime))
        return None
    st_name = sd[0]  # hour field of scheduledate corresponds to name of scheduletemplate
    if st_name.startswith('P:'):
        template = st_dict.get((st_name, "Public"), default)
    else:
        template = st_dict.get((st_name, provider_no), default)
    if not template:
        sys.stdout.write("ERROR: Missing template [" + str(st_name) + "] for " + str(
            provider_no) + " in find_next_available_appointments\n")
        return None
    timecodestr = template[1]

    # print("provider_no=" + str(provider_no) + " ref_datetime " + str(ref_datetime))
    # show_timecode_start_stop(timecodestr)

    if not is_valid_timecode_string(timecodestr, stc_dict):
        return None

    # print(get_timecode_start_stop(timecodestr))

    # check which slots are available between the start and end times
    ref_date = datetime.combine(ref_datetime, datetime.min.time())
    # print("timecodestr [" + str(st_name) + "]:" + str(timecodestr))

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


# builds a string from provider_no entries in provider_no_list, for example  "('101', '102', '999998')"
def build_provider_no_str(provider_no_list):
    provider_nums_str = ""
    idx = 0
    length = len(provider_no_list)
    for provider_no in provider_no_list:
        idx += 1
        provider_nums_str += "'" + str(provider_no) + "'"
        if idx < length:
            provider_nums_str += ','
    return provider_nums_str


# patterned after ThirdApptTimeReport in Oscar's
# src/main/java/oscar/oscarReport/reportByTemplate/ThirdApptTimeReporter.java
def third_appt_time_reporter(cursor, provider_no_list, date_from, sched_symbols_list, appt_length):
    num_days = -1
    if date_from is None or provider_no_list is None or sched_symbols_list is None:
        print("ERROR: date_from and provider_no_list must be set and at least one schedule symbol must be set")
        return False
    provider_nums_str = build_provider_no_str(provider_no_list)
    date_str = str(date_from.date())  # expect datetime object from which the date is extracted
    schedule_sql = "select scheduledate.provider_no, scheduletemplate.timecode, scheduledate.sdate" \
                   " from scheduletemplate, scheduledate" \
                   " where scheduletemplate.name=scheduledate.hour and scheduledate.sdate >= '" + date_str + \
                   "' and  scheduledate.provider_no in (" + provider_nums_str + ") and scheduledate.status = 'A' and " \
                   " (scheduletemplate.provider_no=scheduledate.provider_no or scheduletemplate.provider_no='Public')" \
                   " order by scheduledate.sdate"
    # print('sql: ' + schedule_sql)
    res = get_query_results(cursor, schedule_sql)
    # print('schedule results length: ' + str(len(res)))
    # print('schedule results:')
    # for r in res:
    #     print(str(r))

    day_mins = 24. * 60.
    i = 0
    num_appts = 0
    third = 3
    sched_date = None
    while i < len(res) and num_appts < third:
        provider_no = res[i][0]
        print("provider_no=" + str(provider_no))
        timecodes = res[i][1]
        print("templatecode=" + str(timecodes))
        sched_date = res[i][2]
        print("scheduledate=" + str(sched_date))
        duration = day_mins / len(timecodes)
        appt_sql = "select start_time, end_time from appointment where appointment_date = '" + date_str + \
                   "' and provider_no = '" + str(provider_no) + "' and status not like '%C%' " + \
                   " order by start_time asc"
        print('appt_sql: ' + appt_sql)
        appts = get_query_results(cursor, appt_sql)
        codepos = 0
        latest_appt_hour = 0
        latest_appt_min = 0
        unbooked = 0
        itotalmin = 0
        while itotalmin < day_mins:
            code = timecodes[codepos]
            codepos += 1
            print("iTotalMin: " + str(itotalmin) + " codepos: " + str(codepos))
            ihours = int(itotalmin / 60)
            imins = int(itotalmin % 60)
            appt_index = 0
            while appt_index < len(appts):
                print("appt_index: " + str(appt_index))
                # appt = appts[appt_index]
                appt_time = appts[appt_index][0].total_seconds()
                # print('appt_time=' + str(appt_time))
                appt_hour_s = int(appt_time) / 3600
                appt_min_s = int(appt_time) % 60

                print('hour=' + str(appt_hour_s) + ' min=' + str(appt_min_s))
                print('ihour=' + str(ihours) + ' imins=' + str(imins))
                if ihours == appt_hour_s and imins == appt_min_s:
                    appt_time = appts[appt_index][1].total_seconds()
                    appt_hour_e = int(appt_time) / 3600
                    appt_min_e = int(appt_time) % 60
                    print('appt_hour_e=' + str(appt_hour_e) + ' min=' + str(appt_min_e))
                    if appt_hour_e > latest_appt_hour or \
                            (appt_hour_e == latest_appt_hour and appt_min_e > latest_appt_min):
                        latest_appt_hour = appt_hour_e
                        latest_appt_min = appt_min_e
                else:
                    appt_index -= 1
                    break
                appt_index += 1

            code_match = False
            sched_idx = 0
            while sched_idx < len(sched_symbols_list):
                if code == sched_symbols_list[sched_idx]:
                    code_match = True
                    if ihours > latest_appt_hour or (ihours == latest_appt_hour and imins > latest_appt_min):
                        unbooked += duration

                    if unbooked >= appt_length:
                        unbooked = 0
                        num_appts += 1
                        if num_appts == third:
                            break
                sched_idx += 1

            if num_appts == third:
                break

            if not code_match:
                unbooked = 0

            itotalmin += duration

    if sched_date is not None:
        num_days = (sched_date - date_from.date()).days

    print("num_days: " + str(num_days) + " date_from: " + str(date_from) + " sched_date: " + str(sched_date)),
    print(" num_appts: " + str(num_appts))


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
            the_datetime = datetime(2015, 6, 9, 0, 0, 0)
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

            # third_appt_time_reporter(cur, provider_nos, the_datetime, ['1'], 15)

    except Mdb.Error as e:
        print("Error %d: %s" % (e.args[0], e.args[1]))
        sys.exit(1)

    finally:
        if con:
            con.close()
