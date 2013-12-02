/* UBC-009 Numerator */


SELECT
  COUNT(DISTINCT d.demographic_no) AS Count /* DISTINCT keyword is optional */
FROM
  demographic AS d
WHERE
  d.patient_status = 'AC' AND
  d.demographic_no NOT IN (
    SELECT DISTINCT
      e.demographicNo
    FROM
      eChart AS e
    WHERE
      e.`timeStamp` >= DATE_SUB( NOW(), INTERVAL 36 MONTH )
  );
