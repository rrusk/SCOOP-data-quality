/**
 * Created by rrusk on 2015/02/20.
 */
// Title: What percentage of patients, calculated as active, has an invalid date of birth?
// Description: DQ-DEM-03
// Note: Checks for patients that are more than 120 years old or younger than yesterday.  A useful check to add would be that the patient was born before the first recorded encounter.

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

  // Checks for encounter before birthdate
  function hasInvalidEncounterDate(birthdate) {
      for (var i = 0; i < encounterList.length; i++) {
	  if (encounterList[i].startDate() < birthdate) {
	      emit("e_d_no: " + patient["json"]["emr_demographics_primary_key"] + " edate: " + encounterList[i].startDate() + " birthdate: "+birthdate,1);
              return true;
	  }
      }
      for (var i = 0; i < drugList.length; i++) {
	  if (typeof drugList[i].orderInformation() !== 'undefined' &&
              typeof drugList[i].orderInformation().length != 0) {
              for (var j = 0; j < drugList[i].orderInformation().length; j++) {
		  var drugPrescribedDate = drugList[i].orderInformation()[j].orderDateTime();
		  if (drugPrescribedDate < birthdate) {
		      emit("rx_d_no: " + patient["json"]["emr_demographics_primary_key"],1);
		      return true;
		  }
            }
        }
      }
      return false;
  }

  // Checks if patient is out of age range
  function incorrectAge() {
     return (age < 0 || age > 120);// || hasInvalidEncounterDate(patient.birthtime()));
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
