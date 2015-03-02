/**
 * Created by rrusk on 25/02/15.
 */
// Title: Average number of prescriptions per encounter in the past 12 months
// Description: DQ-MED-02
// Note:


function map(patient) {

    var drugList = patient.medications();
    var encounterList = patient.encounters();

    // Months are counted from 0 in Javascript so August is 7, for instance.
    var now = new Date();  // no parameters or yyyy,mm,dd if specified
    var start = addDate(now, 0, -12, -1); // 12 month study window; generally most
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
        daybefore.setHours(0, 0);
        return (patient['json']['effective_time'] > daybefore / 1000);
    }

    function isDrugInWindow(drug) {
        var drugStart = drug.indicateMedicationStart().getTime();
        return (drugStart >= start && drugStart <= end);
    }

    function countMedications(drugList) {
        for (var i = 0; i < drugList.length; i++) {
            if (isDrugInWindow(drugList[i])) {
                emit('numerator', 1);
            }
        }
    }

    // Checks for encounters between start and end dates
    function countEncounters(startDate, endDate) {
        for (var i = 0; i < encounterList.length; i++) {
            if (encounterList[i].startDate() >= startDate &&
                encounterList[i].startDate() <= endDate) {
                emit('denominator', 1);
            }
        }
    }

    function listLengthRatio() {
        drugListLen = drugList.length;
        encounterListLen = encounterList.length;
        emit('drugListLen', drugListLen);
        emit('encounterListLen', encounterListLen);
    }

    emit('denominator', 0);
    emit('numerator', 0);
    if (currentRec) {
        countMedications(drugList);
        countEncounters(start, end);
        //listLengthRatio();
    }
}
