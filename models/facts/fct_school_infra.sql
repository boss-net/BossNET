-- models/facts/fct_school_infra.sql

SELECT
    eiin,
    school_name,
    district,
    division,
    total_classrooms,
    has_library,
    has_science_lab,
    toilet_count,
    student_teacher_ratio
FROM raw_school_data
WHERE country = 'Bangladesh';
