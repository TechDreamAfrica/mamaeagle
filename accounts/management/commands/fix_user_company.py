"""
Management command to associate users with companies
Usage: python manage.py fix_user_company
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Company, UserCompany
from datetime import date

User = get_user_model()


class Command(BaseCommand):
    help = 'Associate users with companies if they don\'t have one'

    def handle(self, *args, **options):
        self.stdout.write('Checking users without company associations...')

        # Get all users without a company
        users_without_company = []
        for user in User.objects.all():
            if not UserCompany.objects.filter(user=user, is_active=True).exists():
                users_without_company.append(user)

        if not users_without_company:
            self.stdout.write(self.style.SUCCESS('All users have company associations!'))
            return

        self.stdout.write(f'Found {len(users_without_company)} users without company associations')

        # Check if there are existing companies
        companies = Company.objects.all()
        if not companies.exists():
            self.stdout.write('No companies found. Creating a default company...')
            company = Company.objects.create(
                name='Default Company',
                email='admin@company.com',
                fiscal_year_start=date(2024, 1, 1),
            )
            self.stdout.write(self.style.SUCCESS(f'Created default company: {company.name}'))
        else:
            company = companies.first()
            self.stdout.write(f'Using existing company: {company.name}')

        # Associate users with the company
        for user in users_without_company:
            UserCompany.objects.create(
                user=user,
                company=company,
                role='admin' if user.is_superuser else user.role,
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS(f'Associated {user.username} with {company.name}'))

        self.stdout.write(self.style.SUCCESS(
            f'Successfully associated {len(users_without_company)} users with companies!'
        ))
