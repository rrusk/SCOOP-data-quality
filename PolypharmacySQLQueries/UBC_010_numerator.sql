/* UBC-010 Numerator */

SELECT
  COUNT(d.demographic_no) AS Count
FROM
  demographic AS d

WHERE
  d.patient_status = 'AC' AND

  
CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) >= DATE_SUB( NOW(), INTERVAL 80 YEAR ) AND

CONCAT_WS( '-',d.year_of_birth,d.month_of_birth,d.date_of_birth ) <=  DATE_SUB( NOW(), INTERVAL 0 YEAR ) AND

d.sex = 'M';
