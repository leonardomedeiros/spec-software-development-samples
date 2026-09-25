from django.db import migrations


def backfill_actor_contract(apps, schema_editor):
    ActorModel = apps.get_model("tasktrack", "ActorModel")
    ContractModel = apps.get_model("tasktrack", "ContractModel")

    orphan_actors = ActorModel.objects.filter(contract__isnull=True)
    if not orphan_actors.exists():
        return

    default_contract = ContractModel.objects.order_by("created_at").first()
    if default_contract is None:
        raise RuntimeError(
            "Existem atores sem contrato vinculado, mas nenhum contrato foi encontrado para "
            "realizar o backfill automaticamente. Crie um contrato e vincule os atores manualmente."
        )
    orphan_actors.update(contract_id=default_contract.id)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tasktrack", "0013_add_requirement_project_actor_contract"),
    ]

    operations = [
        migrations.RunPython(backfill_actor_contract, noop_reverse),
    ]
