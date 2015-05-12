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
    refdate = datetime.date(2015, 2, 27)
    end = datetime.date.fromordinal(refdate.toordinal() - 1)  # day prior to refdate
    start_4mo_ago = end + relativedelta(months=-4)  # four months earlier
    start_12mo_ago = end + relativedelta(months=-12)  # 12 months earlier
    start_24mo_ago = end + relativedelta(months=-24)  # 24 months earlier
    print "REFERENCE DATE: ", str(refdate)
    print "  END DATE:", str(end)
    print " 4 Mo Prev:", str(start_4mo_ago)
    print "12 Mo Prev:", str(start_12mo_ago)
    print "24 Mo Prev:", str(start_24mo_ago)
    # connect to database
    con = Mdb.connect(host='127.0.0.1', port=db_port, user=db_user, passwd=db_passwd, db=db_name)

    cur = con.cursor()

    print("Providers:")
    providers = DQ.get_providers(cur)
    provider_nos = DQ.get_provider_nums(providers, study_providers)
    print("provider_nos: " + str(provider_nos))

    print("Demographics:")
    all_patients_dict = DQ.get_demographics(cur)
    # patients with 'AC' status
    active_patients_dict = DQ.active_patients(all_patients_dict)

    cnt_too_old_patients = 0
    cnt_ac_patients = 0
    cnt_impossible_birthdate = 0
    for d_key in all_patients_dict:
        d_row = all_patients_dict[d_key]
        if DQ.is_impossible_birthdate(d_row[0], d_row[1], d_row[2]):
            cnt_impossible_birthdate += 1
        if DQ.calculate_age(d_row[0], d_row[1], d_row[2], start_4mo_ago) > 150:
            cnt_too_old_patients += 1
        if DQ.is_active(all_patients_dict, d_key):
            cnt_ac_patients += 1
    print " impossible age: ", cnt_impossible_birthdate
    print "        too old: ", cnt_too_old_patients
    print "    'ac' status: ", cnt_ac_patients

    # patient 65+ as of 4 month before reference date (elderly defaults to only active patients)
    elderly_patients_dict = DQ.elderly(all_patients_dict, start_4mo_ago)

    default = None
    all_drugs_dict = DQ.get_drugs(cur)
    cnt_missing_demo_nos = 0
    for demographic_key in all_drugs_dict:
        demographic = all_patients_dict.get(demographic_key, default)
        if not demographic:
            cnt_missing_demo_nos += 1
            # print "\tDRUG RECORDED WITH DEMO_NO ", str(demographic_key), " MISSING FROM DEMOGRAPHICS: "
    print "\t", str(cnt_missing_demo_nos), " drug records with demographic number not in demographic table"

    # drug dictionary for patients with 'AC' status
    considered_drugs_dict = DQ.relevant_drugs(all_patients_dict, all_drugs_dict)

    default = None
    dx_dict = DQ.get_dxresearch(cur)
    cnt_missing_demo_nos = 0
    for demographic_key in dx_dict:
        demographic = all_patients_dict.get(demographic_key, default)
        if not demographic:
            cnt_missing_demo_nos += 1
            # print "\tCONDITION RECORDED WITH DEMO_NO ", str(demographic_key), " MISSING FROM DEMOGRAPHICS: "
    print "\t", str(cnt_missing_demo_nos), " condition records with demographic number not in demographic table"

    default = None
    all_encounters_dict = DQ.get_encounters(cur)
    cnt_missing_demo_nos = 0
    for demographic_key in all_encounters_dict:
        demographic = all_patients_dict.get(demographic_key, default)
        if not demographic:
            cnt_missing_demo_nos += 1
            # print "\tENCOUNTER RECORDED WITH DEMO_NO ", str(demographic_key), " MISSING FROM DEMOGRAPHICS: "
    print "\t", str(cnt_missing_demo_nos), " encounter records with demographic number not in demographic table"

    print("\n\nTesting DQ-DEM-01:")
    cnt_ac = 0
    cnt_ac_with_encounter = 0
    the_default = None
    for a_key in active_patients_dict:
        cnt_ac += 1
        edict = all_encounters_dict.get(a_key, the_default)
        mlist = considered_drugs_dict.get(a_key, the_default)
        if (edict and DQ.had_encounter(edict, start_24mo_ago, end)) or \
                (mlist and DQ.had_rx_encounter(mlist, start_24mo_ago, end)):
            cnt_ac_with_encounter += 1
    print("Number of active patients: " + str(cnt_ac))
    print("Number of active patients with encounter in past 24 months: " + str(cnt_ac_with_encounter))
    if cnt_ac > 0:
        percentage = 100.0 * cnt_ac_with_encounter / cnt_ac
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
    print("Number with neither M nor F gender: " + str(num))
    if den > 0:
        percentage = 100.0 * num / den
        print("Percentage of calculated active patients neither F nor M: " + str(percentage))

    print("\n\nTesting DQ-DEM-03:")
    num = 0
    for a_key in calc_active_patients_dict:
        drec = calc_active_patients_dict[a_key]
        if DQ.is_impossible_birthdate(drec[0], drec[1], drec[2]):
            num += 1
        else:
            if DQ.calculate_age(drec[0], drec[1], drec[2]) < 0 or DQ.calculate_age(drec[0], drec[1], drec[2]) > 150:
                num += 1
    print("Number of calculated active patients: " + str(den))
    print("Number with invalid date of birth: " + str(num))
    if den > 0:
        percentage = 100.0 * num / den
        print("Percentage of calculated active patients with invalid date of birth: " + str(percentage))

    print("\n\nTesting DQ-DEM-04:")
    num = 0
    for a_key in calc_active_patients_dict:
        drec = calc_active_patients_dict[a_key]
        if drec[0] is None or drec[1] is None or drec[2] is None or drec[0] == '0001':
            num += 1
    print("Number of calculated active patients: " + str(den))
    print("Number with undocumented date of birth: " + str(num))
    if den > 0:
        percentage = 100.0 * num / den
        print("Percentage of calculated active patients with undocumented date of birth: " + str(percentage))

    print("\n\nTesting DQ-MED-01:")
    current_med = 0
    current_coded_med = 0
    for demographics_key in all_drugs_dict:
        if DQ.is_active(all_patients_dict, demographics_key):
            patients_drug_list = all_drugs_dict[demographics_key]
            # patient's drugs are assumed grouped by DIN, with most recent prescription first
            previous_din = None
            for drug in patients_drug_list:
                if DQ.is_current_medication(drug, end, duration_multiplier=1.2, prn_multiplier=2.0, use_longterm=True,
                                            use_prn=True):
                    current_din = drug[1]
                    if (current_din is None or current_din == '') or (current_din != previous_din):
                        current_med += 1
                        if DQ.is_coded(drug):
                            current_coded_med += 1
                            previous_din = current_din
                        else:
                            previous_din = None
    print("Number of current medications to patients with 'AC' status: " + str(current_med))
    print("Number that are coded: " + str(current_coded_med))
    if current_med > 0:
        percentage = 100.0 * current_coded_med / current_med
        print("Percentage of current medications that are coded: " + str(percentage))

    print("\n\nTesting DQ-MED-01b:")
    current_med = 0
    current_coded_med = 0
    for demographics_key in all_drugs_dict:
        if DQ.is_active(all_patients_dict, demographics_key):
            patients_drug_list = all_drugs_dict[demographics_key]
            # patient's drugs are assumed grouped by DIN, with most recent prescription first
            for drug in patients_drug_list:
                if DQ.is_current_medication(drug, end, duration_multiplier=1.0, prn_multiplier=1.0, use_longterm=False,
                                            use_prn=False):
                    current_med += 1
                    if DQ.is_coded(drug):
                        current_coded_med += 1
    print(
        "Number of current medications to patients with 'AC' status (no long-term or multipliers): " + str(current_med))
    print("Number that are coded: " + str(current_coded_med))
    if current_coded_med > 0:
        percentage = 100.0 * current_coded_med / current_med
        print("Percentage of current medications that are coded: " + str(percentage))

    print("\n\nTesting DQ-MED-01c:")
    current_med = 0
    current_coded_med = 0
    for demographics_key in all_drugs_dict:
        if DQ.is_active(all_patients_dict, demographics_key):
            patients_drug_list = all_drugs_dict[demographics_key]
            # patient's drugs are assumed grouped by DIN, with most recent prescription first
            previous_din = None
            for drug in patients_drug_list:
                if DQ.is_current_medication(drug, end, duration_multiplier=1.2, prn_multiplier=1.0, use_longterm=False,
                                            use_prn=False):
                    current_din = drug[1]
                    if (current_din is None or current_din == '') or (current_din != previous_din):
                        current_med += 1
                        if DQ.is_coded(drug):
                            current_coded_med += 1
                            previous_din = current_din
                        else:
                            previous_din = None
    print("Number of current medications for patients with 'AC' status using first current med found"),
    print(" and duration multiplier only: " + str(current_med))
    print("Number that are coded: " + str(current_coded_med))
    if current_med > 0:
        percentage = 100.0 * current_coded_med / current_med
        print("Percentage of current medications that are coded: " + str(percentage))

    print("\n\nTesting DQ-MED-01d:")
    current_med = 0
    current_coded_med = 0
    for demographics_key in all_drugs_dict:
        if DQ.is_active(all_patients_dict, demographics_key):
            patients_drug_list = all_drugs_dict[demographics_key]
            # patient's drugs are assumed grouped by DIN, with most recent prescription first
            previous_din = None
            for drug in patients_drug_list:
                if DQ.is_current_medication(drug, end, duration_multiplier=1.2, prn_multiplier=1.0, use_longterm=True,
                                            use_prn=False):
                    current_din = drug[1]
                    if (current_din is None or current_din == '') or (current_din != previous_din):
                        current_med += 1
                        if DQ.is_coded(drug):
                            current_coded_med += 1
                            previous_din = current_din
                        else:
                            previous_din = None
    print("Number of current medications for patients with 'AC' status using first current med found"),
    print(" and duration multiplier only: " + str(current_med))
    print("Number that are coded: " + str(current_coded_med))
    if current_med > 0:
        percentage = 100.0 * current_coded_med / current_med
        print("Percentage of current medications that are coded: " + str(percentage))

    print("\n\nTesting DQ-MED-02:")
    cnt_prescriptions = 0
    cnt_encounters = 0
    # TODO: Should test active status of patient at reference date.
    # Probably safe to ignore since patients that are not 'AC' are unlikely
    # to have either prescriptions or encounters within the last 12 months.
    default = None
    for demographic_key in all_drugs_dict:
        med_list = all_drugs_dict.get(demographic_key, default)
        for med in med_list:
            try:
                if start_12mo_ago <= med[2] <= end:
                    cnt_prescriptions += 1
            except TypeError:
                print "DEBUG: demographic_no =", demographic_key, 'med = ', str(med)
    for demographic_key in all_encounters_dict:
        enc_list = all_encounters_dict.get(demographic_key, default)
        for enc in enc_list:
            if start_12mo_ago <= enc[1].date() <= end:
                cnt_encounters += 1
    print("Number of prescriptions recorded in past 12 months: " + str(cnt_prescriptions))
    print("Number of encounters recorded in past 12 months: " + str(cnt_encounters))
    if cnt_encounters > 0:
        ratio = 1.0 * cnt_prescriptions / cnt_encounters
        print("Ratio of prescriptions to encounters: " + str(ratio))

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
    # if len(current_din) != 8:
    # print("DEBUG: current_din: " + str(current_din))
    # if True:  # previous_din != current_din:
    # if DQ.is_current_medication(drug, end, duration_multiplier=1.2, prn_multiplier=2.0):
    # current_med += 1
    # if current_din != "null":
    # coded_med += 1
    #
    # # mysql> select count(*) from
    # (select dr.demographic_no, regional_identifier, BN, GN, customName, ATC, dr.end_date from drugs dr join
    # demographic de on dr.demographic_no = de.demographic_no where de.patient_status='AC' and dr.archived=0 and
    # (dr.long_term=1 or dr.end_date>NOW()) and LENGTH(dr.regional_identifier)=8) x;
    # # +----------+
    # # | count(*) |
    # # +----------+
    # # |     7776 |
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
    cnt_active_patients = 0
    cnt_active_no_med = 0
    default = None
    for demographic_key in calc_active_patients_dict:
        cnt_active_patients += 1
        med_list = all_drugs_dict.get(demographic_key, default)
        if med_list:
            has_current_med = False
            for med in med_list:
                if DQ.is_long_term(med) or DQ.is_current_medication(med, end, duration_multiplier=1.2,
                                                                    prn_multiplier=2.0):
                    has_current_med = True
                    break
            if not has_current_med:
                cnt_active_no_med += 1
        else:
            cnt_active_no_med += 1
    print("Number of calculated active patients: " + str(cnt_active_patients))
    print("Number of calculated active patients with no current medications documented: " + str(cnt_active_no_med))
    if cnt_active_patients > 0:
        percentage = 100.0 * cnt_active_no_med / cnt_active_patients
        print("Percentage of active patients with no current medications: " + str(percentage))

    print("\n\nTesting DQ-PL-01: What percentage of problems on the problem list, documented in the past 12 months,"),
    print(" has a diagnostic code?")
    cnt_problems = 0
    cnt_prob_codes = 0
    default = None
    for demographic_key in dx_dict:
        prob_list = dx_dict.get(demographic_key, default)
        for prob in prob_list:
            try:
                if start_12mo_ago <= prob[1] <= end:
                    cnt_problems += 1
                    if prob[0]:
                        cnt_prob_codes += 1
            except TypeError:
                print "DEBUG: demographic_no =", demographic_key, 'prob = ', str(prob)
    print("Number of problems in last 12 months: " + str(cnt_problems))
    print("Number of coded problems in last 12 months: " + str(cnt_prob_codes))
    if cnt_prob_codes > 0:
        percentage = 100.0 * cnt_problems / cnt_prob_codes
        print("Percentage of problems that were coded in past 12 months: " + str(percentage))

    print("\n\nTesting DQ-PL-02: What percentage of patients, 12 AND OVER, calculated as active, has at least one"),
    print(" documented problem on the problem list (documented in the past 12 months)?")
    cnt_with_problem = 0
    cnt_active_12plus = 0
    default = None
    for demographic_key in calc_active_patients_dict:
        record = calc_active_patients_dict[demographic_key]
        if DQ.calculate_age(record[0], record[1], record[2], end) >= 12:
            cnt_active_12plus += 1
            prob_list = dx_dict.get(demographic_key, default)
            if prob_list:
                for prob in prob_list:
                    try:
                        if start_12mo_ago <= prob[1] <= end:
                            cnt_with_problem += 1
                            break
                    except TypeError:
                        print "DEBUG: demographic_no =", demographic_key, 'prob = ', str(prob)
    print("Number of calculated active patients 12 and over: " + str(cnt_active_12plus))
    print("Number of with at least one problem documented in in last 12 months: " + str(cnt_with_problem))
    if cnt_active_12plus > 0:
        percentage = 100.0 * cnt_with_problem / cnt_active_12plus
        print("Percentage of problems that were coded in past 12 months: " + str(percentage))

    print("\n\nTesting DQ-PL-03: What percentage of patients, calculated as active, 12 and over, has Diabetes on the"),
    print(" problem list?")
    cnt_with_diabetes = 0
    cnt_active_12plus = 0
    default = None
    for demographic_key in calc_active_patients_dict:
        record = calc_active_patients_dict[demographic_key]
        if DQ.calculate_age(record[0], record[1], record[2], end) >= 12:
            cnt_active_12plus += 1
            prob_list = dx_dict.get(demographic_key, default)
            if DQ.has_code(prob_list, ['250']):
                cnt_with_diabetes += 1
    print("Number of calculated active patients 12 and over: " + str(cnt_active_12plus))
    print("Number of with diabetes on problem list: " + str(cnt_with_diabetes))
    if cnt_active_12plus > 0:
        percentage = 100.0 * cnt_with_problem / cnt_active_12plus
        print("Percentage of calc active patients over 12 with diabetes: " + str(percentage))

    print("\n\nTesting DQ-PL-04: Of patients with a current Tiotropium medication, what percentage has COPD"),
    print(" on the problem list?")
    cnt_has_med = 0
    cnt_has_prob = 0
    default = None
    for demographic_key in active_patients_dict:
        med_list = all_drugs_dict.get(demographic_key, default)
        if med_list:
            if DQ.has_current_target_medication(med_list, ['R03BB04'], end, duration_multiplier=1.2,
                                                prn_multiplier=2.0):
                cnt_has_med += 1
                prob_list = dx_dict.get(demographic_key, default)
                if DQ.has_code(prob_list, ['4912', '492', '496']):
                    cnt_has_prob += 1
    print("Number of patients with current Tiotropium med: " + str(cnt_has_med))
    print("Number with both current Tiotropium and COPD: " + str(cnt_has_prob))
    if cnt_has_med > 0:
        percentage = 100.0 * cnt_has_prob / cnt_has_med
        print("Percentage with COPD on Tiotropium: " + str(percentage))

    print("\n\nTesting DQ-PL-05: Of patients with a current Levothyroxine medication, what percentage has"),
    print(" Hypothyroidism on the problem list?")
    cnt_has_med = 0
    cnt_has_prob = 0
    default = None
    for demographic_key in active_patients_dict:
        med_list = all_drugs_dict.get(demographic_key, default)
        if med_list:
            if DQ.has_current_target_medication(med_list, ['H03AA'], end, duration_multiplier=1.2, prn_multiplier=2.0):
                cnt_has_med += 1
                prob_list = dx_dict.get(demographic_key, default)
                if DQ.has_code(prob_list, ['243', '244', '245']):
                    cnt_has_prob += 1
    print("Number of patients with current Levothyroxine med: " + str(cnt_has_med))
    print("Number with both current Levothyroxine and hypothyroidism: " + str(cnt_has_prob))
    if cnt_has_med > 0:
        percentage = 100.0 * cnt_has_prob / cnt_has_med
        print("Percentage with hypothyroidism on levothyroxine: " + str(percentage))

    print("\n\nTesting DQ-PL-06: Of patients with a current anti-gout medication, what percentage has Gout"),
    print(" on the problem list?")
    cnt_has_med = 0
    cnt_has_prob = 0
    default = None
    for demographic_key in active_patients_dict:
        med_list = all_drugs_dict.get(demographic_key, default)
        if med_list:
            if DQ.has_current_target_medication(med_list, ['M04A'], end, duration_multiplier=1.2, prn_multiplier=2.0):
                cnt_has_med += 1
                prob_list = dx_dict.get(demographic_key, default)
                if DQ.has_code(prob_list, ['274']):
                    cnt_has_prob += 1
    print("Number of patients with current allopurinol med: " + str(cnt_has_med))
    print("Number with both current allopurinol and gout: " + str(cnt_has_prob))
    if cnt_has_med > 0:
        percentage = 100.0 * cnt_has_prob / cnt_has_med
        print("Percentage with gout on allopurinol: " + str(percentage))

    print("\n\nTesting STOPP Rule A02:")
    any_drugs = ["C03C"]
    notanydx_list = ["401", "402", "404", "405", "428", "39891", "7895", "5712", "5715", "5716", "581", "V1303", "5853",
                     "5854", "5855", "5856", "5859", "585", "586", "5184"]
    DQ.d_anydrug_n_notanyproblem(elderly_patients_dict, dx_dict, all_drugs_dict, all_encounters_dict, any_drugs,
                                 notanydx_list, provider_nos, start_4mo_ago, end)

    print("\n\nTesting STOPP Rule A03:")
    dx_codes = ["401"]
    any_drugs = ["C03C"]
    notany_drugs = ["C03AA", "C07A", "C08", "C09"]
    DQ.d_anyproblem_n_anydrug_notanydrug(elderly_patients_dict, dx_dict, all_drugs_dict, all_encounters_dict, dx_codes,
                                         any_drugs,
                                         notany_drugs, provider_nos, start_4mo_ago, end)

    print("\n\nTesting STOPP Rule test B07:")
    any_drugs = ["N03AE01", "N05BA02", "N05BA05", "N05BA01", "N05CD01", "N05CD03", "N05CD08", "N05CD02"]
    DQ.d_n_anydrug(elderly_patients_dict, all_drugs_dict, all_encounters_dict, any_drugs, provider_nos, start_4mo_ago,
                   end)

    print("\n\nTesting STOPP Rule B08:")
    any_drugs = ["N05A", "N06C"]
    notanydx_list = ["295", "297", "298"]
    DQ.d_anydrug_n_notanyproblem(elderly_patients_dict, dx_dict, all_drugs_dict, all_encounters_dict, any_drugs,
                                 notanydx_list, provider_nos, start_4mo_ago, end)

    print("\n\nTesting STOPP Rule I02:")
    any_drugs = ["N02A"]
    notany_drugs = ["A06A"]
    DQ.d_anydrug_n_notanydrug(elderly_patients_dict, dx_dict, all_drugs_dict, all_encounters_dict, any_drugs,
                              notany_drugs,
                              provider_nos,
                              start_4mo_ago, end)

except Mdb.Error as e:
    print("Error %d: %s" % (e.args[0], e.args[1]))
    sys.exit(1)

finally:
    if con:
        con.close()
