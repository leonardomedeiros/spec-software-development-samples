from django.contrib.auth.models import User as DjangoUser
from django.core.management.base import BaseCommand, CommandError
from uuid import uuid4

from tasktrack.domain.entities import User
from tasktrack.domain.enums import UserRole
from tasktrack.infra.repositories import DjangoUserRepository


class Command(BaseCommand):
    help = "Cria um usuário de autenticação e seu perfil TaskTrack."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument(
            "--role",
            default="MEMBER",
            choices=[role.value for role in UserRole],
        )

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        if DjangoUser.objects.filter(username=email).exists():
            raise CommandError("Já existe um usuário Django com esse e-mail.")

        auth_user = DjangoUser.objects.create_user(
            username=email,
            email=email,
            first_name=options["name"].strip(),
            password=options["password"],
        )
        try:
            DjangoUserRepository().save(
                User(
                    id=uuid4(),
                    name=options["name"].strip(),
                    email=email,
                    role=UserRole(options["role"]),
                )
            )
        except Exception:
            auth_user.delete()
            raise

        self.stdout.write(self.style.SUCCESS(f"Usuário {email} criado com a função {options['role']}"))
