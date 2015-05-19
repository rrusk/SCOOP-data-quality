/**
 * Created by rrusk on 25/02/15.
 * Modified by rrusk on 2015/05/05.
*/
// Title: What percentage of patients, calculated as active, has no current medications?
// Description: DQ-MED-03
// Note 1: All current records in endpoint have an active status since the Oscar E2E exporter
//         only emits documents of active patients.
// Note 2: Uses both case management notes and prescription events to determine active status

function map(patient) {


    var durationMultiplier = 1.2;
    var prnMultiplier = 2.0;

    var drugList = patient.medications();
    var encounterList = patient.encounters();

    var refdateStr = setStoppDQRefDateStr(); // hQuery library function call
    var refdate = new Date(refdateStr);      // refdateStr is 'yyyy,mm,dd' with mm from 1-12
    refdate.setHours(23, 59);                // set to end of refdate then subtract one day
    var start = addDate(refdate, -2, 0, -1); // 24 month study window; generally most
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

    // a and b are javascript Date objects
    // Returns a with the m x calculated date offset added in
    function endDateOffset(a, b, m) {
        var start = new Date(a);
        var end = new Date(b);
        var diff = Math.floor((end - start) / (1000 * 3600 * 24));
        var offset = Math.floor(m * diff);
        return addDate(start, 0, 0, offset);
    }

    // Test that record is current (as of day before study reference date at 0:00AM)
    function currentRecord(date) {
        var daybefore = new Date(date);
        daybefore.setHours(0, 0);
        return patient['json']['effective_time'] > daybefore / 1000;
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
                    drugPrescribed.setHours(24, 1);  // kludge to get start date to match rx_date in EMR
                    if (drugPrescribed >= startDate && drugPrescribed <= endDate) {
                        return true;
                    }
                }
            }
        }
        return false;
    }


    // Status is active if current long-term medication or before prescription end date
    function isCurrentDrug(drug) {
        return drug.isLongTerm() || isDrugInWindow(drug);
    }

    function isDrugInWindow(drug) {
        var drugStart; // = drug.indicateMedicationStart();
        //var drugStartInt = drugStart.getTime();
        var drugEnd; // = drug.indicateMedicationStop();
        //var drugEndInt = drugEnd.getTime();
        var m; // = durationMultiplier;
        //if (drug.isPRN()) {
        //    m = prnMultiplier;
        //}
        var modDrugEnd;
        //var modDrugEnd = endDateOffset(drugStartInt, drugEndInt, m);
        //drugStart.setHours(24, 1);   // kludge to get prescription start date to align with database date
        //modDrugEnd.setHours(47, 59); // kludge to get prescription end date to align with database date
        //if (modDrugEnd >= end && drugStart <= end) {
            // emit('demo1='+patient['json']['emr_demographics_primary_key']+'; modDrugEnd='+modDrugEnd+'; end='+end+'; drugStart='+drugStart,1);
        //    return true;
        //} else {
            // need to also search older prescriptions
            if (typeof drug.orderInformation() !== 'undefined' &&
                typeof drug.orderInformation().length != 0) {
                for (var j = 0; j < drug.orderInformation().length; j++) {
                    drugStart = drug.orderInformation()[j].orderDateTime();
                    drugEnd = drug.orderInformation()[j].orderExpirationDateTime();
                    m = durationMultiplier;
                    if (drug.orderInformation()[j].isPRN()) {
                        m = prnMultiplier;
                    }
                    modDrugEnd = endDateOffset(drugStart, drugEnd, m);
                    drugStart.setHours(24, 1);
                    modDrugEnd.setHours(47, 59);
                    if (modDrugEnd >= end && drugStart <= end) {
                        // emit('demo2='+patient['json']['emr_demographics_primary_key']+'; modDrugEnd='+modDrugEnd+'; end='+end+'; drugStart='+drugStart,1);
                        return true;
                    }
                }
            }
        //}
        return false;
    }

    function hasCurrentMedication(drugList) {
        for (var i = 0; i < drugList.length; i++) {
            if (isCurrentDrug(drugList[i])) {
                return true;
            }
        }
        return false;
    }

    refdateStr = refdateStr.replace(/,/g, '');
    emit('denominator_' + refdateStr, 0);
    emit('numerator_' + refdateStr, 0);
    if (currentRec && (hadEncounter(start, end) || hadRxEncounter(start, end))) {
        emit('denominator_' + refdateStr, 1);
        if (!hasCurrentMedication(drugList)) {
            emit('numerator_' + refdateStr, 1);
        }
    }
}
