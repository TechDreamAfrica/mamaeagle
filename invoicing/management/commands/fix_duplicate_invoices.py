from django.core.management.base import BaseCommand
from django.db.models import Count
from invoicing.models import Invoice
import re


class Command(BaseCommand):
    help = 'Find and fix duplicate invoice numbers'

    def handle(self, *args, **kwargs):
        self.stdout.write('Checking for duplicate invoice numbers...\n')
        
        # Find duplicate invoice numbers
        duplicates = Invoice.objects.values('invoice_number').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        if not duplicates:
            self.stdout.write(self.style.SUCCESS('No duplicate invoice numbers found!'))
            return
        
        self.stdout.write(self.style.WARNING(f'Found {len(duplicates)} duplicate invoice numbers'))
        
        for dup in duplicates:
            invoice_number = dup['invoice_number']
            self.stdout.write(f'\nProcessing duplicate: {invoice_number}')
            
            # Get all invoices with this number
            invoices = Invoice.objects.filter(invoice_number=invoice_number).order_by('id')
            
            # Keep the first one, renumber the rest
            for idx, invoice in enumerate(invoices):
                if idx == 0:
                    self.stdout.write(f'  Keeping invoice ID {invoice.id} with number {invoice_number}')
                    continue
                
                # Find a new unique number
                user = invoice.user
                all_invoices = Invoice.objects.filter(
                    user=user,
                    invoice_number__regex=r'^INV-\d+$'
                ).values_list('invoice_number', flat=True)
                
                max_number = 0
                for inv_num in all_invoices:
                    match = re.search(r'INV-(\d+)$', inv_num)
                    if match:
                        num = int(match.group(1))
                        if num > max_number:
                            max_number = num
                
                new_number = max_number + 1
                new_invoice_number = f"INV-{new_number:05d}"
                
                old_number = invoice.invoice_number
                invoice.invoice_number = new_invoice_number
                invoice.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  Renumbered invoice ID {invoice.id}: {old_number} -> {new_invoice_number}'
                    )
                )
        
        self.stdout.write(self.style.SUCCESS('\nAll duplicates have been fixed!'))
