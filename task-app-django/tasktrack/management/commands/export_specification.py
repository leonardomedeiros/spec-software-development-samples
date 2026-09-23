from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from tasktrack.infra.repositories import DjangoRequirementRepository, DjangoTaskRepository
from tasktrack.use_cases.specification_export import export_requirements_section


class Command(BaseCommand):
    help = "Regenera a seção de Requisitos Rastreáveis do SPECIFICATION.md a partir dos dados atuais."

    def handle(self, *args, **options):
        spec_path = settings.BASE_DIR / "SPECIFICATION.md"
        try:
            export_requirements_section(
                DjangoRequirementRepository(),
                DjangoTaskRepository(),
                spec_path,
            )
        except (ValueError, OSError) as e:
            raise CommandError(str(e))

        self.stdout.write(self.style.SUCCESS(f"SPECIFICATION.md atualizado com sucesso ({spec_path})."))
