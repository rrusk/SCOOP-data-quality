/**
 * Created by rrusk on 02/03/15.
 */
// Title: Test that RegEx ignores leading spaces in ATC code
// Description: DQ RegEx test
function map(patient) {

    var drugList = patient.medications();
    var targetMedications = {
        "whoATC": ['\\bJ07BC20']
    };

    function checkMedications(takenDrugs) {
        for (var i = 0; i < takenDrugs.length; i++) {
                // Get all represented codes for each drug
                var codes = takenDrugs[i].medicationInformation().codedProduct();
                if (codes) {
                    for (var j = 0; j < codes.length; j++) {
                        var atc = codes[j].code();
                        if (atc === 'J07BC20') {
                            emit('J07BC20', 1);
                        } else if (atc === ' J07BC20') {
                            emit('_J07BC20', 1);
                        } else if (atc === '  J07BC20') {
                            emit('__J07BC20', 1);
                        }
                    }
                }
            }
        }


    // Check for current medications
    function hasTargetMedication(takenDrugs, theTargetDrugs) {
        var list = takenDrugs.regex_match(theTargetDrugs);
        for (var i = 0; i < list.length; i++) {
            var str = String(list[i]['json']['codes']['whoATC']);
            emit("RegEx: "+str.replace(' ','_'), 1);
        }
    }

    checkMedications(drugList);
    hasTargetMedication(drugList, targetMedications);

}
