
CREATE TABLE node_metrics
(
    timestamp                  BIGINT NOT NULL,
    node_name                  VARCHAR(255),
    metric_source              VARCHAR(255),

    -- Resource utilization (from cAdvisor)
    cpu_utilization_percent    DOUBLE PRECISION,
    total_cpu_assigned         INTEGER,
    machine_cpu_cores          INTEGER,
    memory_utilization_percent DOUBLE PRECISION,
    memory_utilization_bytes   DOUBLE PRECISION,
    memory_assigned_bytes      DOUBLE PRECISION,
    machine_memory_total_bytes DOUBLE PRECISION,


    -- Power metrics (from Kepler) sum of all this is the total power consumption in watts
    cpu_core_watts             DOUBLE PRECISION,
    cpu_package_watts          DOUBLE PRECISION,
    memory_power_watts         DOUBLE PRECISION,
    platform_watts             DOUBLE PRECISION,
    energy_watts               DOUBLE PRECISION,
    created_at                 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (timestamp, node_name)
);

-- Energy forecast inserts for EuroSolar Netherlands for the upcoming month
-- 4 time slots per day (6-hour intervals): 00:00-06:00, 06:00-12:00, 12:00-18:00, 18:00-24:00


CREATE TABLE energy_availability
(
    id                          SERIAL PRIMARY KEY,
    -- Provider info (will be duplicated but keeps it simple)
    provider_name               VARCHAR(100)             NOT NULL,
    location                    VARCHAR(255),
    energy_source_type          VARCHAR(50),
    -- Time slot details
    slot_start_time             TIMESTAMP WITH TIME ZONE NOT NULL,
    slot_end_time               TIMESTAMP WITH TIME ZONE NOT NULL,
    -- Energy data
    available_watts             DECIMAL(15, 4)           NOT NULL,
    guaranteed_minimum_watts    DECIMAL(15, 4),
    potential_maximum_watts     DECIMAL(15, 4),
    -- Forecast metadata
    confidence_percentage       DECIMAL(5, 2),
    weather_dependency          BOOLEAN                  DEFAULT false,
    -- Forecast management
    forecast_date               DATE                     NOT NULL,     -- Which day's forecast this belongs to
    is_active                   BOOLEAN                  DEFAULT true, -- To handle updates
    created_at                  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- October 21 - November 28, 2025
-- 4 time slots per day (6-hour intervals in CET - Central European Time UTC+1)
-- Time slots: 01:00-07:00, 07:00-13:00, 13:00-19:00, 19:00-01:00 (next day)

-- Day 1: 2025-10-21 (Tuesday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-21 01:00:00+01', '2025-10-21 07:00:00+01', 2500.0000, 1500.0000, 4000.0000, 95.50, false, '2025-10-21',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-21 07:00:00+01', '2025-10-21 13:00:00+01', 18720.0000, 16320.0000, 21120.0000, 88.75, true,
        '2025-10-21', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-21 13:00:00+01', '2025-10-21 19:00:00+01', 47500.0000, 42500.0000, 50000.0000, 90.30, true,
        '2025-10-21', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-21 19:00:00+01', '2025-10-22 01:00:00+01', 9000.0000, 4800.0000, 13200.0000, 87.40, true,
        '2025-10-21', true, NOW());

-- Generate data for remaining days of October (22-31)
-- Day 2: 2025-10-22 (Wednesday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-22 01:00:00+01', '2025-10-22 07:00:00+01', 2200.0000, 1200.0000, 3500.0000, 96.20, false, '2025-10-22',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-22 07:00:00+01', '2025-10-22 13:00:00+01', 34560.0000, 29760.0000, 39360.0000, 82.15, true,
        '2025-10-22', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-22 13:00:00+01', '2025-10-22 19:00:00+01', 40800.0000, 34560.0000, 47040.0000, 75.60, true,
        '2025-10-22', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-22 19:00:00+01', '2025-10-23 01:00:00+01', 10800.0000, 7200.0000, 7200.0000, 71.80, true,
        '2025-10-22', true, NOW());

-- Day 3: 2025-10-23 (Friday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-23 01:00:00+01', '2025-10-23 07:00:00+01', 2800.0000, 1800.0000, 4200.0000, 95.80, false, '2025-10-23',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-23 07:00:00+01', '2025-10-23 13:00:00+01', 38880.0000, 34560.0000, 43200.0000, 88.90, true,
        '2025-10-23', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-23 13:00:00+01', '2025-10-23 19:00:00+01', 48000.0000, 42240.0000, 50000.0000, 93.40, true,
        '2025-10-23', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-23 19:00:00+01', '2025-10-24 01:00:00+01', 10560.0000, 9000.0000, 14400.0000, 89.60, true,
        '2025-10-23', true, NOW());

-- Day 4: 2025-10-24 (Saturday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-24 01:00:00+01', '2025-10-24 07:00:00+01', 3100.0000, 2100.0000, 4500.0000, 97.30, false, '2025-10-24',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-24 07:00:00+01', '2025-10-24 13:00:00+01', 35040.0000, 29760.0000, 40320.0000, 84.50, true,
        '2025-10-24', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-24 13:00:00+01', '2025-10-24 19:00:00+01', 44160.0000, 39360.0000, 48900.0000, 86.80, true,
        '2025-10-24', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-24 19:00:00+01', '2025-10-25 01:00:00+01', 11400.0000, 7800.0000, 12480.0000, 81.20, true,
        '2025-10-24', true, NOW());

-- Day 5: 2025-10-25 (Sunday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-25 01:00:00+01', '2025-10-25 07:00:00+01', 2900.0000, 1900.0000, 4300.0000, 96.90, false, '2025-10-25',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-25 07:00:00+01', '2025-10-25 13:00:00+01', 38160.0000, 33360.0000, 42960.0000, 89.10, true,
        '2025-10-25', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-25 13:00:00+01', '2025-10-25 19:00:00+01', 48900.0000, 44160.0000, 50000.0000, 94.20, true,
        '2025-10-25', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-25 19:00:00+01', '2025-10-26 01:00:00+01', 11520.0000, 10800.0000, 14880.0000, 90.50, true,
        '2025-10-25', true, NOW());

-- Day 6: 2025-10-26 (Monday) - Cloudy weather expected
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-26 01:00:00+01', '2025-10-26 07:00:00+01', 1500.0000, 800.0000, 2200.0000, 98.20, false, '2025-10-26',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-26 07:00:00+01', '2025-10-26 13:00:00+01', 16320.0000, 10080.0000, 22560.0000, 65.40, true,
        '2025-10-26', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-26 13:00:00+01', '2025-10-26 19:00:00+01', 21600.0000, 15360.0000, 27840.0000, 58.70, true,
        '2025-10-26', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-26 19:00:00+01', '2025-10-27 01:00:00+01', 7200.0000, 7000.0000, 10200.0000, 62.80, true,
        '2025-10-26', true, NOW());

-- Continue with remaining August days (27-31) and September days (1-21)
-- Day 7: 2025-10-27 (Tuesday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-27 01:00:00+01', '2025-10-27 07:00:00+01', 2600.0000, 1600.0000, 3800.0000, 97.60, false, '2025-10-27',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-27 07:00:00+01', '2025-10-27 13:00:00+01', 36720.0000, 31920.0000, 41520.0000, 87.30, true,
        '2025-10-27', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-27 13:00:00+01', '2025-10-27 19:00:00+01', 46080.0000, 40320.0000, 50000.0000, 91.50, true,
        '2025-10-27', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-27 19:00:00+01', '2025-10-28 01:00:00+01', 10080.0000, 8400.0000, 13440.0000, 86.70, true,
        '2025-10-27', true, NOW());

-- Day 8: 2025-10-28 (Wednesday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-28 01:00:00+01', '2025-10-28 07:00:00+01', 2400.0000, 1400.0000, 3600.0000, 95.20, false, '2025-10-28',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-28 07:00:00+01', '2025-10-28 13:00:00+01', 35520.0000, 30720.0000, 40320.0000, 86.80, true,
        '2025-10-28', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-28 13:00:00+01', '2025-10-28 19:00:00+01', 42720.0000, 37920.0000, 47520.0000, 88.90, true,
        '2025-10-28', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-28 19:00:00+01', '2025-10-29 01:00:00+01', 10200.0000, 11000.0000, 23000.0000, 84.50, true,
        '2025-10-28', true, NOW());

-- Day 9: 2025-10-29 (Thursday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-29 01:00:00+01', '2025-10-29 07:00:00+01', 2700.0000, 1700.0000, 3900.0000, 96.50, false, '2025-10-29',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-29 07:00:00+01', '2025-10-29 13:00:00+01', 36960.0000, 32160.0000, 41760.0000, 89.20, true,
        '2025-10-29', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-29 13:00:00+01', '2025-10-29 19:00:00+01', 44640.0000, 39840.0000, 49440.0000, 91.40, true,
        '2025-10-29', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-29 19:00:00+01', '2025-10-30 01:00:00+01', 9600.0000, 8400.0000, 12960.0000, 87.80, true,
        '2025-10-29', true, NOW());

-- Day 10: 2025-10-30 (Friday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-30 01:00:00+01', '2025-10-30 07:00:00+01', 2500.0000, 1500.0000, 3700.0000, 97.10, false, '2025-10-30',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-30 07:00:00+01', '2025-10-30 13:00:00+01', 17280.0000, 31200.0000, 40800.0000, 88.60, true,
        '2025-10-30', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-30 13:00:00+01', '2025-10-30 19:00:00+01', 43680.0000, 38880.0000, 48480.0000, 90.30, true,
        '2025-10-30', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-30 19:00:00+01', '2025-10-31 01:00:00+01', 18500.0000, 7500.0000, 25500.0000, 86.40, true,
        '2025-10-30', true, NOW());

-- Day 11: 2025-10-31 (Saturday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-31 01:00:00+01', '2025-10-31 07:00:00+01', 2800.0000, 1800.0000, 4000.0000, 96.80, false, '2025-10-31',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-31 07:00:00+01', '2025-10-31 13:00:00+01', 37440.0000, 32640.0000, 42240.0000, 89.50, true,
        '2025-10-31', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-31 13:00:00+01', '2025-10-31 19:00:00+01', 45120.0000, 40320.0000, 49920.0000, 91.70, true,
        '2025-10-31', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-10-31 19:00:00+01', '2025-11-01 01:00:00+01', 19500.0000, 13500.0000, 26500.0000, 88.20, true,
        '2025-10-31', true, NOW());

-- NOVEMBER 2025 DATA (Days 12-32: November 1-21)
-- Day 12: 2025-11-01 (Sunday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-01 01:00:00+01', '2025-11-01 07:00:00+01', 2600.0000, 1600.0000, 3800.0000, 95.30, false, '2025-11-01',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-01 07:00:00+01', '2025-11-01 13:00:00+01', 36480.0000, 31680.0000, 41280.0000, 87.60, true,
        '2025-11-01', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-01 13:00:00+01', '2025-11-01 19:00:00+01', 43200.0000, 38400.0000, 48000.0000, 89.40, true,
        '2025-11-01', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-01 19:00:00+01', '2025-11-02 01:00:00+01', 9600.0000, 10000.0000, 10560.0000, 85.20, true,
        '2025-11-01', true, NOW());

-- Day 13: 2025-11-02 (Monday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-02 01:00:00+01', '2025-11-02 07:00:00+01', 2300.0000, 1300.0000, 3500.0000, 94.80, false, '2025-11-02',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-02 07:00:00+01', '2025-11-02 13:00:00+01', 34560.0000, 29760.0000, 39360.0000, 86.40, true,
        '2025-11-02', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-02 13:00:00+01', '2025-11-02 19:00:00+01', 41760.0000, 36960.0000, 46560.0000, 88.10, true,
        '2025-11-02', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-02 19:00:00+01', '2025-11-03 01:00:00+01', 8700.0000, 8500.0000, 20500.0000, 83.90, true,
        '2025-11-02', true, NOW());

-- Day 14: 2025-11-03 (Tuesday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-03 01:00:00+01', '2025-11-03 07:00:00+01', 2400.0000, 1400.0000, 3600.0000, 95.60, false, '2025-11-03',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-03 07:00:00+01', '2025-11-03 13:00:00+01', 35520.0000, 30720.0000, 40320.0000, 87.20, true,
        '2025-11-03', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-03 13:00:00+01', '2025-11-03 19:00:00+01', 42720.0000, 37920.0000, 47520.0000, 88.80, true,
        '2025-11-03', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-03 19:00:00+01', '2025-11-04 01:00:00+01', 15500.0000, 9500.0000, 21500.0000, 84.60, true,
        '2025-11-03', true, NOW());

-- Day 15: 2025-11-04 (Wednesday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-04 01:00:00+01', '2025-11-04 07:00:00+01', 2200.0000, 1200.0000, 3400.0000, 94.20, false, '2025-11-04',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-04 07:00:00+01', '2025-11-04 13:00:00+01', 33600.0000, 28800.0000, 38400.0000, 85.80, true,
        '2025-11-04', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-04 13:00:00+01', '2025-11-04 19:00:00+01', 40800.0000, 17280.0000, 45600.0000, 87.50, true,
        '2025-11-04', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-04 19:00:00+01', '2025-11-05 01:00:00+01', 7800.0000, 7000.0000, 11400.0000, 82.30, true,
        '2025-11-04', true, NOW());

-- Day 16: 2025-11-05 (Thursday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-05 01:00:00+01', '2025-11-05 07:00:00+01', 2100.0000, 1100.0000, 3300.0000, 93.50, false, '2025-11-05',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-05 07:00:00+01', '2025-11-05 13:00:00+01', 32640.0000, 27840.0000, 37440.0000, 84.90, true,
        '2025-11-05', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-05 13:00:00+01', '2025-11-05 19:00:00+01', 39840.0000, 35040.0000, 44640.0000, 86.70, true,
        '2025-11-05', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-05 19:00:00+01', '2025-11-06 01:00:00+01', 7200.0000, 6000.0000, 10800.0000, 81.40, true,
        '2025-11-05', true, NOW());

-- Day 17: 2025-11-06 (Friday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-06 01:00:00+01', '2025-11-06 07:00:00+01', 2000.0000, 1000.0000, 3200.0000, 92.80, false, '2025-11-06',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-06 07:00:00+01', '2025-11-06 13:00:00+01', 31680.0000, 26880.0000, 36480.0000, 84.10, true,
        '2025-11-06', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-06 13:00:00+01', '2025-11-06 19:00:00+01', 38880.0000, 34080.0000, 43680.0000, 85.90, true,
        '2025-11-06', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-06 19:00:00+01', '2025-11-07 01:00:00+01', 11000.0000, 5000.0000, 10200.0000, 80.60, true,
        '2025-11-06', true, NOW());

-- Day 18: 2025-11-07 (Saturday) - Cloudy day
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-07 01:00:00+01', '2025-11-07 07:00:00+01', 1200.0000, 600.0000, 1800.0000, 91.20, false, '2025-11-07',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-07 07:00:00+01', '2025-11-07 13:00:00+01', 16800.0000, 7200.0000, 21600.0000, 65.30, true,
        '2025-11-07', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-07 13:00:00+01', '2025-11-07 19:00:00+01', 20160.0000, 15360.0000, 24960.0000, 58.40, true,
        '2025-11-07', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-07 19:00:00+01', '2025-11-08 01:00:00+01', 6000.0000, 2000.0000, 10000.0000, 62.70, true,
        '2025-11-07', true, NOW());

-- Day 19: 2025-11-08 (Sunday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-08 01:00:00+01', '2025-11-08 07:00:00+01', 1900.0000, 900.0000, 3100.0000, 92.40, false, '2025-11-08',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-08 07:00:00+01', '2025-11-08 13:00:00+01', 30720.0000, 25920.0000, 35520.0000, 83.50, true,
        '2025-11-08', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-08 13:00:00+01', '2025-11-08 19:00:00+01', 37920.0000, 33120.0000, 42720.0000, 85.20, true,
        '2025-11-08', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-08 19:00:00+01', '2025-11-09 01:00:00+01', 10000.0000, 4000.0000, 9600.0000, 79.80, true,
        '2025-11-08', true, NOW());

-- Day 20: 2025-11-09 (Monday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-09 01:00:00+01', '2025-11-09 07:00:00+01', 1800.0000, 800.0000, 3000.0000, 91.60, false, '2025-11-09',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-09 07:00:00+01', '2025-11-09 13:00:00+01', 29760.0000, 24960.0000, 34560.0000, 82.70, true,
        '2025-11-09', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-09 13:00:00+01', '2025-11-09 19:00:00+01', 36960.0000, 32160.0000, 41760.0000, 84.40, true,
        '2025-11-09', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-09 19:00:00+01', '2025-11-10 01:00:00+01', 9500.0000, 3500.0000, 15500.0000, 79.10, true,
        '2025-11-09', true, NOW());

-- Day 21: 2025-11-10 (Tuesday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-10 01:00:00+01', '2025-11-10 07:00:00+01', 1700.0000, 700.0000, 2900.0000, 90.80, false, '2025-11-10',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-10 07:00:00+01', '2025-11-10 13:00:00+01', 28800.0000, 50000.0000, 33600.0000, 81.90, true,
        '2025-11-10', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-10 13:00:00+01', '2025-11-10 19:00:00+01', 17280.0000, 31200.0000, 40800.0000, 83.60, true,
        '2025-11-10', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-10 19:00:00+01', '2025-11-11 01:00:00+01', 9000.0000, 3000.0000, 9000.0000, 78.30, true,
        '2025-11-10', true, NOW());

-- Day 22: 2025-11-11 (Wednesday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-11 01:00:00+01', '2025-11-11 07:00:00+01', 1600.0000, 600.0000, 2800.0000, 90.10, false, '2025-11-11',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-11 07:00:00+01', '2025-11-11 13:00:00+01', 27840.0000, 48000.0000, 32640.0000, 81.20, true,
        '2025-11-11', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-11 13:00:00+01', '2025-11-11 19:00:00+01', 35040.0000, 30240.0000, 39840.0000, 82.80, true,
        '2025-11-11', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-11 19:00:00+01', '2025-11-12 01:00:00+01', 8500.0000, 2500.0000, 8700.0000, 77.50, true,
        '2025-11-11', true, NOW());

-- Day 23: 2025-11-12 (Thursday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-12 01:00:00+01', '2025-11-12 07:00:00+01', 1500.0000, 500.0000, 2700.0000, 89.30, false, '2025-11-12',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-12 07:00:00+01', '2025-11-12 13:00:00+01', 26880.0000, 22080.0000, 31680.0000, 80.40, true,
        '2025-11-12', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-12 13:00:00+01', '2025-11-12 19:00:00+01', 34080.0000, 29280.0000, 38880.0000, 82.10, true,
        '2025-11-12', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-12 19:00:00+01', '2025-11-13 01:00:00+01', 8000.0000, 2000.0000, 8400.0000, 76.70, true,
        '2025-11-12', true, NOW());

-- Day 24: 2025-11-13 (Friday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-13 01:00:00+01', '2025-11-13 07:00:00+01', 1400.0000, 400.0000, 2600.0000, 88.60, false, '2025-11-13',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-13 07:00:00+01', '2025-11-13 13:00:00+01', 25920.0000, 21120.0000, 30720.0000, 79.80, true,
        '2025-11-13', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-13 13:00:00+01', '2025-11-13 19:00:00+01', 33120.0000, 28320.0000, 37920.0000, 81.30, true,
        '2025-11-13', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-13 19:00:00+01', '2025-11-14 01:00:00+01', 7500.0000, 1500.0000, 13500.0000, 75.90, true,
        '2025-11-13', true, NOW());

-- Day 25: 2025-11-14 (Saturday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-14 01:00:00+01', '2025-11-14 07:00:00+01', 1300.0000, 300.0000, 2500.0000, 87.90, false, '2025-11-14',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-14 07:00:00+01', '2025-11-14 13:00:00+01', 24960.0000, 20160.0000, 29760.0000, 79.10, true,
        '2025-11-14', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-14 13:00:00+01', '2025-11-14 19:00:00+01', 32160.0000, 27360.0000, 36960.0000, 80.50, true,
        '2025-11-14', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-14 19:00:00+01', '2025-11-15 01:00:00+01', 7000.0000, 1000.0000, 7800.0000, 75.20, true,
        '2025-11-14', true, NOW());

-- Day 26: 2025-11-15 (Sunday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-15 01:00:00+01', '2025-11-15 07:00:00+01', 1200.0000, 200.0000, 2400.0000, 87.20, false, '2025-11-15',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-15 07:00:00+01', '2025-11-15 13:00:00+01', 50000.0000, 19200.0000, 28800.0000, 78.40, true,
        '2025-11-15', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-15 13:00:00+01', '2025-11-15 19:00:00+01', 31200.0000, 26400.0000, 17280.0000, 79.70, true,
        '2025-11-15', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-15 19:00:00+01', '2025-11-16 01:00:00+01', 6500.0000, 500.0000, 7500.0000, 74.50, true,
        '2025-11-15', true, NOW());

-- Day 27: 2025-11-16 (Monday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-16 01:00:00+01', '2025-11-16 07:00:00+01', 1100.0000, 100.0000, 2300.0000, 86.50, false, '2025-11-16',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-16 07:00:00+01', '2025-11-16 13:00:00+01', 48000.0000, 18240.0000, 27840.0000, 77.70, true,
        '2025-11-16', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-16 13:00:00+01', '2025-11-16 19:00:00+01', 30240.0000, 25440.0000, 35040.0000, 78.90, true,
        '2025-11-16', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-16 19:00:00+01', '2025-11-17 01:00:00+01', 6000.0000, 0.0000, 7200.0000, 73.80, true,
        '2025-11-16', true, NOW());

-- Day 28: 2025-11-17 (Tuesday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-17 01:00:00+01', '2025-11-17 07:00:00+01', 1000.0000, 0.0000, 2200.0000, 85.80, false, '2025-11-17',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-17 07:00:00+01', '2025-11-17 13:00:00+01', 22080.0000, 17280.0000, 26880.0000, 77.00, true,
        '2025-11-17', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-17 13:00:00+01', '2025-11-17 19:00:00+01', 29280.0000, 24480.0000, 34080.0000, 78.10, true,
        '2025-11-17', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-17 19:00:00+01', '2025-11-18 01:00:00+01', 5500.0000, 0.0000, 11500.0000, 73.10, true,
        '2025-11-17', true, NOW());

-- Day 29: 2025-11-18 (Wednesday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-18 01:00:00+01', '2025-11-18 07:00:00+01', 900.0000, 0.0000, 2100.0000, 85.10, false, '2025-11-18',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-18 07:00:00+01', '2025-11-18 13:00:00+01', 21120.0000, 16320.0000, 25920.0000, 76.30, true,
        '2025-11-18', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-18 13:00:00+01', '2025-11-18 19:00:00+01', 28320.0000, 23520.0000, 33120.0000, 77.30, true,
        '2025-11-18', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-18 19:00:00+01', '2025-11-19 01:00:00+01', 5000.0000, 0.0000, 11000.0000, 72.40, true,
        '2025-11-18', true, NOW());

-- Day 30: 2025-11-19 (Thursday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-19 01:00:00+01', '2025-11-19 07:00:00+01', 800.0000, 0.0000, 2000.0000, 84.40, false, '2025-11-19',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-19 07:00:00+01', '2025-11-19 13:00:00+01', 20160.0000, 15360.0000, 24960.0000, 75.60, true,
        '2025-11-19', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-19 13:00:00+01', '2025-11-19 19:00:00+01', 27360.0000, 22560.0000, 32160.0000, 76.50, true,
        '2025-11-19', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-19 19:00:00+01', '2025-11-20 01:00:00+01', 4500.0000, 0.0000, 10500.0000, 71.70, true,
        '2025-11-19', true, NOW());

-- Day 31: 2025-11-20 (Friday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-20 01:00:00+01', '2025-11-20 07:00:00+01', 700.0000, 0.0000, 1900.0000, 83.70, false, '2025-11-20',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-20 07:00:00+01', '2025-11-20 13:00:00+01', 19200.0000, 14400.0000, 50000.0000, 74.90, true,
        '2025-11-20', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-20 13:00:00+01', '2025-11-20 19:00:00+01', 26400.0000, 21600.0000, 31200.0000, 75.70, true,
        '2025-11-20', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-20 19:00:00+01', '2025-11-21 01:00:00+01', 4000.0000, 0.0000, 10000.0000, 71.00, true,
        '2025-11-20', true, NOW());

-- Day 32: 2025-11-21 (Saturday) - Final day
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-21 01:00:00+01', '2025-11-21 07:00:00+01', 600.0000, 0.0000, 1800.0000, 83.00, false, '2025-11-21',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-21 07:00:00+01', '2025-11-21 13:00:00+01', 18240.0000, 13440.0000, 48000.0000, 74.20, true,
        '2025-11-21', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-21 13:00:00+01', '2025-11-21 19:00:00+01', 25440.0000, 20640.0000, 30240.0000, 74.90, true,
        '2025-11-21', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-21 19:00:00+01', '2025-11-22 01:00:00+01', 3500.0000, 0.0000, 9500.0000, 70.30, true,
        '2025-11-21', true, NOW());

-- UPCOMING WEEK: November 22-28, 2025
-- Day 33: 2025-11-22 (Sunday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-22 01:00:00+01', '2025-11-22 07:00:00+01', 500.0000, 0.0000, 1700.0000, 82.30, false, '2025-11-22',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-22 07:00:00+01', '2025-11-22 13:00:00+01', 17280.0000, 12480.0000, 22080.0000, 73.50, true,
        '2025-11-22', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-22 13:00:00+01', '2025-11-22 19:00:00+01', 24480.0000, 19680.0000, 29280.0000, 74.10, true,
        '2025-11-22', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-22 19:00:00+01', '2025-11-23 01:00:00+01', 3000.0000, 0.0000, 9000.0000, 69.60, true,
        '2025-11-22', true, NOW());

-- Day 34: 2025-11-23 (Monday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-23 01:00:00+01', '2025-11-23 07:00:00+01', 400.0000, 0.0000, 1600.0000, 81.60, false, '2025-11-23',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-23 07:00:00+01', '2025-11-23 13:00:00+01', 16320.0000, 11520.0000, 21120.0000, 72.80, true,
        '2025-11-23', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-23 13:00:00+01', '2025-11-23 19:00:00+01', 23520.0000, 18720.0000, 28320.0000, 73.30, true,
        '2025-11-23', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-23 19:00:00+01', '2025-11-24 01:00:00+01', 2500.0000, 0.0000, 8500.0000, 68.90, true,
        '2025-11-23', true, NOW());

-- Day 35: 2025-11-24 (Tuesday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-24 01:00:00+01', '2025-11-24 07:00:00+01', 300.0000, 0.0000, 1500.0000, 80.90, false, '2025-11-24',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-24 07:00:00+01', '2025-11-24 13:00:00+01', 15360.0000, 10560.0000, 20160.0000, 72.10, true,
        '2025-11-24', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-24 13:00:00+01', '2025-11-24 19:00:00+01', 22560.0000, 37000.0000, 27360.0000, 72.50, true,
        '2025-11-24', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-24 19:00:00+01', '2025-11-25 01:00:00+01', 2000.0000, 0.0000, 8000.0000, 68.20, true,
        '2025-11-24', true, NOW());

-- Day 36: 2025-11-25 (Wednesday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-25 01:00:00+01', '2025-11-25 07:00:00+01', 200.0000, 0.0000, 1400.0000, 80.20, false, '2025-11-25',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-25 07:00:00+01', '2025-11-25 13:00:00+01', 14400.0000, 9600.0000, 19200.0000, 71.40, true,
        '2025-11-25', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-25 13:00:00+01', '2025-11-25 19:00:00+01', 21600.0000, 16800.0000, 26400.0000, 71.70, true,
        '2025-11-25', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-25 19:00:00+01', '2025-11-26 01:00:00+01', 1500.0000, 0.0000, 7500.0000, 67.50, true,
        '2025-11-25', true, NOW());

-- Day 37: 2025-11-26 (Thursday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-26 01:00:00+01', '2025-11-26 07:00:00+01', 100.0000, 0.0000, 1300.0000, 79.50, false, '2025-11-26',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-26 07:00:00+01', '2025-11-26 13:00:00+01', 13440.0000, 10800.0000, 18240.0000, 70.70, true,
        '2025-11-26', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-26 13:00:00+01', '2025-11-26 19:00:00+01', 20640.0000, 33000.0000, 25440.0000, 70.90, true,
        '2025-11-26', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-26 19:00:00+01', '2025-11-27 01:00:00+01', 1000.0000, 0.0000, 7000.0000, 66.80, true,
        '2025-11-26', true, NOW());

-- Day 38: 2025-11-27 (Friday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-27 01:00:00+01', '2025-11-27 07:00:00+01', 0.0000, 0.0000, 1200.0000, 78.80, false, '2025-11-27',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-27 07:00:00+01', '2025-11-27 13:00:00+01', 12480.0000, 9600.0000, 17280.0000, 70.00, true,
        '2025-11-27', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-27 13:00:00+01', '2025-11-27 19:00:00+01', 19680.0000, 14880.0000, 24480.0000, 70.10, true,
        '2025-11-27', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-27 19:00:00+01', '2025-11-28 01:00:00+01', 500.0000, 0.0000, 6500.0000, 66.10, true,
        '2025-11-27', true, NOW());

-- Day 39: 2025-11-28 (Saturday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-28 01:00:00+01', '2025-11-28 07:00:00+01', 0.0000, 0.0000, 1100.0000, 78.10, false, '2025-11-28',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-28 07:00:00+01', '2025-11-28 13:00:00+01', 11520.0000, 8400.0000, 16320.0000, 69.30, true,
        '2025-11-28', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-28 13:00:00+01', '2025-11-28 19:00:00+01', 18720.0000, 13920.0000, 23520.0000, 69.30, true,
        '2025-11-28', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-11-28 19:00:00+01', '2025-11-29 01:00:00+01', 0.0000, 0.0000, 6000.0000, 65.40, true,
        '2025-11-28', true, NOW());

-- ============================================================================
-- APP DEFINITIONS TABLE
-- Stores reusable Kubernetes application definitions (catalog)
-- ============================================================================

CREATE TABLE IF NOT EXISTS app_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    namespace VARCHAR(255) NOT NULL DEFAULT 'default',
    description TEXT,
    manifest TEXT NOT NULL,
    workload_type VARCHAR(20) NOT NULL DEFAULT 'Optional',
    estimated_energy_required DOUBLE PRECISION,
    CONSTRAINT chk_app_workload_type CHECK (workload_type IN ('Critical', 'Preferred', 'Optional'))
);

-- ============================================================================
-- APP DEPLOYMENT REQUESTS TABLE
-- For energy-aware Kubernetes application deployment request management
-- ============================================================================

CREATE TABLE IF NOT EXISTS app_deployments_request (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_definition_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    estimated_energy_watts DECIMAL(10, 4),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deployed_at TIMESTAMP WITH TIME ZONE,
    schedule_at TIMESTAMP WITH TIME ZONE,

    -- Foreign key constraint
    CONSTRAINT fk_deployment_app FOREIGN KEY (app_definition_id)
        REFERENCES app_definitions(id) ON DELETE CASCADE
);