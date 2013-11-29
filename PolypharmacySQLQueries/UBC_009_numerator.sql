/* UBC-009 Numerator */

SELECT
  COUNT(d.demographic_no) AS Count
FROM
  demographic AS d

WHERE
  d.patient_status = 'AC' 
  


