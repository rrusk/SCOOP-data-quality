/* UBC-007 Numerator */

SELECT
  COUNT(d.drugid) AS Count
FROM drugs AS d
WHERE
  d.rx_date >= DATE_SUB( NOW(), INTERVAL 12 MONTH ) AND
  (d.regional_identifier IS NULL OR d.regional_identifier = '') AND
  (d.ATC IS NULL OR d.ATC = '') AND
  d.archived = 0;
