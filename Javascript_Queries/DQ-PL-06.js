/**
 * Created by rrusk on 27/02/15.
 */
// Title: Of patients with a current anti-gout medication, what percentage has Gout on the problem list?
// Description: DQ-PL-06
// Note: All current records in endpoint have an active status since the Oscar E2E exporter only emits documents of active patients.


function map(patient) {

    var drugList = patient.medications();
    var problemList = patient.conditions();
    var targetProblemCodes = {
        "ICD9": ["\\b274"]
    };
    var targetMedications = {
        "whoATC": ['\\bM04A']
    };

    var durationMultiplier = 1.2;
    var prnMultiplier = 2.0;

    // Months are counted from 0 in Javascript so August is 7, for instance.
    var now = new Date();  // no parameters or yyyy,mm,dd if specified
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

    // Uses statusOfMedication to determine if drug is current.
    // Active if, when E2E record was exported, medication was long-term or before end date.
    // Test only makes sense for current records.
    function isActiveDrug(drug) {
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

    // Check for current medications
    function hasCurrentTargetMedication(takenDrugs, theTargetDrugs) {
        var list = takenDrugs.regex_match(theTargetDrugs);
        for (var i = 0; i < list.length; i++) {
            if (isActiveDrug(list[i]) || isDrugInWindow(list[i])) {
                /*emit(list[i]['json']['codes']['whoATC'], 1);
                var num1 = list[i]['json']['start_time'];
                var num2 = list[i]['json']['end_time'];
                var d1 = new Date(num1*1000);
                var d2 = new Date(num2*1000);
                var status = list[i]['json']['statusOfMedication']['value'];
                if (isPRN(list[i])) {
                    status=status+" isPRN";
                }
                if(isDrugInWindow(list[i])) {
                    status=status+" in window";
                }
                emit(""+status+" " +d1+","+d2, 1);*/
                return true;
            }
        }
        /*for (var i = 0; i < takenDrugs.length; i++) {
            if (takenDrugs[i].includesCodeFrom(list)) {
                if (isActiveDrug(takenDrugs[i]) || isDrugInWindow(takenDrugs[i])) {
                    var obj = JSON.stringify(takenDrugs[i]);
                    var type = typeof obj;
                    emit(type, 1);
                    return true;
                }
            }
        }*/
        return false;
    }

    emit('denominator', 0);
    emit('numerator', 0);

    if (currentRec && hasCurrentTargetMedication(drugList, targetMedications)) {
        emit('denominator', 1);
        if (hasProblemCode(targetProblemCodes)) {
            emit('numerator', 1);
        }
    }
}
