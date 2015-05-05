/**
 * Created by rrusk on 25/02/15.
 * Modified by rrusk on 2015/05/05.
 */
// Title: What percentage of patients, 12 AND OVER, calculated as active, has at least one documented problem on the problem list (documented in the past 12 months)?
// Description: DQ-PL-02
// Note: All current records in endpoint have an active status since the Oscar E2E exporter only emits documents of active patients.


function map(patient) {

    var age = 12;
    var drugList = patient.medications();
    var encounterList = patient.encounters();
    var problemList = patient.conditions();

    var refdateStr = setStoppDQRefDateStr();  // hQuery library function call
    var refdate = new Date(refdateStr);       // refdateStr is 'yyyy,mm,dd' with mm from 1-12
    refdate.setHours(23, 59);                 // set to end of refdate then subtract one day
    var start = addDate(refdate, -2, 0, -1);  // 24 month encounter window
    var prStart = addDate(refdate, -1, 0, -1);// 12 month problem list; generally most
    var end = addDate(refdate, 0, 0, -1);     // recent records are from previous day
    var currentRec = currentRecord(end);

    var age = patient.age(end);

    // Shifts date by year, month, and date specified
    function addDate(date, y, m, d) {
        var n = new Date(date);
        n.setFullYear(date.getFullYear() + (y || 0));
        n.setMonth(date.getMonth() + (m || 0));
        n.setDate(date.getDate() + (d || 0));
        return n;
    }

    // Test that record is current (as of day before date at 0:00AM)
    function currentRecord(date) {
        var daybefore = new Date(date);
        daybefore.setHours(0,0);
        return patient['json']['effective_time'] > daybefore / 1000;

    }

    // Checks if patient is older than ageLimit
    function targetPopulation(ageLimit) {
        return patient.age(end) >= ageLimit;
    }

    // Checks for encounter between start and end dates
    function hadEncounter(startDate, endDate) {
        for (var i = 0; i < encounterList.length; i++) {
            if (encounterList[i].startDate() >= startDate &&
                encounterList[i].startDate() <= endDate) {
                return true;
            }
        }
        return false;
    }

    // Checks for prescription encounter between start and end dates
    function hadRxEncounter(startDate, endDate) {
        for (var i = 0; i < drugList.length; i++) {
            if (typeof drugList[i].orderInformation() !== 'undefined' &&
                typeof drugList[i].orderInformation().length != 0) {
                for (var j = 0; j < drugList[i].orderInformation().length; j++) {
                    var drugPrescribed = drugList[i].orderInformation()[j].orderDateTime();
                    drugPrescribed.setHours(24,1);  // kludge to get start date to match rx_date in EMR
                    if (drugPrescribed >= startDate && drugPrescribed <= endDate) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    // Checks for encounter between start and end dates
    function hasProblem(startDate, endDate) {
        for (var i = 0; i < problemList.length; i++) {
            if (problemList[i].startDate() >= startDate &&
                problemList[i].startDate() <= endDate) {
                return true;
            }
        }
        return false;
    }

    refdateStr = refdateStr.replace(/,/g, '');
    emit('denominator_' + refdateStr, 0);
    emit('numerator_' + refdateStr, 0);
    if (currentRec && targetPopulation(age) && (hadEncounter(start, end) || hadRxEncounter(start, end))) {
        emit('denominator_' + refdateStr, 1);
        if (hasProblem(prStart, end)) {
            emit('numerator_' + refdateStr, 1);
        }
    }
}
