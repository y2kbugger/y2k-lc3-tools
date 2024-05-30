INSERT INTO trace VALUES ('Reticulating splines...');

CREATE TABLE signal(
    clk BOOLEAN,
    is_running BOOLEAN,
    tracing BOOLEAN
    );
INSERT INTO signal VALUES (
    FALSE,
    FALSE,
    FALSE
    );

CREATE TABLE register(
    R0 INT,
    R1 INT,
    R2 INT,
    R3 INT,
    R4 INT,
    R5 INT,
    R6 INT,
    R7 INT,
    PC INT,
    COND INT
    );
INSERT INTO register VALUES (
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0
);

CREATE TABLE memory(
    address INT UNIQUE,
    value INT
    );

pragma recursive_triggers = 1;

-- detect rising and falling edges to trigger a step
DROP TRIGGER IF EXISTS clk_trigger;
CREATE TRIGGER clk_trigger
AFTER UPDATE OF clk ON signal
BEGIN
    INSERT INTO trace VALUES (
        CASE
            WHEN OLD.clk = 0 AND NEW.clk = 1 THEN 'rising edge'
            WHEN OLD.clk = 1 AND NEW.clk = 0 THEN 'falling edge'
            ELSE 'no edge detected'  -- Optional, for other cases
        END
    );
END;
