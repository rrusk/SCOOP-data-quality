/* UBC-008 Denominator */

SELECT
  COUNT(DISTINCT d.demographic_no) AS 'Count'
FROM
  drugs AS d
WHERE d.rx_date >= DATE_SUB( NOW(), INTERVAL 12 MONTH ) AND
  d.archived = 0;
