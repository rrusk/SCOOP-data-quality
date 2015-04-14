/**
 * Created by rrusk on 09/03/15.
 */
// Title: Elderly Patients with active status
// Description: Potential STOPP Population
// Obtain estimate of number of STOPP patients (>= 65y as of 4 months ago at beginning of study window)
// Compare to:
// mysql> SELECT COUNT(d.demographic_no) AS Count FROM demographic AS d
//   WHERE d.patient_status = 'AC' AND
//   CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) <=
//   DATE_SUB( DATE_SUB(NOW(), INTERVAL 4 MONTH), INTERVAL 65 YEAR);

function map(patient) {

    var ageElderly = 65;
    var ageMax = 150;

    // Months are counted from 0 in Javascript so August is 7, for instance.
    var now = new Date();  // no parameters or yyyy,mm,dd if specified
    var start = addDate(now, 0, -4, -1); // four month study window; generally most
    //var end = addDate(now, 0, 0, -1);    // recent records are from previous day
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
        return patient['json']['effective_time'] > daybefore / 1000;
    }

    // Checks if patient is older than ageLimit at start of window
    function targetPopulation(ageLimit, ageUpper) {
        if (ageUpper === undefined) {
            ageUpper = ageMax;
        }
        return (patient.age(start) >= ageLimit) &&  (patient.age(start) <= ageUpper);
    }

    emit('denominator', 1);
    emit('numerator', 0);
    if (currentRec && targetPopulation(ageElderly)) {
        emit('numerator', 1);
    }
}