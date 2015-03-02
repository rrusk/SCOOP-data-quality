/**
 * Created by rrusk on 25/02/15.
 */
// Title: What percentage of patients, calculated as active, has no current medications?
// Description: DQ-MED-03
// Note: All current records in endpoint have an active status since the Oscar E2E exporter only emits documents of active patients.


function map(patient) {


    var durationMultiplier = 1.2;
    var prnMultiplier = 2.0;

    var drugList = patient.medications();
    var encounterList = patient.encounters();

    // Months are counted from 0 in Javascript so August is 7, for instance.
    var now = new Date();  // no parameters or yyyy,mm,dd if specified
    var start = addDate(now, -2, 0, -1); // 24 month study window; generally most
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

    // a and b are javascript Date objects
    // Returns a with the m x calculated date offset added in
    function endDateOffset(a, b, m) {
        var start = new Date(a);
        var end = new Date(b);
        var diff = Math.floor((end - start) / (1000 * 3600 * 24));
        var offset = Math.floor(m * diff);
        return addDate(start, 0, 0, offset);
    }

    // Test that record is current (as of day before date at 0:00AM)
    function currentRecord(date) {
        var daybefore = new Date(date);
        daybefore.setDate(daybefore.getDate() - 1);
        daybefore.setHours(0,0);
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
        var status = drug['json']['statusOfMedication']['value'];
        return currentRec && (status === 'active');
    }

    // Test for PRN flag
    function isPRN(drug) {
        return (drug.freeTextSig().indexOf(" E2E_PRN flag") !== -1);
    }

    function isDrugInWindow(drug) {
        var drugStart = drug.indicateMedicationStart().getTime();
        var drugEnd = drug.indicateMedicationStop().getTime();

        var m = durationMultiplier;
        if (isPRN(drug)) {
            m = prnMultiplier;
        }
        return (endDateOffset(drugStart, drugEnd, m) >= end && drugStart <= end);
    }

    function hasCurrentMedication(drugList) {
        for (var i = 0; i < drugList.length; i++) {
            if (isCurrentDrug(drugList[i]) || isDrugInWindow(drugList[i])) {
                return true;
            }
        }
        return false;
    }

    emit('denominator', 0);
    emit('numerator', 0);
    if (currentRec && (hadEncounter(start, end) || hadRxEncounter(start, end))) {
            emit('denominator', 1);
        if (!hasCurrentMedication(drugList)) {
            emit('numerator', 1);
        }
    }
}
