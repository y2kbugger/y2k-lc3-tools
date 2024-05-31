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

-- CLK Rising edge detection
DROP TRIGGER IF EXISTS clk_trigger_rising;
CREATE TRIGGER clk_trigger_rising
AFTER UPDATE OF clk ON signal
    WHEN OLD.clk = 0 AND NEW.clk = 1
BEGIN
    -- Insert into trace table based on clk edge detection
    INSERT INTO trace VALUES ('clk rising edge');
END;

-- CLK Falling edge detection
DROP TRIGGER IF EXISTS clk_trigger_falling;
CREATE TRIGGER clk_trigger_falling
AFTER UPDATE OF clk ON signal
    WHEN OLD.clk = 1 AND NEW.clk = 0
BEGIN
    -- Insert into trace table based on clk edge detection
    INSERT INTO trace VALUES ('clk falling edge');

    -- Update PC in register table based on falling edge detection
    UPDATE register
        SET PC = PC + 1;
END;
