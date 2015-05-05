/**
 * Created by rrusk on 25/02/15.
 * Modified by rrusk on 2015/05/04.
 */
// Title: Average number of prescriptions per encounter in the past 12 months
// Description: DQ-MED-02
// Note 1: Only counts encounters in the case management notes.
// Note 2: Examines all prescription start dates rather than just latest prescription


function map(patient) {

    var drugList = patient.medications();
    var encounterList = patient.encounters();

    var refdateStr = setStoppDQRefDateStr(); // hQuery library function call
    var refdate = new Date(refdateStr);      // refdateStr is 'yyyy,mm,dd' with mm from 1-12
    refdate.setHours(23, 59);                // set to end of refdate then subtract one day
    var start = addDate(refdate, -1, 0, -1); // 12 month study window; generally most
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

    // Test that record is current (as of day before date at 0:00AM)
    function currentRecord(date) {
        var daybefore = new Date(date);
        daybefore.setHours(0, 0);
        return (patient['json']['effective_time'] > daybefore / 1000);
    }

    function countPrescriptionsInWindow(drug) {
        if (typeof drug.orderInformation() !== 'undefined' &&
            typeof drug.orderInformation().length != 0) {
            var drugStart;
            var drugEnd;
            for (var j = 0; j < drug.orderInformation().length; j++) {
                drugStart = drug.orderInformation()[j].orderDateTime();
                drugEnd = drug.orderInformation()[j].orderExpirationDateTime();
                drugStart.setHours(24, 1);
                drugEnd.setHours(47, 59);
                if (start <= drugStart && drugStart <= end) {
                    // emit('demo2='+patient['json']['emr_demographics_primary_key']+'; modDrugEnd='+modDrugEnd+'; end='+end+'; drugStart='+drugStart,1);
                    emit('numerator_' + refdateStr, 1);
                }
            }
        }
    }

    function countPrescriptions(drugList) {
        for (var i = 0; i < drugList.length; i++) {
            countPrescriptionsInWindow(drugList[i]);
        }
    }

    function countCaseMgmtNoteEncounters(startDate, endDate) {
        for (var i = 0; i < encounterList.length; i++) {
            if (encounterList[i].startDate() >= startDate &&
                encounterList[i].startDate() <= endDate) {
                emit('denominator_' + refdateStr, 1);
            }
        }
    }

    /*    function listLengthRatio() {
     var drugListLen = drugList.length;
     var encounterListLen = encounterList.length;
     emit('drugListLen', drugListLen);
     emit('encounterListLen', encounterListLen);
     }*/

    refdateStr = refdateStr.replace(/,/g, '');
    emit('denominator_' + refdateStr, 0);
    emit('numerator_' + refdateStr, 0);
    if (currentRec) {
        countPrescriptions(drugList);
        countCaseMgmtNoteEncounters(start, end);
        //listLengthRatio();
    }
}
