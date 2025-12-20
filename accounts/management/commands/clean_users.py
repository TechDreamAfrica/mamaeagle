"""
Management command to clean all non-superuser accounts from the database
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from accounts.models import Company, UserCompany
from reports.models import JournalEntry, JournalEntryLine, Account

User = get_user_model()


class Command(BaseCommand):
    help = 'Remove all non-superuser accounts and their related data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Remove ALL users including superusers (use with caution!)',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm the deletion without prompting',
        )

    def handle(self, *args, **options):
        delete_all = options['all']
        auto_confirm = options['confirm']
        
        # Get users to delete
        if delete_all:
            users_to_delete = User.objects.all()
            warning_msg = "ALL USERS INCLUDING SUPERUSERS"
        else:
            users_to_delete = User.objects.filter(is_superuser=False)
            warning_msg = "ALL NON-SUPERUSER ACCOUNTS"
        
        user_count = users_to_delete.count()
        
        if user_count == 0:
            self.stdout.write(self.style.SUCCESS('No users to delete.'))
            return
        
        # Show warning
        self.stdout.write(self.style.WARNING('\n' + '='*70))
        self.stdout.write(self.style.WARNING(f'WARNING: This will delete {warning_msg}'))
        self.stdout.write(self.style.WARNING('='*70))
        self.stdout.write(f'\nUsers to be deleted: {user_count}')
        
        # List users
        self.stdout.write('\nUsers:')
        for user in users_to_delete[:10]:  # Show first 10
            user_type = 'SUPERUSER' if user.is_superuser else 'Regular'
            self.stdout.write(f'  - {user.username} ({user.email}) [{user_type}]')
        
        if user_count > 10:
            self.stdout.write(f'  ... and {user_count - 10} more')
        
        # Related data info
        companies_count = Company.objects.filter(
            created_by__in=users_to_delete
        ).count()
        accounts_count = Account.objects.filter(
            user__in=users_to_delete
        ).count()
        journal_entries_count = JournalEntry.objects.filter(
            user__in=users_to_delete
        ).count()
        
        self.stdout.write(f'\nRelated data that will be affected:')
        self.stdout.write(f'  - Companies: {companies_count}')
        self.stdout.write(f'  - Accounts: {accounts_count}')
        self.stdout.write(f'  - Journal Entries: {journal_entries_count}')
        
        # Confirm deletion
        if not auto_confirm:
            self.stdout.write(self.style.WARNING(
                '\nThis action cannot be undone!'
            ))
            confirm = input('\nType "DELETE" to confirm: ')
            
            if confirm != 'DELETE':
                self.stdout.write(self.style.ERROR('\nCancelled. No users were deleted.'))
                return
        
        # Perform deletion
        self.stdout.write('\nDeleting related data...')
        
        deleted_summary = {}
        
        try:
            with transaction.atomic():
                # Delete journal entry lines first (they reference accounts)
                journal_lines_deleted = JournalEntryLine.objects.filter(
                    journal_entry__user__in=users_to_delete
                ).delete()
                if journal_lines_deleted[0] > 0:
                    deleted_summary['JournalEntryLine'] = journal_lines_deleted[0]
                    self.stdout.write(f'  - Deleted {journal_lines_deleted[0]} journal entry lines')
                
                # Delete journal entries
                journal_entries_deleted = JournalEntry.objects.filter(
                    user__in=users_to_delete
                ).delete()
                if journal_entries_deleted[0] > 0:
                    deleted_summary['JournalEntry'] = journal_entries_deleted[0]
                    self.stdout.write(f'  - Deleted {journal_entries_deleted[0]} journal entries')
                
                # Delete accounts
                accounts_deleted = Account.objects.filter(
                    user__in=users_to_delete
                ).delete()
                if accounts_deleted[0] > 0:
                    deleted_summary['Account'] = accounts_deleted[0]
                    self.stdout.write(f'  - Deleted {accounts_deleted[0]} accounts')
                
                # Now delete users (Django CASCADE will handle the rest)
                self.stdout.write('\nDeleting users...')
                deleted_count, deleted_objects = users_to_delete.delete()
                
                # Merge deletion results
                for obj_type, count in deleted_objects.items():
                    if obj_type not in deleted_summary:
                        deleted_summary[obj_type] = count
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nError during deletion: {str(e)}'))
            return
        
        # Show results
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('DELETION COMPLETED'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(f'\nTotal users deleted: {user_count}')
        
        if deleted_summary:
            self.stdout.write('\nDeleted objects by type:')
            for obj_type, count in deleted_summary.items():
                self.stdout.write(f'  - {obj_type}: {count}')
        
        self.stdout.write(self.style.SUCCESS('\nDatabase cleanup completed successfully!'))
