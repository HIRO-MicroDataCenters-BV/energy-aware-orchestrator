-- Energy forecast inserts for EuroSolar Netherlands for the next 7 days
-- 6 time slots per day (4-hour intervals): 00:00-04:00, 04:00-08:00, 08:00-12:00, 12:00-16:00, 16:00-20:00, 20:00-24:00


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

-- Day 1: 2025-08-21 (Wednesday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-21 00:00:00+00', '2025-08-21 04:00:00+00', 500.0000, 200.0000, 800.0000, 95.50, false, '2025-08-21',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-21 04:00:00+00', '2025-08-21 08:00:00+00', 12000.0000, 8000.0000, 18000.0000, 85.20, true,
        '2025-08-21', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-21 08:00:00+00', '2025-08-21 12:00:00+00', 65000.0000, 58000.0000, 75000.0000, 92.30, true,
        '2025-08-21', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-21 12:00:00+00', '2025-08-21 16:00:00+00', 85000.0000, 78000.0000, 95000.0000, 88.75, true,
        '2025-08-21', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-21 16:00:00+00', '2025-08-21 20:00:00+00', 45000.0000, 38000.0000, 55000.0000, 87.40, true,
        '2025-08-21', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-21 20:00:00+00', '2025-08-22 00:00:00+00', 500.0000, 200.0000, 800.0000, 98.10, false, '2025-08-21',
        true, NOW());

-- Day 2: 2025-08-22 (Thursday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-22 00:00:00+00', '2025-08-22 04:00:00+00', 500.0000, 200.0000, 800.0000, 96.20, false, '2025-08-22',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-22 04:00:00+00', '2025-08-22 08:00:00+00', 14000.0000, 9000.0000, 20000.0000, 82.15, true,
        '2025-08-22', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-22 08:00:00+00', '2025-08-22 12:00:00+00', 58000.0000, 48000.0000, 68000.0000, 75.60, true,
        '2025-08-22', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-22 12:00:00+00', '2025-08-22 16:00:00+00', 72000.0000, 62000.0000, 85000.0000, 68.30, true,
        '2025-08-22', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-22 16:00:00+00', '2025-08-22 20:00:00+00', 32000.0000, 25000.0000, 42000.0000, 71.80, true,
        '2025-08-22', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-22 20:00:00+00', '2025-08-23 00:00:00+00', 500.0000, 200.0000, 800.0000, 97.50, false, '2025-08-22',
        true, NOW());

-- Day 3: 2025-08-23 (Friday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-23 00:00:00+00', '2025-08-23 04:00:00+00', 500.0000, 200.0000, 800.0000, 95.80, false, '2025-08-23',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-23 04:00:00+00', '2025-08-23 08:00:00+00', 13000.0000, 8500.0000, 17000.0000, 88.90, true,
        '2025-08-23', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-23 08:00:00+00', '2025-08-23 12:00:00+00', 68000.0000, 62000.0000, 78000.0000, 93.40, true,
        '2025-08-23', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-23 12:00:00+00', '2025-08-23 16:00:00+00', 88000.0000, 82000.0000, 98000.0000, 91.20, true,
        '2025-08-23', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-23 16:00:00+00', '2025-08-23 20:00:00+00', 48000.0000, 42000.0000, 58000.0000, 89.60, true,
        '2025-08-23', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-23 20:00:00+00', '2025-08-24 00:00:00+00', 500.0000, 200.0000, 800.0000, 96.70, false, '2025-08-23',
        true, NOW());

-- Day 4: 2025-08-24 (Saturday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-24 00:00:00+00', '2025-08-24 04:00:00+00', 500.0000, 200.0000, 800.0000, 97.30, false, '2025-08-24',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-24 04:00:00+00', '2025-08-24 08:00:00+00', 11000.0000, 7000.0000, 16000.0000, 84.50, true,
        '2025-08-24', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-24 08:00:00+00', '2025-08-24 12:00:00+00', 62000.0000, 52000.0000, 72000.0000, 86.80, true,
        '2025-08-24', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-24 12:00:00+00', '2025-08-24 16:00:00+00', 82000.0000, 75000.0000, 92000.0000, 83.90, true,
        '2025-08-24', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-24 16:00:00+00', '2025-08-24 20:00:00+00', 42000.0000, 35000.0000, 52000.0000, 81.20, true,
        '2025-08-24', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-24 20:00:00+00', '2025-08-25 00:00:00+00', 500.0000, 200.0000, 800.0000, 98.40, false, '2025-08-24',
        true, NOW());

-- Day 5: 2025-08-25 (Sunday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-25 00:00:00+00', '2025-08-25 04:00:00+00', 500.0000, 200.0000, 800.0000, 96.90, false, '2025-08-25',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-25 04:00:00+00', '2025-08-25 08:00:00+00', 13500.0000, 9500.0000, 18000.0000, 89.10, true,
        '2025-08-25', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-25 08:00:00+00', '2025-08-25 12:00:00+00', 66000.0000, 58000.0000, 78000.0000, 94.20, true,
        '2025-08-25', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-25 12:00:00+00', '2025-08-25 16:00:00+00', 92000.0000, 85000.0000, 105000.0000, 92.80, true,
        '2025-08-25', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-25 16:00:00+00', '2025-08-25 20:00:00+00', 52000.0000, 45000.0000, 62000.0000, 90.50, true,
        '2025-08-25', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-25 20:00:00+00', '2025-08-26 00:00:00+00', 500.0000, 200.0000, 800.0000, 97.80, false, '2025-08-25',
        true, NOW());

-- Day 6: 2025-08-26 (Monday) - Cloudy weather expected
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-26 00:00:00+00', '2025-08-26 04:00:00+00', 500.0000, 200.0000, 800.0000, 98.20, false, '2025-08-26',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-26 04:00:00+00', '2025-08-26 08:00:00+00', 6000.0000, 3000.0000, 10000.0000, 65.40, true,
        '2025-08-26', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-26 08:00:00+00', '2025-08-26 12:00:00+00', 28000.0000, 18000.0000, 42000.0000, 58.70, true,
        '2025-08-26', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-26 12:00:00+00', '2025-08-26 16:00:00+00', 35000.0000, 22000.0000, 55000.0000, 55.20, true,
        '2025-08-26', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-26 16:00:00+00', '2025-08-26 20:00:00+00', 18000.0000, 10000.0000, 28000.0000, 62.80, true,
        '2025-08-26', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-26 20:00:00+00', '2025-08-27 00:00:00+00', 500.0000, 200.0000, 800.0000, 96.50, false, '2025-08-26',
        true, NOW());

-- Day 7: 2025-08-27 (Tuesday)
INSERT INTO energy_availability
VALUES (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-27 00:00:00+00', '2025-08-27 04:00:00+00', 500.0000, 200.0000, 800.0000, 97.60, false, '2025-08-27',
        true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-27 04:00:00+00', '2025-08-27 08:00:00+00', 12500.0000, 8000.0000, 17000.0000, 87.30, true,
        '2025-08-27', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-27 08:00:00+00', '2025-08-27 12:00:00+00', 64000.0000, 56000.0000, 75000.0000, 91.50, true,
        '2025-08-27', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-27 12:00:00+00', '2025-08-27 16:00:00+00', 84000.0000, 78000.0000, 96000.0000, 89.40, true,
        '2025-08-27', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-27 16:00:00+00', '2025-08-27 20:00:00+00', 44000.0000, 38000.0000, 54000.0000, 86.70, true,
        '2025-08-27', true, NOW()),
       (DEFAULT, 'EuroSolar Netherlands', 'Flevoland Province, Netherlands', 'Solar',
        '2025-08-27 20:00:00+00', '2025-08-28 00:00:00+00', 500.0000, 200.0000, 800.0000, 98.90, false, '2025-08-27',
        true, NOW());