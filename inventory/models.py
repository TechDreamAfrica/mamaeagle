from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.utils import timezone
import uuid
from accounts.managers import CompanyManager

User = get_user_model()


class Category(models.Model):
    """
    Model representing inventory categories for organizing products.
    """
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='inventory_categories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CompanyManager()
    
    class Meta:
        db_table = 'inventory_category'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
        unique_together = ['company', 'name']
        indexes = [
            models.Index(fields=['company', 'is_active']),
        ]
    
    def __str__(self):
        if self.parent_category:
            return f"{self.parent_category.name} > {self.name}"
        return self.name
    
    @property
    def full_path(self):
        """Return the full category path."""
        path = [self.name]
        parent = self.parent_category
        while parent:
            path.insert(0, parent.name)
            parent = parent.parent_category
        return " > ".join(path)


class Supplier(models.Model):
    """
    Model representing suppliers/vendors for inventory items.
    """
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='suppliers')
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    payment_terms = models.CharField(max_length=100, blank=True)
    lead_time_days = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    rating = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CompanyManager()
    
    class Meta:
        db_table = 'inventory_supplier'
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
        ordering = ['name']
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['company', 'name']),
        ]
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Model representing inventory products/items.
    """
    PRODUCT_TYPES = [
        ('physical', 'Physical Product'),
        ('digital', 'Digital Product'),
        ('service', 'Service'),
        ('bundle', 'Bundle'),
    ]
    
    UNIT_TYPES = [
        ('piece', 'Piece'),
        ('box', 'Box'),
        ('case', 'Case'),
        ('dozen', 'Dozen'),
        ('kg', 'Kilogram'),
        ('lb', 'Pound'),
        ('liter', 'Liter'),
        ('gallon', 'Gallon'),
        ('meter', 'Meter'),
        ('hour', 'Hour'),
        ('each', 'Each'),
    ]
    
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='inventory_products')
    sku = models.CharField(max_length=50)
    barcode = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='physical')
    unit_type = models.CharField(max_length=20, choices=UNIT_TYPES, default='piece')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_stock_level = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    maximum_stock_level = models.IntegerField(default=1000, validators=[MinValueValidator(0)])
    reorder_point = models.IntegerField(default=10, validators=[MinValueValidator(0)])
    reorder_quantity = models.IntegerField(default=50, validators=[MinValueValidator(0)])
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    dimensions = models.CharField(max_length=100, blank=True, help_text="L x W x H")
    suppliers = models.ManyToManyField(Supplier, through='ProductSupplier', related_name='products')
    is_active = models.BooleanField(default=True)
    is_serialized = models.BooleanField(default=False)
    tax_exempt = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_products')
    
    objects = CompanyManager()
    
    class Meta:
        db_table = 'inventory_product'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['name']
        unique_together = [['company', 'sku'], ['company', 'barcode']]
        indexes = [
            models.Index(fields=['company', 'sku']),
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['company', 'name']),
        ]
    
    def __str__(self):
        return f"{self.sku} - {self.name}"
    
    @property
    def current_stock(self):
        """Calculate current stock level."""
        stock_movements = self.stock_movements.aggregate(
            total=models.Sum('quantity_change')
        )
        return stock_movements['total'] or 0
    
    @property
    def stock_value(self):
        """Calculate total value of current stock."""
        return self.current_stock * self.cost_price
    
    @property
    def needs_reorder(self):
        """Check if product needs to be reordered."""
        return self.current_stock <= self.reorder_point
    
    @property
    def is_low_stock(self):
        """Check if product is below minimum stock level."""
        return self.current_stock <= self.minimum_stock_level
    
    def send_low_stock_alert(self):
        """Send SMS alert for low stock to admin users."""
        if self.is_low_stock:
            from .utils import send_low_stock_sms
            admin_users = User.objects.filter(
                companies__company=self.company,
                role__in=['admin', 'manager'],
                is_active=True
            ).distinct()
            
            for admin in admin_users:
                if admin.phone_number:
                    send_low_stock_sms(
                        phone=admin.phone_number,
                        product_name=self.name,
                        current_stock=self.current_stock,
                        minimum_stock=self.minimum_stock_level
                    )
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage."""
        if self.cost_price == 0:
            return 0
        return ((self.selling_price - self.cost_price) / self.cost_price) * 100

    def save(self, *args, **kwargs):
        """Generate SKU and slug if not provided."""
        import random
        import string
        from django.utils.text import slugify
        
        # Auto-generate SKU if not provided
        if not self.sku and self.name:
            base_sku = ''.join(word[:3].upper() for word in self.name.split()[:3])
            sku = base_sku
            num = 1
            while Product.objects.filter(company=self.company, sku=sku).exclude(pk=self.pk).exists():
                # Add random suffix to make it unique
                suffix = ''.join(random.choices(string.digits, k=3))
                sku = f"{base_sku}{suffix}"
                num += 1
                if num > 100:  # Prevent infinite loop
                    sku = f"{base_sku}{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"
                    break
            self.sku = sku
        
        # Auto-generate slug if not provided
        if not self.slug and self.name:
            base_slug = slugify(self.name)
            slug = base_slug
            num = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{num}"
                num += 1
            self.slug = slug
            
        super().save(*args, **kwargs)


class ProductSupplier(models.Model):
    """
    Model representing the relationship between products and suppliers.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    supplier_sku = models.CharField(max_length=100, blank=True)
    supplier_cost = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_order_quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    lead_time_days = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_preferred = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_productsupplier'
        verbose_name = 'Product Supplier'
        verbose_name_plural = 'Product Suppliers'
        unique_together = ['product', 'supplier']
        ordering = ['product__name', 'supplier__name']
    
    def __str__(self):
        return f"{self.product.name} - {self.supplier.name}"


class Warehouse(models.Model):
    """
    Model representing warehouse/storage locations.
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_warehouses')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_warehouse'
        verbose_name = 'Warehouse'
        verbose_name_plural = 'Warehouses'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class StockMovement(models.Model):
    """
    Model representing all stock movements (in/out/transfers).
    """
    MOVEMENT_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return'),
        ('damage', 'Damage'),
        ('theft', 'Theft'),
        ('expired', 'Expired'),
        ('initial', 'Initial Stock'),
    ]
    
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='stock_movements')
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity_change = models.IntegerField(help_text="Positive for stock in, negative for stock out")
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    movement_date = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='stock_movements')
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = CompanyManager()
    
    class Meta:
        db_table = 'inventory_stockmovement'
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'
        indexes = [
            models.Index(fields=['company', 'product']),
            models.Index(fields=['company', 'movement_date']),
        ]
        ordering = ['-movement_date', '-created_at']
        indexes = [
            models.Index(fields=['movement_date']),
            models.Index(fields=['movement_type']),
            models.Index(fields=['product', 'warehouse']),
        ]
    
    def __str__(self):
        return f"{self.product.sku} - {self.movement_type} - {self.quantity_change}"
    
    def save(self, *args, **kwargs):
        """Calculate total cost before saving."""
        if self.unit_cost and self.quantity_change:
            self.total_cost = abs(self.quantity_change) * self.unit_cost
        super().save(*args, **kwargs)


class StockLevel(models.Model):
    """
    Model representing current stock levels per product per warehouse.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_levels')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_levels')
    quantity_on_hand = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    quantity_reserved = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    quantity_available = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    last_movement_date = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_stocklevel'
        verbose_name = 'Stock Level'
        verbose_name_plural = 'Stock Levels'
        unique_together = ['product', 'warehouse']
        ordering = ['product__name', 'warehouse__name']
    
    def __str__(self):
        return f"{self.product.sku} - {self.warehouse.code} - {self.quantity_on_hand}"
    
    def save(self, *args, **kwargs):
        """Calculate available quantity before saving."""
        self.quantity_available = self.quantity_on_hand - self.quantity_reserved
        super().save(*args, **kwargs)


class PurchaseOrder(models.Model):
    """
    Model representing purchase orders for inventory replenishment.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('confirmed', 'Confirmed'),
        ('partially_received', 'Partially Received'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
        ('closed', 'Closed'),
    ]
    
    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='purchase_orders')
    order_date = models.DateField(default=timezone.now)
    expected_delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_purchase_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_purchaseorder'
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'
        ordering = ['-order_date', '-created_at']
    
    def __str__(self):
        return f"PO {self.po_number} - {self.supplier.name}"
    
    @property
    def total_items(self):
        """Return total number of items in the purchase order."""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0


class PurchaseOrderItem(models.Model):
    """
    Model representing line items in purchase orders.
    """
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='purchase_order_items')
    quantity_ordered = models.IntegerField(validators=[MinValueValidator(1)])
    quantity_received = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'inventory_purchaseorderitem'
        verbose_name = 'Purchase Order Item'
        verbose_name_plural = 'Purchase Order Items'
        unique_together = ['purchase_order', 'product']
        ordering = ['product__name']
    
    def __str__(self):
        return f"{self.purchase_order.po_number} - {self.product.name}"
    
    @property
    def quantity_pending(self):
        """Return quantity still pending delivery."""
        return self.quantity_ordered - self.quantity_received
    
    @property
    def is_fully_received(self):
        """Return True if all ordered quantity has been received."""
        return self.quantity_received >= self.quantity_ordered
    
    def save(self, *args, **kwargs):
        """Calculate total cost before saving."""
        self.total_cost = self.quantity_ordered * self.unit_cost
        super().save(*args, **kwargs)


class InventoryCount(models.Model):
    """
    Model representing physical inventory counts/audits.
    """
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    count_number = models.CharField(max_length=50, unique=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventory_counts')
    count_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    count_type = models.CharField(max_length=20, choices=[
        ('full', 'Full Count'),
        ('cycle', 'Cycle Count'),
        ('spot', 'Spot Check'),
    ], default='cycle')
    counted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_counts')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'inventory_inventorycount'
        verbose_name = 'Inventory Count'
        verbose_name_plural = 'Inventory Counts'
        ordering = ['-count_date']
    
    def __str__(self):
        return f"Count {self.count_number} - {self.warehouse.name} ({self.count_date})"


class InventoryCountItem(models.Model):
    """
    Model representing individual items counted during inventory audits.
    """
    inventory_count = models.ForeignKey(InventoryCount, on_delete=models.CASCADE, related_name='count_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='count_items')
    expected_quantity = models.IntegerField(default=0)
    counted_quantity = models.IntegerField(null=True, blank=True)
    variance = models.IntegerField(default=0)
    variance_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    counted_at = models.DateTimeField(null=True, blank=True)
    counted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='counted_items')
    
    class Meta:
        db_table = 'inventory_inventorycountitem'
        verbose_name = 'Inventory Count Item'
        verbose_name_plural = 'Inventory Count Items'
        unique_together = ['inventory_count', 'product']
        ordering = ['product__name']
    
    def __str__(self):
        return f"{self.inventory_count.count_number} - {self.product.name}"
    
    def save(self, *args, **kwargs):
        """Calculate variance before saving."""
        if self.counted_quantity is not None:
            self.variance = self.counted_quantity - self.expected_quantity
            self.variance_value = self.variance * self.product.cost_price
        super().save(*args, **kwargs)
