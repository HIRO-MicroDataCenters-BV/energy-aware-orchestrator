CREATE TABLE container_power_metrics
(
    timestamp                     TIMESTAMP NOT NULL,
    container_name                VARCHAR(255),
    pod_name                      VARCHAR(255),
    namespace                     VARCHAR(255),
    node_name                     VARCHAR(255),
    metric_source                 VARCHAR(255),

    -- Power metrics (from Kepler) sum of all this is the total power consumption in watts
    cpu_core_watts                DOUBLE PRECISION,
    cpu_package_watts             DOUBLE PRECISION,
    memory_power_watts            DOUBLE PRECISION,
    platform_watts                DOUBLE PRECISION,
    other_watts                   DOUBLE PRECISION,

    -- Resource utilization (from cAdvisor)
    cpu_utilization_percent       DOUBLE PRECISION,
    memory_utilization_percent    DOUBLE PRECISION,
    memory_usage_bytes            BIGINT,
    network_io_rate_bytes_per_sec DOUBLE PRECISION,
    disk_io_rate_bytes_per_sec    DOUBLE PRECISION,

    PRIMARY KEY (timestamp, container_name, pod_name)
);

##
This table stores power metrics for containers, including CPU and memory power consumption in joules.


CREATE TABLE node_power_metrics
(
    timestamp                     TIMESTAMP NOT NULL,
    node_name                     VARCHAR(255),
    metric_source                 VARCHAR(255),

    -- Power metrics (from Kepler) sum of all this is the total power consumption in watts
    cpu_core_watts                DOUBLE PRECISION,
    cpu_package_watts             DOUBLE PRECISION,
    memory_power_watts            DOUBLE PRECISION,
    platform_watts                DOUBLE PRECISION,

    -- Resource utilization (from cAdvisor)
    cpu_utilization_percent       DOUBLE PRECISION,
    memory_utilization_percent    DOUBLE PRECISION,
    memory_usage_bytes            BIGINT,
    PRIMARY KEY (timestamp, node_name)
);



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