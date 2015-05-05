/**
 * Created by rrusk on 27/02/15.
 * Modified by rrusk on 2015/05/05.
 */
// Title: Of patients with a current Tiotropium medication, what percentage has COPD on the problem list?
// Description: DQ-PL-04
// Note: All current records in endpoint have an active status since the Oscar E2E exporter only emits documents of active patients.


function map(patient) {

    var drugList = patient.medications();
    var problemList = patient.conditions();
    var targetProblemCodes = {
        "ICD9": ["\\b4912", "\\b492", "\\b496"]
    };
    var targetMedications = {
        "whoATC": ['R03BB04']
    };

    var durationMultiplier = 1.2;
    var prnMultiplier = 2.0;

    var refdateStr = setStoppDQRefDateStr();  // hQuery library function call
    var refdate = new Date(refdateStr);       // refdateStr is 'yyyy,mm,dd' with mm from 1-12
    refdate.setHours(23, 59);                 // set to end of refdate then subtract one day
    //var start = addDate(refdate, -2, 0, -1);  // 24 month encounter window
    var end = addDate(refdate, 0, 0, -1);     // recent records are from previous day
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
    function currentRecord(date) {
        var daybefore = new Date(date);
        daybefore.setHours(0,0);
        return patient['json']['effective_time'] > daybefore / 1000;

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
            }
        }*/
        return problemList.regex_match(theDxCodes).length;
    }

    // Status is active if current long-term medication or before prescription end date
    function isCurrentDrug(drug) {
        return drug.isLongTerm() || isDrugInWindow(drug);
    }

    function isDrugInWindow(drug) {
        var drugStart = drug.indicateMedicationStart();
        var drugStartInt = drugStart.getTime();
        var drugEnd = drug.indicateMedicationStop();
        var drugEndInt = drugEnd.getTime();
        var m = durationMultiplier;
        if (drug.isPRN()) {  // PRN only captured at medication level at present
            m = prnMultiplier;
        }
        var modDrugEnd = endDateOffset(drugStartInt, drugEndInt, m);
        drugStart.setHours(24, 1);   // kludge to get prescription start date to align with database date
        modDrugEnd.setHours(47, 59); // kludge to get prescription end date to align with database date
        if (modDrugEnd >= end && drugStart <= end) {
            // emit('demo1='+patient['json']['emr_demographics_primary_key']+'; modDrugEnd='+modDrugEnd+'; end='+end+'; drugStart='+drugStart,1);
            return true;
        } else {
            // need to also search older prescriptions
            if (typeof drug.orderInformation() !== 'undefined' &&
                typeof drug.orderInformation().length != 0) {
                for (var j = 0; j < drug.orderInformation().length; j++) {
                    drugStart = drug.orderInformation()[j].orderDateTime();
                    drugEnd = drug.orderInformation()[j].orderExpirationDateTime();
                    // PRN for individual prescriptions is not currently captured from E2E document
                    modDrugEnd = endDateOffset(drugStart, drugEnd, m);
                    drugStart.setHours(24, 1);
                    modDrugEnd.setHours(47, 59);
                    if (modDrugEnd >= end && drugStart <= end) {
                        // emit('demo2='+patient['json']['emr_demographics_primary_key']+'; modDrugEnd='+modDrugEnd+'; end='+end+'; drugStart='+drugStart,1);
                        return true;
                    }
                }
            }
        }
        return false;
    }

    // Check for medications
    function hasCurrentTargetMedication(takenDrugs, theTargetDrugs) {
        for (var i = 0; i < takenDrugs.length; i++) {
            if (takenDrugs[i].includesCodeFrom(theTargetDrugs)) {
                if (isCurrentDrug(takenDrugs[i])) {
                    return true;
                }
            }
        }
        return false;
    }

    refdateStr = refdateStr.replace(/,/g, '');
    emit('denominator_' + refdateStr, 0);
    emit('numerator_' + refdateStr, 0);
    if (currentRec && hasCurrentTargetMedication(drugList, targetMedications)) {
        emit('denominator_' + refdateStr, 1);
        if (hasProblemCode(targetProblemCodes)) {
            emit('numerator_' + refdateStr, 1);
        }
    }
}
