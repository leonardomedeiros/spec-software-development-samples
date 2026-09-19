from django.db import migrations, models


def ensure_contract_status(apps, schema_editor):
    connection = schema_editor.connection
    table_name = "contracts"
    column_names = {
        column.name
        for column in connection.introspection.get_table_description(
            connection.cursor(), table_name
        )
    }
    if "status" not in column_names:
        schema_editor.add_field(
            apps.get_model("tasktrack", "ContractModel"),
            models.CharField(
                name="status",
                max_length=20,
                default="PROSPECTING",
                choices=[
                    ("PROSPECTING", "PROSPECTING"),
                    ("IN_PROGRESS", "IN_PROGRESS"),
                    ("SIGNED", "SIGNED"),
                ],
            ),
        )


class Migration(migrations.Migration):
    dependencies = [
        ("tasktrack", "0002_contractmodel"),
    ]

    operations = [
        migrations.RunPython(
            ensure_contract_status,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
