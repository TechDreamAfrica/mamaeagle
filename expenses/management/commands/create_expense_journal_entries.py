from django.core.management.base import BaseCommand
from expenses.models import Expense
from expenses.signals import create_journal_entry_for_expense


class Command(BaseCommand):
    help = 'Create journal entries for existing approved/paid expenses'

    def handle(self, *args, **options):
        # Get all approved or paid expenses
        expenses = Expense.objects.filter(status__in=['approved', 'paid'])
        
        self.stdout.write(f'Found {expenses.count()} approved/paid expenses')
        
        created_count = 0
        for expense in expenses:
            # Trigger the signal manually
            create_journal_entry_for_expense(
                sender=Expense,
                instance=expense,
                created=False
            )
            created_count += 1
            self.stdout.write(f'  ✓ Created journal entry for: {expense.description}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} journal entries')
        )
