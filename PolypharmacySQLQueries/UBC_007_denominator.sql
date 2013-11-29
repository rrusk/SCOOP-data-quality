/* UBC-007 Denominator */

SELECT  COUNT(d.drugid) AS CountFROM  drugs AS dWHERE  d.rx_date >= DATE_SUB( NOW(), INTERVAL 12 MONTH ) AND
  d.archived = 0