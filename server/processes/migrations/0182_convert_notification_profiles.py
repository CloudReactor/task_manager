# Generated by Django 4.2.14 on 2024-09-03 06:12

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0181_emailnotificationdeliverymethod_and_more"),
    ]

    operations = [
        migrations.RunSQL(sql="""
INSERT INTO processes_notificationdeliverymethod (
    uuid, name, description, created_at, updated_at, type,
    created_by_group_id, created_by_user_id, run_environment_id,
    email_bcc_addresses, email_cc_addresses, email_to_addresses)
SELECT uuid, name, description, created_at, updated_at,
    'processes.emailnotificationdeliverymethod',
    created_by_group_id, created_by_user_id, run_environment_id,
    bcc_addresses, cc_addresses, to_addresses
FROM processes_emailnotificationprofile
ON CONFLICT DO NOTHING
""",
                reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql="""
INSERT INTO processes_notificationdeliverymethod (
    uuid, name, description, created_at, updated_at, type,
    created_by_group_id, created_by_user_id, run_environment_id,
    pagerduty_api_key, pagerduty_event_class_template,
    pagerduty_event_component_template, pagerduty_event_group_template)
SELECT uuid, name, description, created_at, updated_at,
    'processes.pagerdutynotificationdeliverymethod',
    created_by_group_id, created_by_user_id, run_environment_id,
    integration_key, default_event_component_template,
    default_event_group_template, default_event_class_template
FROM processes_pagerdutyprofile
ON CONFLICT DO NOTHING
""",
                reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql="""
INSERT INTO processes_notificationprofile (
    uuid, name, description, created_at, updated_at, enabled,
    created_by_group_id, created_by_user_id, run_environment_id)
SELECT uuid, name, description, created_at, updated_at, enabled,
    created_by_group_id, created_by_user_id, run_environment_id
FROM processes_alertmethod
ON CONFLICT DO NOTHING
""",
                reverse_sql=migrations.RunSQL.noop),
    ]
