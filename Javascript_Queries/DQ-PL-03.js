/**
 * Created by rrusk on 27/02/15.
 */
// Title: What percentage of patients, calculated as active, 12 and over, has Diabetes on the problem list?
// Description: DQ-PL-03
// Note: All current records in endpoint have an active status since the Oscar E2E exporter only emits documents of active patients.


function map(patient) {

    var age = 12;
    var drugList = patient.medications();
    var encounterList = patient.encounters();
    var problemList = patient.conditions();
    var targetProblemCodes = {
        "ICD9": ["\\b250"]
    };

    // Months are counted from 0 in Javascript so August is 7, for instance.
    var now = new Date();  // no parameters or yyyy,mm,dd if specified
    var start = addDate(now, -2, 0, -1); // 24 month window; generally most
    var end = addDate(now, 0, 0, -1);    // recent records are from previous day
    var currentRec = currentRecord(now);

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
        daybefore.setDate(daybefore.getDate() - 1);
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
                    if (drugPrescribed >= startDate && drugPrescribed <= endDate) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    // Checks for patients with DxCode
    function hasProblemCode(theDxCodes) {
        /*list = problemList.regex_match(theDxCodes);
        for (var i = 0; i < list.length; i++) {
            emit(list[i]['json']['codes']['ICD9'], 1);
        }
        for (var i = 0; i < problemList.length; i++) {
            if (problemList[i].regex_includesCodeFrom(theDxCodes)) {
                emit(problemList[i]['json']['codes']['ICD9'], 1);
                if (problemList[i]['json']['codes']['ICD9'][0] != "244" &&
                    problemList[i]['json']['codes']['ICD9'][0] != "245") {
                    emit(problemList[i], 1);
                }
            }
        }*/
        return problemList.regex_match(theDxCodes).length;
    }

    emit('denominator', 0);
    emit('numerator', 0);
    if (currentRec && targetPopulation(age) && (hadEncounter(start, end) || hadRxEncounter(start, end))) {
        emit('denominator', 1);
        if (hasProblemCode(targetProblemCodes)) {
            emit('numerator', 1);
        }
    }
}
