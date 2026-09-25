import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasktrack", "0014_backfill_actor_contract"),
    ]

    operations = [
        migrations.AlterField(
            model_name="requirementmodel",
            name="project",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="requirements",
                to="tasktrack.projectmodel",
            ),
        ),
        migrations.AlterField(
            model_name="actormodel",
            name="contract",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="actors",
                to="tasktrack.contractmodel",
            ),
        ),
    ]
