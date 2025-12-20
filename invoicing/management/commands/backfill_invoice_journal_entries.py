from django.core.management.base import BaseCommand
from django.db import transaction
from invoicing.models import Payment
from invoicing.signals import create_journal_entry_for_payment
from reports.models import JournalEntry


class Command(BaseCommand):
    help = 'Backfill journal entries for existing invoice payments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making any changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get all payments that don't have journal entries
        all_payments = Payment.objects.select_related('invoice', 'invoice__user').all()
        
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        for payment in all_payments:
            # Check if journal entry already exists
            existing_entry = JournalEntry.objects.filter(
                user=payment.invoice.user,
                reference_type='payment',
                reference_id=payment.id
            ).first()
            
            if existing_entry:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Skipped: Journal entry already exists for payment {payment.id} (Invoice {payment.invoice.invoice_number})'
                    )
                )
                continue
            
            if not dry_run:
                try:
                    with transaction.atomic():
                        # Manually call the signal handler to create the journal entry
                        from invoicing.signals import get_or_create_revenue_account, get_or_create_cash_account
                        from reports.models import JournalEntryLine
                        from decimal import Decimal
                        
                        # Get or create revenue account
                        revenue_account = get_or_create_revenue_account(payment.invoice.user)
                        
                        # Get or create cash/bank account based on payment method
                        cash_account = get_or_create_cash_account(payment.invoice.user, payment.payment_method)
                        
                        if not revenue_account or not cash_account:
                            error_count += 1
                            self.stdout.write(
                                self.style.ERROR(
                                    f'Error: Could not create accounts for payment {payment.id} (Invoice {payment.invoice.invoice_number})'
                                )
                            )
                            continue
                        
                        # Create journal entry
                        journal_entry = JournalEntry.objects.create(
                            user=payment.invoice.user,
                            entry_date=payment.payment_date,
                            reference_type='payment',
                            reference_id=payment.id,
                            invoice=payment.invoice,
                            description=f"Payment received for Invoice {payment.invoice.invoice_number}",
                            status='posted'
                        )
                        
                        # Debit cash/bank account (increases asset)
                        JournalEntryLine.objects.create(
                            journal_entry=journal_entry,
                            account=cash_account,
                            debit=payment.amount,
                            credit=Decimal('0'),
                            description=f"Payment for Invoice {payment.invoice.invoice_number}"
                        )
                        
                        # Credit revenue account (increases revenue)
                        JournalEntryLine.objects.create(
                            journal_entry=journal_entry,
                            account=revenue_account,
                            debit=Decimal('0'),
                            credit=payment.amount,
                            description=f"Revenue from Invoice {payment.invoice.invoice_number}"
                        )
                        
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Created: Journal entry for payment {payment.id} (Invoice {payment.invoice.invoice_number}) - Amount: {payment.amount}'
                            )
                        )
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error creating journal entry for payment {payment.id} (Invoice {payment.invoice.invoice_number}): {str(e)}'
                        )
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Would create: Journal entry for payment {payment.id} (Invoice {payment.invoice.invoice_number}) - Amount: {payment.amount}'
                    )
                )
                created_count += 1
        
        # Summary
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS(f'\nSummary:'))
        self.stdout.write(f'  Total payments processed: {all_payments.count()}')
        self.stdout.write(f'  Journal entries created: {created_count}')
        self.stdout.write(f'  Skipped (already exist): {skipped_count}')
        self.stdout.write(f'  Errors: {error_count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN MODE - No actual changes were made'))
            self.stdout.write('Run without --dry-run to apply changes')
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Journal entries backfilled successfully'))
