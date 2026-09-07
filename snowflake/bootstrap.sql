-- snowflake/bootstrap.sql
-- Run once, as ACCOUNTADMIN, in a Snowsight worksheet.
-- Creates the warehouses, databases, role, service user, and landing stage
-- for the interchange-revenue-pipeline project.
--
-- Before running: replace REPLACE_WITH_A_STRONG_PASSWORD in the worksheet
-- (not in this file) with a password you choose.

use role accountadmin;

-- ---------------------------------------------------------------------------
-- Warehouses (XS, aggressive auto-suspend to protect trial credits)
-- ---------------------------------------------------------------------------
create warehouse if not exists ingest_wh
    with warehouse_size = xsmall auto_suspend = 60 auto_resume = true
    initially_suspended = true comment = 'Raw ingestion / COPY INTO';

create warehouse if not exists transform_wh
    with warehouse_size = xsmall auto_suspend = 60 auto_resume = true
    initially_suspended = true comment = 'dbt runs';

create warehouse if not exists ci_wh
    with warehouse_size = xsmall auto_suspend = 60 auto_resume = true
    initially_suspended = true comment = 'CI builds (GitHub Actions)';

-- ---------------------------------------------------------------------------
-- Databases and the raw landing schema (dbt creates analytics schemas itself)
-- ---------------------------------------------------------------------------
create database if not exists interchange_raw
    comment = 'Landing zone for simulated source data';
create schema if not exists interchange_raw.sim
    comment = 'Simulator output tables';

create database if not exists interchange_analytics
    comment = 'dbt-managed models (staging / intermediate / marts)';

-- ---------------------------------------------------------------------------
-- Role. One functional role for local dev; split into LOADER/TRANSFORMER/CI
-- in the Phase 8 hardening pass.
-- ---------------------------------------------------------------------------
create role if not exists interchange_role;
grant role interchange_role to role sysadmin;

grant usage on warehouse ingest_wh    to role interchange_role;
grant usage on warehouse transform_wh to role interchange_role;
grant usage on warehouse ci_wh        to role interchange_role;

grant all on database interchange_raw               to role interchange_role;
grant all on schema   interchange_raw.sim           to role interchange_role;
grant all on all    tables in schema interchange_raw.sim to role interchange_role;
grant all on future tables in schema interchange_raw.sim to role interchange_role;
grant all on all    stages in schema interchange_raw.sim to role interchange_role;
grant all on future stages in schema interchange_raw.sim to role interchange_role;

grant all on database interchange_analytics                     to role interchange_role;
grant usage on future schemas in database interchange_analytics to role interchange_role;
grant all   on future schemas in database interchange_analytics to role interchange_role;
grant all   on future tables  in database interchange_analytics to role interchange_role;

-- ---------------------------------------------------------------------------
-- File formats + internal stage the simulator PUTs files into
-- ---------------------------------------------------------------------------
create file format if not exists interchange_raw.sim.ff_parquet
    type = parquet;

create file format if not exists interchange_raw.sim.ff_csv
    type = csv field_optionally_enclosed_by = '"' skip_header = 1
    null_if = ('', 'NULL') empty_field_as_null = true;

create stage if not exists interchange_raw.sim.landing
    file_format = interchange_raw.sim.ff_parquet
    comment = 'Internal stage for simulator output files';

-- ---------------------------------------------------------------------------
-- Service user for dbt + Airflow (local dev)
-- ---------------------------------------------------------------------------
create user if not exists svc_interchange
    password = 'REPLACE_WITH_A_STRONG_PASSWORD'
    default_role = interchange_role
    default_warehouse = transform_wh
    default_namespace = interchange_analytics
    must_change_password = false
    comment = 'Local dev service account (dbt + Airflow)';

grant role interchange_role to user svc_interchange;

-- ---------------------------------------------------------------------------
-- Sanity checks
-- ---------------------------------------------------------------------------
show warehouses like '%_wh';
show databases like 'interchange_%';
select current_organization_name() as org_name,
       current_account_name()      as account_name;
