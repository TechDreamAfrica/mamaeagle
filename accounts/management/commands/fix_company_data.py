"""
Management command to fix company data integrity issues in production database.
Run this BEFORE applying migrations if you encounter:
"Incorrect integer value: 'Company Name' for column 'company_id'"
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Fix company_id data integrity issues in production database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting data cleanup...'))
        
        with connection.cursor() as cursor:
            # Check if we have any companies
            cursor.execute("SELECT COUNT(*) FROM accounts_company")
            company_count = cursor.fetchone()[0]
            
            if company_count == 0:
                self.stdout.write(self.style.ERROR('No companies found! Please create at least one company first.'))
                return
            
            # Get the first company ID to use as default
            cursor.execute("SELECT id FROM accounts_company ORDER BY id LIMIT 1")
            default_company_id = cursor.fetchone()[0]
            self.stdout.write(f'Using company ID {default_company_id} as default')
            
            tables_to_fix = [
                ('invoicing_customer', 'company_id'),
                ('invoicing_invoice', 'company_id'),
                ('invoicing_product', 'company_id'),
                ('expenses_expense', 'company_id'),
                ('expenses_expensecategory', 'company_id'),
                ('expenses_vendor', 'company_id'),
                ('sales_lead', 'company_id'),
                ('sales_customer', 'company_id'),
                ('sales_deal', 'company_id'),
                ('inventory_product', 'company_id'),
                ('inventory_stock', 'company_id'),
                ('hr_employee', 'company_id'),
            ]
            
            for table, column in tables_to_fix:
                try:
                    # Check if table exists
                    cursor.execute(f"""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_schema = DATABASE() 
                        AND table_name = '{table}'
                    """)
                    
                    if cursor.fetchone()[0] == 0:
                        self.stdout.write(f'  Skipping {table} (table does not exist)')
                        continue
                    
                    # Check if column exists
                    cursor.execute(f"""
                        SELECT COUNT(*) 
                        FROM information_schema.columns 
                        WHERE table_schema = DATABASE() 
                        AND table_name = '{table}' 
                        AND column_name = '{column}'
                    """)
                    
                    if cursor.fetchone()[0] == 0:
                        self.stdout.write(f'  Skipping {table}.{column} (column does not exist)')
                        continue
                    
                    # Fix NULL values
                    cursor.execute(f"""
                        UPDATE {table} 
                        SET {column} = %s 
                        WHERE {column} IS NULL
                    """, [default_company_id])
                    null_fixed = cursor.rowcount
                    
                    # Fix text values (non-numeric)
                    cursor.execute(f"""
                        UPDATE {table} 
                        SET {column} = %s 
                        WHERE {column} REGEXP '[^0-9]'
                    """, [default_company_id])
                    text_fixed = cursor.rowcount
                    
                    # Fix invalid foreign key references
                    cursor.execute(f"""
                        UPDATE {table} t
                        LEFT JOIN accounts_company c ON t.{column} = c.id
                        SET t.{column} = %s
                        WHERE c.id IS NULL AND t.{column} IS NOT NULL
                    """, [default_company_id])
                    invalid_fixed = cursor.rowcount
                    
                    total_fixed = null_fixed + text_fixed + invalid_fixed
                    if total_fixed > 0:
                        self.stdout.write(self.style.SUCCESS(
                            f'  ✓ Fixed {table}.{column}: '
                            f'{null_fixed} NULL, {text_fixed} text values, {invalid_fixed} invalid refs'
                        ))
                    else:
                        self.stdout.write(f'  ✓ {table}.{column} - no issues found')
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Error fixing {table}.{column}: {str(e)}'))
            
            self.stdout.write(self.style.SUCCESS('\n✓ Data cleanup completed!'))
            self.stdout.write('You can now run: python manage.py migrate')
