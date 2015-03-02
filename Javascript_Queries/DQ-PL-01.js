/**
 * Created by rrusk on 26/02/15.
 */
// Title: What percentage of problems on the problem list, documented in the past 12 months, has a diagnostic code?
// Description: DQ-PL-01
// Note: This query isn't useful since the Oscar E2E only exports coded problems.  If it were to include uncoded problems
// then the health-data-standards importer would have to make them appear coded for the patientapi to process them.

function map(patient) {

    var conditionList = patient.conditions();

    /*var rawConditionList = patient["json"]['conditions']
    emit('cL', conditionList.length);
    if (typeof rawConditionList !== 'undefined') {
        emit('rL', rawConditionList.length);
    } else {
        emit('rL undefined', 1);
    }*/

    // Months are counted from 0 in Javascript so August is 7, for instance.
    var now = new Date();  // no parameters or yyyy,mm,dd if specified
    var start = addDate(now, -1, 0, -1); // 12 month window; generally most
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
        return patient['json']['effective_time'] > daybefore/1000;
    }

    function countCodedConditions(startDate, endDate)  {
        for (var i = 0; i < conditionList.length; i++) {
            if (conditionList[i].startDate() !== 'undefined' && conditionList[i].startDate() >= startDate &&
                conditionList[i].startDate() <= endDate) {
                emit('denominator', 1);
                if (conditionList[i].isUsable()) { // checks for code
                    emit('numerator', 1);
                }
            }
        }
    }

    emit('denominator', 0);
    emit('numerator', 0);
    if (currentRec) {
        countCodedConditions(start, end);
    }
}