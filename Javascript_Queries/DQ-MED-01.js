/**
 * Created by rrusk on 15/07/14.
 */
// Title: What percentage of current medications is coded?
// Description: DQ-MED-01


function map(patient) {

    var durationMultiplier = 1.2;
    var prnMultiplier = 2.0;

    var drugList = patient.medications();

    // Months are counted from 0 in Javascript so August is 7, for instance.
    var now = new Date();  // no parameters or yyyy,mm,dd if specified
    //var start = addDate(now, 0, -12, -1); // 12 month study window; generally most
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

    // Test for PRN flag
    function isPRNold(drug) {
        return (drug.freeTextSig().indexOf(" E2E_PRN_FLAG") !== -1);
    }

    // Test that record is current (as of day before date at 0:00AM)
    function currentRecord(date) {
        var daybefore = new Date(date);
        daybefore.setDate(daybefore.getDate() - 1);
        daybefore.setHours(0, 0);
        return (patient['json']['effective_time'] > daybefore / 1000);
    }

    // Status is active if current long-term medication or before prescription end date
    function isCurrentDrug(drug) {
        var status = drug['json']['statusOfMedication']['value'];
        return currentRec && (status === 'active');
    }

    function isDrugInWindow(drug) {
        var drugStart = drug.indicateMedicationStart().getTime();
        var drugEnd = drug.indicateMedicationStop().getTime();

        var m = durationMultiplier;
        if (isPRNold(drug)) {
            m = prnMultiplier;
        }
        return (endDateOffset(drugStart, drugEnd, m) >= end && drugStart <= end);
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
            if (drugList[i].isPRN() != isPRNold(drugList[i])) {
                emit("prn_mismatch", 1);
            }
            if (drugList[i].isLongTerm() && !isCurrentDrug(drugList[i])) {
                emit("lt_mismatch1", 1);
            }
            if (isCurrentDrug(drugList[i]) || isDrugInWindow(drugList[i])) {
                if (!isDrugInWindow(drugList[i]) && !drugList[i].isLongTerm()) {
                    emit('lt_mismatch2', 1)
                }
                if (currentRec) {
                    //var num_prescriptions = drugList[i].orderInformation().length;
                    emit('denominator', 1);
                    if (hasCode(drugList[i])) {
                        emit('numerator', 1)
                    } else {
                        //emit('Unknown', num_prescriptions);
                    }
                }
            }
        }
    }

    emit('denominator', 0);
    emit('numerator', 0);
    if (currentRec) {
        checkMedications(drugList);
    }
}
