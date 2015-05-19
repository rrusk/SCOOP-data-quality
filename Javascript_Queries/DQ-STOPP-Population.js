/**
 * Created by rrusk on 15/07/14.
 */
// Title: Elderly Patients Seen by Study Practitioners in 4 month window
// Description: STOPP Rule Population v2
// Obtain estimate of how many STOPP patients might be seen by provider within 4 month window

function map(patient) {

    var ignore_providers_list = true;
    var providers = setStoppDQProviders();
    if (providers) {
        ignore_providers_list = false;
    }

    var v1_age = 65;

    var drugList = patient.medications();
    var encounterList = patient.encounters();

    var refdateStr = setStoppDQRefDateStr();   // hQuery library function call
    var refdate = new Date(refdateStr);      // refdateStr is 'yyyy,mm,dd' with mm from 1-12
    refdate.setHours(23, 59);                 // set to end of refdate then subtract one day
    var start = addDate(refdate, 0, -4, -1); // four month study window; generally most
    var end = addDate(refdate, 0, 0, -1);    // recent records are from previous day
    var currentRec = currentRecord(end);

    // Shifts date by year, month, and date specified
    function addDate(date, y, m, d) {
        var n = new Date(date);
        n.setFullYear(date.getFullYear() + (y || 0));
        n.setMonth(date.getMonth() + (m || 0));
        n.setDate(date.getDate() + (d || 0));
        return n;
    }

    // Test that record is current (as of day before study reference date at 0:00AM)
    function currentRecord(date) {
        var daybefore = new Date(date);
        daybefore.setHours(0, 0);
        return patient['json']['effective_time'] > daybefore / 1000;
    }

    // Checks if patient is older than ageLimit at start of window
    // The upper limit filters out patients with unknown age
    function targetPopulation(ageLimit) {
        return patient.age(start) >= ageLimit && patient.age(start) <= 150;
    }

    // Checks for encounter with any of the specified providers between start and end dates
    function hadEncounter(startDate, endDate) {
        for (var i = 0; i < encounterList.length; i++) {
            if (encounterList[i].startDate() >= startDate &&
                encounterList[i].startDate() <= endDate) {
                if (ignore_providers_list ||
                    (typeof encounterList[i].performer() !== 'undefined' &&
                    typeof encounterList[i].performer()['json'] !== 'undefined' &&
                    providers.indexOf(encounterList[i].performer()['json']['family_name']) > -1)) {
                    return true;
                }
            }
        }
        return false;
    }

    // Checks for encounter with any of the specified providers between start and end dates
    function hadRxEncounter(startDate, endDate) {
        for (var i = 0; i < drugList.length; i++) {
            if (typeof drugList[i].orderInformation() !== 'undefined' &&
                typeof drugList[i].orderInformation().length != 0) {
                for (var j = 0; j < drugList[i].orderInformation().length; j++) {
                    var drugPrescribed = drugList[i].orderInformation()[j].orderDateTime();
                    drugPrescribed.setHours(24, 1);  // kludge to get start date to match rx_date in EMR
                    if (drugPrescribed >= startDate && drugPrescribed <= endDate) {
                        if (ignore_providers_list ||
                            (typeof providers !== 'undefined' &&
                            providers.length != 0 &&
                            typeof drugList[i].orderInformation()[j]['json'] !== 'undefined' &&
                            typeof drugList[i].orderInformation()[j]['json']['performer'] !== 'undefined' &&
                            providers.indexOf(drugList[i].orderInformation()[j]['json']['performer']['family_name']) > -1)) {
                            return true;
                        }
                    }
                }
            }
        }
        return false;
    }

    refdateStr = refdateStr.replace(/,/g, '');
    emit('denominator_' + refdateStr, 0);
    emit('numerator_' + refdateStr, 0);
    if (currentRec && targetPopulation(v1_age)) {
        emit('denominator_' + refdateStr, 1);
        if (hadEncounter(start, end) || hadRxEncounter(start, end)) {
            emit('numerator_' + refdateStr, 1);
        }
    }
}
