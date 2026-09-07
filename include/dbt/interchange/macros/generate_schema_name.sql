{#
    Use the schema configured on the model as-is (e.g. `staging`, `marts`)
    instead of dbt's default `<target_schema>_<custom_schema>` concatenation.
    Falls back to the profile's target schema when a model sets none.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
