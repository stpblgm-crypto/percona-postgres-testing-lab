-- Synthetic, session-local SQL contract; do not run against external databases.
INSERT INTO order_line (quantity) VALUES (2);
DO $lab$
BEGIN
    IF (SELECT count(*) FROM order_line WHERE quantity = 2) <> 1 THEN
        RAISE EXCEPTION 'positive quantity was not stored';
    END IF;
    BEGIN
        INSERT INTO order_line (quantity) VALUES (0);
        RAISE EXCEPTION 'contract failure: zero quantity was accepted';
    EXCEPTION WHEN check_violation THEN
        NULL;
    END;
    BEGIN
        INSERT INTO order_line (quantity) VALUES (NULL);
        -- Dedicated SQLSTATE distinguishes the intended BEFORE defect from
        -- connectivity, privilege, syntax or unrelated PostgreSQL errors.
        RAISE EXCEPTION USING ERRCODE = 'ZX001',
            MESSAGE = 'contract failure: NULL quantity was accepted';
    EXCEPTION WHEN not_null_violation THEN
        NULL;
    END;
END
$lab$;
SELECT 'CONTRACT_OK';
