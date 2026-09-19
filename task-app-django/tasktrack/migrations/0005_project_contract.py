from django.db import migrations, models
import django.db.models.deletion
import uuid


def assign_existing_projects(apps, schema_editor):
    ContractModel = apps.get_model("tasktrack", "ContractModel")
    ProjectModel = apps.get_model("tasktrack", "ProjectModel")
    UserModel = apps.get_model("tasktrack", "UserModel")

    if not ProjectModel.objects.filter(contract__isnull=True).exists():
        return

    contract = ContractModel.objects.order_by("created_at").first()
    if contract is None:
        owner = UserModel.objects.order_by("created_at").first()
        if owner is None:
            raise RuntimeError(
                "Não é possível associar projetos existentes a um contrato porque não há usuários cadastrados."
            )
        contract = ContractModel.objects.create(
            id=uuid.uuid4(),
            title="Contrato de migração dos projetos existentes",
            description="Contrato criado automaticamente para preservar projetos existentes.",
            owner_id=owner.id,
        )
    ProjectModel.objects.filter(contract__isnull=True).update(contract_id=contract.id)


class Migration(migrations.Migration):
    dependencies = [
        ("tasktrack", "0004_projectmembershipmodel"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectmodel",
            name="contract",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="projects",
                to="tasktrack.contractmodel",
            ),
        ),
        migrations.RunPython(assign_existing_projects, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="projectmodel",
            name="contract",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="projects",
                to="tasktrack.contractmodel",
            ),
        ),
    ]
