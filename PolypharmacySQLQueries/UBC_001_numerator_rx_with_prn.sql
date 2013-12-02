/* UBC-001 Numerator

this query counts Prescriptions (not unique meds) per patient and only includes meds that have a DIN and ATC.  the query also includes prn medications and excludes archived prescriptions 

*/


SELECT COUNT(DISTINCT d.demographic_no) AS 'Count' 
FROM demographic AS d
INNER JOIN drugs AS dr ON d.demographic_no = dr.demographic_no
WHERE d.patient_status = 'AC' AND 
CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) <  DATE_SUB( NOW(), INTERVAL 64 YEAR ) AND
d.demographic_no IN (
     SELECT
     dr.demographic_no
     FROM drugs AS dr
     WHERE 

	dr.archived = 0 AND
      	dr.regional_identifier IS NOT NULL AND
        dr.regional_identifier != '' AND
        dr.ATC IS NOT NULL AND
        dr.ATC != '' AND




rx_date <= NOW() AND
     (DATE_ADD(dr.rx_date, INTERVAL (DATEDIFF(dr.end_date,dr.rx_date)*1.2) DAY)) >= NOW()
     GROUP BY dr.demographic_no
     HAVING COUNT(dr.drugid) >= 5
     );
