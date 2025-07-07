-- models/dimensions/dim_upazilas.sql

SELECT
    upazila_code,
    upazila_name,
    district_name,
    division_name,
    ST_GeomFromText(geometry) AS boundary
FROM raw_geo_upazilas
WHERE country = 'Bangladesh';
