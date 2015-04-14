/**
 * Created by rrusk on 13/04/15.
 */
// Title: What percentage of current medications is coded?
// Description: DQ-MED-01


function map(patient) {

    var durationMultiplier = 1.2;
    var prnMultiplier = 2.0;

    var drugList = patient.medications();

    var refDate = setStoppRefDate();
    var end = addDate(refDate, 0, 0, -1);    // most recent records are from previous day
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

    // Test that record is current (as of day before date at 0:00AM)
    // This test is necessary since E2E only exports active records.
    // When a patient's status is no long 'AC', the record in mongo
    // will no long be updated.
    function currentRecord(date) {
        return (patient['json']['effective_time'] > date / 1000);
    }

    // Status is active if current long-term medication or before prescription end date
    function isCurrentDrug(drug) {
        return drug.isLongTerm() || isDrugInWindow(drug);
    }

    function isDrugInWindow(drug) {
        var drugStart = drug.indicateMedicationStart().getTime();
        var drugEnd = drug.indicateMedicationStop().getTime();

        var m = durationMultiplier;
        if (drug.isPRN()){
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
            if (isCurrentDrug(drugList[i])) {
                emit('denominator', 1);
                if (hasCode(drugList[i])) {
                    emit('numerator', 1)
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
