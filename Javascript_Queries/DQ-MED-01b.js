/**
 * Created by rrusk on 11/05/15.
 */
// Title: What percentage of current medications is coded? (ignoring duration multiplier, PRN and long term flag)
// Modified by rrusk on 11/05/15.
// Description: DQ-MED-01b
// Note 1: The PRN flag is not currently captured for individual prescription events.

function map(patient) {

    var drugList = patient.medications();

    var refdateStr = setStoppDQRefDateStr(); // hQuery library function call
    var refdate = new Date(refdateStr);      // refdateStr is 'yyyy,mm,dd' with mm from 1-12
    refdate.setHours(23, 59);                // set to end of refdate then subtract one day
    // var start = addDate(refdate, -2, 0, -1); // 24 month study window; generally most
    var end = addDate(refdate, 0, 0, -1);    // recent records are from previous day
    var currentRec = currentRecord(end);
    refdateStr = refdateStr.replace(/,/g, '');

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

    // Status is active if current long-term medication or before prescription end date
    function scanPrescriptions(drug) {
        var drugStart;
        var drugEnd;
        var coded = hasCode(drug);
        // count all "current" prescriptions
        if (typeof drug.orderInformation() !== 'undefined' &&
            typeof drug.orderInformation().length != 0) {
            for (var j = 0; j < drug.orderInformation().length; j++) {
                drugStart = drug.orderInformation()[j].orderDateTime();
                drugEnd = drug.orderInformation()[j].orderExpirationDateTime();
                drugStart.setHours(24, 1);   // kludge to get prescription start date to align with database date
                drugEnd.setHours(47, 59); // kludge to get prescription end date to align with database date
                if (drugEnd >= end && drugStart <= end) {
                    // emit('d at index '+j, 1);
                    // emit('demo2='+patient['json']['emr_demographics_primary_key']+'; modDrugEnd='+modDrugEnd+'; end='+end+'; drugStart='+drugStart,1);
                    emit('denominator_' + refdateStr, 1);
                    if (coded) {
                        // emit('n at index '+j, 1);
                        emit('numerator_' + refdateStr, 1);
                    }
                }
            }
        }
    }

    function hasCode(drug) {
        var codes = drug.medicationInformation().codedProduct();
        if (codes) {
            for (var j = 0; j < codes.length; j++) {
                if (codes[j].codeSystemName() && codes[j].codeSystemName() !== 'Unknown' &&
                    codes[j].code() && codes[j].code() !== 'NI') {
                    return true;
                }
            }
        }
        return false;
    }

    function checkMedications(drugList) {
        for (var i = 0; i < drugList.length; i++) {
            scanPrescriptions(drugList[i]);
        }
    }

    emit('denominator_' + refdateStr, 0);
    emit('numerator_' + refdateStr, 0);
    if (currentRec) {
        checkMedications(drugList);
    }
}