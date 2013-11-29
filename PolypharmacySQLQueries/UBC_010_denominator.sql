/* UBC-010 Denominator */


SELECT
  COUNT(d.demographic_no) AS Count
FROM
  demographic AS d
WHERE
  d.patient_status = 'AC'


