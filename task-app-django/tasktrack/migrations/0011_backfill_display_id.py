from django.db import migrations


def backfill_display_ids(apps, schema_editor):
    IdentifierSequenceModel = apps.get_model("tasktrack", "IdentifierSequenceModel")
    model_prefixes = [
        (apps.get_model("tasktrack", "ContractModel"), "CRT"),
        (apps.get_model("tasktrack", "ProjectModel"), "PRJ"),
        (apps.get_model("tasktrack", "TaskModel"), "TSK"),
        (apps.get_model("tasktrack", "RequirementModel"), "REQ"),
    ]
    for Model, prefix in model_prefixes:
        value = 0
        for obj in Model.objects.order_by("created_at"):
            value += 1
            obj.display_id = f"{prefix}{value}"
            obj.save(update_fields=["display_id"])
        IdentifierSequenceModel.objects.update_or_create(
            prefix=prefix, defaults={"last_value": value}
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tasktrack", "0010_add_display_id"),
    ]

    operations = [
        migrations.RunPython(backfill_display_ids, noop_reverse),
    ]
