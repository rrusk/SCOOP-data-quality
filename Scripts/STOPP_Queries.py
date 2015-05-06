import sys

__author__ = 'rrusk'

import STOPP_DQ as DQ
import datetime

# if import MySQLdb fails (for Ubuntu 14.04.1) run 'sudo apt-get install python-mysqldb'
import MySQLdb as Mdb

# if import dateutil.relativedelta fails run 'sudo apt-get install python-dateutil'
from dateutil.relativedelta import relativedelta

con = None

try:
    # configure database connection
    db_user = DQ.read_config("db_user")
    db_passwd = DQ.read_config("db_passwd")
    db_name = DQ.read_config("db_name")
    db_port = int(DQ.read_config("db_port"))

    study_providers = DQ.get_study_provider_list("providers.csv")

    print("provider_list " + str(study_providers))

    # refdate = datetime.date.today()
    refdate = datetime.date(2015, 2, 19)
    end = datetime.date.fromordinal(refdate.toordinal() - 1)  # day prior to refdate
    start = end + relativedelta(months=-4)  # four months earlier

    # connect to database
    con = Mdb.connect(host='127.0.0.1', port=db_port, user=db_user, passwd=db_passwd, db=db_name)

    cur = con.cursor()

    print("Providers:")
    providers = DQ.get_providers(cur)
    provider_nos = DQ.get_provider_nums(providers, study_providers)
    print("provider_nos: " + str(provider_nos))

    print("Demographics:")
    all_patients_dict = DQ.get_demographics(cur)
    active_patients_dict = DQ.active_patients(all_patients_dict)

    cnt_all_patients = 0
    cnt_ac_patients = 0
    cnt_invalid_patients = 0
    for d_key in all_patients_dict:
        d_row = all_patients_dict[d_key]
        if not DQ.is_impossible_birthdate(d_row[0], d_row[1], d_row[2]):
            cnt_invalid_patients += 1
        if DQ.calculate_age(d_row[0], d_row[1], d_row[2], start) > 150:
            cnt_all_patients += 1
            if DQ.is_active(all_patients_dict, d_key):
                cnt_ac_patients += 1

    elderly_patients_dict = DQ.elderly(all_patients_dict, start)

    all_drugs_dict = DQ.get_drugs(cur)
    considered_drugs_dict = DQ.relevant_drugs(all_patients_dict, all_drugs_dict)
    dx_dict = DQ.get_dxresearch(cur)
    all_encounters_dict = DQ.get_encounters(cur)

    print("\n\nTesting DQ-DEM-01:")
    start24monthsago = end + relativedelta(months=-24)
    cnt_active = 0
    cnt_active_with_encounter = 0
    the_default = None
    for a_key in active_patients_dict:
        cnt_active += 1
        edict = all_encounters_dict.get(a_key, the_default)
        mlist = considered_drugs_dict.get(a_key, the_default)
        if (edict and DQ.had_encounter(edict, start24monthsago, end)) or \
                (mlist and DQ.had_rx_encounter(mlist, start24monthsago, end)):
            cnt_active_with_encounter += 1
    print("Number of active patients: " + str(cnt_active))
    print("Number of active patients with encounter in past 24 months: " + str(cnt_active_with_encounter))
    percentage = 100.0 * cnt_active_with_encounter / cnt_active
    print("Percentage of active patients with encounter in past 24 months: " + str(percentage))

    print("\n\nTesting DQ-DEM-02:")
    calc_active_patients_dict = DQ.calculated_active_patients(end, all_patients_dict, all_encounters_dict,
                                                              all_drugs_dict)
    den = len(calc_active_patients_dict)
    num = 0
    for a_key in calc_active_patients_dict:
        gender = calc_active_patients_dict[a_key][3]
        if not (gender.upper() == 'M' or gender.upper() == 'F'):
            num += 1
    print("Number of calculated active patients: " + str(den))
    print("Number with unknown gender: " + str(num))
    percentage = 100.0 * num / den
    print("Percentage of calculated active patients neither F or M: " + str(percentage))

    print("\n\nTesting DQ-DEM-03:")
    num = 0
    for a_key in calc_active_patients_dict:
        drec = calc_active_patients_dict[a_key]
        if not DQ.is_impossible_birthdate(drec[0], drec[1], drec[2]):
            num += 1
        else:
            if DQ.calculate_age(drec[0], drec[1], drec[2]) < 0 or DQ.calculate_age(drec[0], drec[1], drec[2]) > 150:
                num += 1
    print("Number of calculated active patients: " + str(den))
    print("Number with invalid date of birth: " + str(num))
    percentage = 100.0 * num / den
    print("Percentage of calculated active patients with invalid date of birth: " + str(percentage))

    print("\n\nTesting DQ-DEM-04:")
    num = 0
    for a_key in calc_active_patients_dict:
        drec = calc_active_patients_dict[a_key]
        if DQ.calculate_age(drec[0], drec[1], drec[2]) > 150:
            num += 1
    print("Number of calculated active patients: " + str(den))
    print("Number with undocumented date of birth: " + str(num))
    percentage = 100.0 * num / den
    print("Percentage of calculated active patients with undocumented date of birth: " + str(percentage))

    print("\n\nTesting DQ-MED-01:")
    current_med = 0
    coded_med = 0
    cnt_demographics = 0
    cnt_ac_demographics = 0
    for demographics_key in all_drugs_dict:
        cnt_demographics += 1
        if DQ.is_active(all_patients_dict, demographics_key):
            cnt_ac_demographics += 1
            patients_drug_list = all_drugs_dict[demographics_key]
            # logic here depends on drugs list being sorted by DIN, etc.
            current_din = 0
            previous_din = 0
            for drug in patients_drug_list:
                if drug[1] == '' or drug[1] is None:
                    current_din = 'null'
                else:
                    current_din = drug[1]
                    if len(current_din) != 8:
                        print("DEBUG: current_din: " + str(current_din))
                # if previous_din != current_din or (current_din == 'null'):
                previous_din = current_din
                if DQ.is_current_medication(drug, end, duration_multiplier=1.2, prn_multiplier=2.0):
                    current_med += 1
                    if current_din != "null":
                        coded_med += 1

    # print("Number of patients with medications: " + str(cnt_demographics))
    # print("Number of active patients with medications: " + str(cnt_ac_demographics))
    print("Number of current medications: " + str(current_med))
    print("Number of current medications that are coded: " + str(coded_med))
    percentage = 100.0 * coded_med / current_med
    print("Percentage of current medications that are coded: " + str(percentage))

    print("\n\nTesting DQ-MED-02:")

    # print("\n\nTesting DQ-MED-01 v2:")
    # current_med = 0
    # coded_med = 0
    # cnt_demographics = 0
    # cnt_ac_demographics = 0
    # for demographics_key in all_drugs_dict:
    # cnt_demographics += 1
    # if DQ.is_active(all_patients_dict, demographics_key):
    # cnt_ac_demographics += 1
    # patients_drug_list = all_drugs_dict[demographics_key]
    # # logic here depends on drugs list being sorted by DIN, etc.
    # for drug in patients_drug_list:
    # if drug[1] == '' or drug[1] is None:
    # current_din = 'null'
    # else:
    # current_din = drug[1]
    #                 if len(current_din) != 8:
    #                     print("DEBUG: current_din: " + str(current_din))
    #             if True:  # previous_din != current_din:
    #                 if DQ.is_current_medication(drug, end, duration_multiplier=1.2, prn_multiplier=2.0):
    #                     current_med += 1
    #                     if current_din != "null":
    #                         coded_med += 1
    #
    #                     # mysql> select count(*) from
    #  (select dr.demographic_no, regional_identifier, BN, GN, customName, ATC, dr.end_date from drugs dr join
    #  demographic de on dr.demographic_no = de.demographic_no where de.patient_status='AC' and dr.archived=0 and
    #  (dr.long_term=1 or dr.end_date>NOW()) and LENGTH(dr.regional_identifier)=8) x;
    #                     # +----------+
    #                     # | count(*) |
    #                     # +----------+
    #                     # |     7776 |
    #                     # +----------+
    #                     # 1 row in set (0.06 sec)
    #                     #
    #                     # mysql> select count(*) from
    #  (select dr.demographic_no, regional_identifier, BN, GN, customName, ATC, dr.end_date from drugs dr join
    #  demographic de on dr.demographic_no = de.demographic_no where de.patient_status='AC' and dr.archived=0 and
    #  (dr.long_term=1 or dr.end_date>NOW())) x;
    #                     # +----------+
    #                     # | count(*) |
    #                     # +----------+
    #                     # |     8131 |
    #                     # +----------+
    #                     # 1 row in set (0.07 sec)
    #                     #
    #
    # # print("Number of patients with medications: " + str(cnt_demographics))
    # # print("Number of active patients with medications: " + str(cnt_ac_demographics))
    # print("Number of current medications: " + str(current_med))
    # print("Number of current medications that are coded: " + str(coded_med))
    # percentage = 100.0 * coded_med / current_med
    # print("Percentage of current medications that are coded: " + str(percentage))

    print("\n\nTesting DQ-MED-03: What percentage of patients, calculated as active, has no current medications?")
    # num = 0
    # for a_key in calc_active_patients_dict:
    #     drec = calc_active_patients_dict[a_key]
    #     if not DQ.is_valid_birthdate(drec[0], drec[1], drec[2]) or DQ.calculate_age(drec[0], drec[1],
    #                                                                                 drec[2]) < 0 or DQ.calculate_age(
    #             drec[0], drec[1], drec[2]) > 150:
    #         num += 1
    # print("Number of calculated active patients: " + str(den))
    # print("Number with invalid date of birth: " + str(num))
    # percentage = 100.0 * num / den
    # print("Percentage of calculated active patients with invalid date of birth: " + str(percentage))

    print("\n\nTesting STOPP Rule A02:")
    any_drugs = ["C03C"]
    notanydx_list = ["401", "402", "404", "405", "428", "39891", "7895", "5712", "5715", "5716", "581", "V1303", "5853",
                     "5854", "5855", "5856", "5859", "585", "586", "5184"]
    DQ.d_anydrug_n_notanyproblem(elderly_patients_dict, dx_dict, all_drugs_dict, all_encounters_dict, any_drugs,
                                 notanydx_list, provider_nos, start, end)

    print("\n\nTesting STOPP Rule A03:")
    dx_codes = ["401"]
    any_drugs = ["C03C"]
    notany_drugs = ["C03AA", "C07A", "C08", "C09"]
    DQ.d_anyproblem_n_anydrug_notanydrug(elderly_patients_dict, dx_dict, all_drugs_dict, all_encounters_dict, dx_codes,
                                         any_drugs,
                                         notany_drugs, provider_nos, start, end)

    print("\n\nTesting STOPP Rule test B07:")
    any_drugs = ["N03AE01", "N05BA02", "N05BA05", "N05BA01", "N05CD01", "N05CD03", "N05CD08", "N05CD02"]
    DQ.d_n_anydrug(elderly_patients_dict, all_drugs_dict, all_encounters_dict, any_drugs, provider_nos, start, end)

    print("\n\nTesting STOPP Rule B08:")
    any_drugs = ["N05A", "N06C"]
    notanydx_list = ["295", "297", "298"]
    DQ.d_anydrug_n_notanyproblem(elderly_patients_dict, dx_dict, all_drugs_dict, all_encounters_dict, any_drugs,
                                 notanydx_list, provider_nos, start, end)

    print("\n\nTesting STOPP Rule I02:")
    any_drugs = ["N02A"]
    notany_drugs = ["A06A"]
    DQ.d_anydrug_n_notanydrug(elderly_patients_dict, dx_dict, all_drugs_dict, all_encounters_dict, any_drugs,
                              notany_drugs,
                              provider_nos,
                              start, end)

except Mdb.Error as e:
    print("Error %d: %s" % (e.args[0], e.args[1]))
    sys.exit(1)

finally:
    if con:
        con.close()
