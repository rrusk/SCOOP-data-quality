/**
 * Created by rrusk on 2015/02/20.
 */
// Title: What percentage of patients, calculated as active, has no documented date of birth?
// Description: DQ-DEM-04
// Note: Checks for patients that are more than 120 years old.  The Oscar E2E records set birthDate to 0001,01,01 if not otherwise recorded.

function map(patient) {

  var drugList = patient.medications();
  var encounterList = patient.encounters();

  // Months are counted from 0 in Javascript so August is 7, for instance.
  var now = new Date();  // no parameters or yyyy,mm,dd if specified
  var start = addDate(now, -2, 0, -1); // 24 month study window; generally most
  var end = addDate(now, 0, 0, -1);    // recent records are from previous day
  var currentRec = currentRecord(now);

  var age = patient.age(end);

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
    daybefore = new Date(date);
    daybefore.setDate(daybefore.getDate() - 1);
    daybefore.setHours(0,0);
    if (patient['json']['effective_time'] > daybefore/1000) {
      return true;
    }
    return false;
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
                typeof drugList[i].orderInformation().length !== 0) {
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

  // Checks if patient is out of age range
  function incorrectAge() {
     return (age > 120);
  }

  emit('denominator', 0);
  emit('numerator', 0);
  if (currentRec && (hadEncounter(start, end) || hadRxEncounter(start, end))) {
    emit('denominator', 1);
    if (incorrectAge()) {
      emit('numerator', 1);
    }
  }
}
