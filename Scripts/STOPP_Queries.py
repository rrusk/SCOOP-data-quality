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

    end = datetime.date.fromordinal(datetime.date.today().toordinal() - 1)  # yesterday
    start = end + relativedelta(months=-4)  # four months ago

    # connect to database
    con = Mdb.connect(host='127.0.0.1', port=db_port, user=db_user, passwd=db_passwd, db=db_name)

    cur = con.cursor()

    print("Providers:")
    providers = DQ.get_providers(cur)
    provider_nos = DQ.get_provider_nums(providers, study_providers)
    print("provider_nos: " + str(provider_nos))

    print("Demographics:")
    all_patients_dict = DQ.get_demographics(cur)
    print("  Total number of patient records: " + str(len(all_patients_dict)))
    print("    Should be consistent with")
    print("      select count(demographic_no) from demographic;")

    active_patients_dict = DQ.active_patients(all_patients_dict)
    print("  Number of active patients: " + str(len(active_patients_dict)))
    print("    Should be consistent with")
    print("      select count(demographic_no) from demographic where patient_status='AC';")

    cnt_all_patients = 0
    cnt_ac_patients = 0
    cnt_invalid_patients = 0
    for d_key in all_patients_dict:
        d_row = all_patients_dict[d_key]
        if not DQ.is_valid_birthdate(d_row[0], d_row[1], d_row[2]):
            cnt_invalid_patients += 1
        if DQ.calculate_age(d_row[0], d_row[1], d_row[2], start) > 150:
            cnt_all_patients += 1
            if DQ.is_active(all_patients_dict, d_key):
                cnt_ac_patients += 1

    print("  Number of invalid birthdate records: " + str(cnt_invalid_patients))
    print("  Number of patient > 150 years: " + str(cnt_all_patients))
    print("    Should be consistent with ")
    print("      SELECT COUNT(d.demographic_no) AS Count FROM demographic AS d ")
    print("      WHERE CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth )"),
    print("<= DATE_SUB(NOW(), INTERVAL 150 YEAR);")

    print("  Number of active patient > 150 years: " + str(cnt_ac_patients))
    print("    Should be consistent with ")
    print("      SELECT COUNT(d.demographic_no) AS Count FROM demographic AS d ")
    print("      WHERE d.patient_status = 'AC' ")
    print("      AND CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth )"),
    print("<= DATE_SUB(NOW(), INTERVAL 150 YEAR);")

    elderly_patients_dict = DQ.elderly(all_patients_dict, start)

    print(
        "  Number of patients >= 65 on " + str(start) + ": " + str(len(DQ.elderly(all_patients_dict, start))))
    elder_cnt = DQ.get_elderly_count_4months_ago(cur)
    print("  Number of patient >= 65 four months ago via direct SQL is " + str(elder_cnt))

    #
    print("\nDrugs:")
    all_drugs_dict = DQ.get_drugs(cur)
    print("Number of patients with medication list: " + str(len(all_drugs_dict)))
    print("Total number of non-archived drugs in drugs table: " + str(DQ.sum_dict_values(all_drugs_dict)))
    print("  Should match output from")
    print("    select count(*) from drugs where archived!=1;")

    considered_drugs_dict = DQ.relevant_drugs(all_patients_dict, all_drugs_dict)
    print("Number of active patients with medication list: " + str(len(considered_drugs_dict)))

    #
    print("Total number of non-archived drugs for active patients: "),
    cnt_all = 0
    cnt_lt = 0
    cnt_prn = 0
    cnt_coded = 0
    for d_key in considered_drugs_dict:
        d_arr = considered_drugs_dict[d_key]
        for d_elem in d_arr:
            cnt_all += 1
            if DQ.is_long_term(d_elem):
                cnt_lt += 1
            if DQ.is_prn(d_elem):
                cnt_prn += 1
            if DQ.is_coded(d_elem):
                cnt_coded += 1
    print(str(cnt_all))
    print("Should match output from")
    print("  select count(*) from drugs dr join demographic de on dr.demographic_no=de.demographic_no")
    print("  where dr.archived!=1 and de.patient_status='AC';")
    print("Number of Long-Term meds in Drugs table for active patients: "),
    print(str(cnt_lt))
    print("Should match output from")
    print("  select count(*) from drugs dr join demographic de on dr.demographic_no=de.demographic_no")
    print("  where dr.archived!=1 and de.patient_status='AC' and dr.long_term=True;")
    print("Number of PRN meds in Drugs table for active patients: "),
    print(str(cnt_prn))
    print("Should match output from")
    print("  select count(*) from drugs dr join demographic de on dr.demographic_no=de.demographic_no")
    print("  where dr.archived!=1 and de.patient_status='AC' and dr.prn=True;")
    print("Number of coded meds in Drugs table for active patients: "),
    print(str(cnt_coded))
    print("Should match output from")
    print("  select count(*) from drugs dr join demographic de on dr.demographic_no=de.demographic_no")
    print("  where dr.archived!=1 and de.patient_status='AC' and")
    print("  (ATC!='' and ATC is not NULL) and (regional_identifier!='' and regional_identifier is not NULL);")

    #
    print("Problems:")
    dx_dict = DQ.get_dxresearch(cur)
    print("Size of dxresearch: " + str(len(dx_dict)))

    #
    print("Encounters:")
    all_encounters_dict = DQ.get_encounters(cur)
    print("Size of encounter list: " + str(len(all_encounters_dict)))

    print("\n\nTesting DQ-DEM-01:")
    start24monthsago = end + relativedelta(months=-24)
    cnt_active = 0
    cnt_active_with_encounter = 0
    the_default = None
    for a_key in active_patients_dict:
        cnt_active += 1
        edict = all_encounters_dict.get(a_key, the_default)
        med_dict = considered_drugs_dict.get(a_key, the_default)
        if (edict and DQ.had_encounter(edict, start24monthsago, end)) or\
                (med_dict and DQ.had_rx_encounter(med_dict, start24monthsago, end)):
            cnt_active_with_encounter += 1
    print("Number of active patients: " + str(cnt_active))
    print("Number of active patients with encounter in past 24 months: " + str(cnt_active_with_encounter))
    percentage = 100.0 * cnt_active_with_encounter / cnt_active
    print("Percentage of active patients with encounter in past 24 months: " + str(percentage))

    print("\n\nTesting DQ-MED-01:")
    current_med = 0
    coded_med = 0
    for demographics_key in all_drugs_dict:
        if DQ.is_active(all_patients_dict, demographics_key):
            demo_drug_list = all_drugs_dict[demographics_key]
            current_din = ''
            for drug in demo_drug_list:
                if drug[1] == '' or drug[1] is None or drug[1] != current_din:
                    current_din = drug[1]  # logic here depends on drugs list being sorted by DIN, etc.
                    if DQ.is_current_medication(drug, end):
                        current_med += 1
                        if DQ.is_coded(drug):
                            coded_med += 1
    print("Number of current medications: " + str(current_med))
    print("Number of current medications that are coded: " + str(coded_med))
    percentage = 100.0 * coded_med / current_med
    print("Percentage of current medications that are coded: " + str(percentage))

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
