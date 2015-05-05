/**
 * Created by rrusk on 26/02/15.
 * Modified by rrusk on 2015/05/05.
 */
// Title: What percentage of problems on the problem list, documented in the past 12 months, has a diagnostic code?
// Description: DQ-PL-01
// Note: This query isn't useful since the Oscar E2E only exports coded problems.
//       If it were to include uncoded problems then the health-data-standards importer
//       would have to make them appear coded for the patientapi to process them.

function map(patient) {

    var conditionList = patient.conditions();

    /*var rawConditionList = patient["json"]['conditions']
    emit('cL', conditionList.length);
    if (typeof rawConditionList !== 'undefined') {
        emit('rL', rawConditionList.length);
    } else {
        emit('rL undefined', 1);
    }*/

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
        daybefore.setHours(0,0);
        return patient['json']['effective_time'] > daybefore/1000;
    }

    function countCodedConditions(startDate, endDate)  {
        for (var i = 0; i < conditionList.length; i++) {
            if (conditionList[i].startDate() !== 'undefined' && conditionList[i].startDate() >= startDate &&
                conditionList[i].startDate() <= endDate) {
                emit('denominator_' + refdateStr, 1);
                if (conditionList[i].isUsable()) { // checks for code
                    emit('numerator_' + refdateStr, 1);
                }
            }
        }
    }


    refdateStr = refdateStr.replace(/,/g, '');
    emit('denominator_' + refdateStr, 0);
    emit('numerator_' + refdateStr, 0);
    if (currentRec) {
        countCodedConditions(start, end);
    }
}