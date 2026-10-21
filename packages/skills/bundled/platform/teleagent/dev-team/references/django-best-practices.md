---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '4dc9899d-3571-4b8d-875e-c3a0b6f1295e'
  PropagateID: '4dc9899d-3571-4b8d-875e-c3a0b6f1295e'
  ReservedCode1: '6dbe32a7-e896-4ff7-9f5c-06fc25fa3857'
  ReservedCode2: '6dbe32a7-e896-4ff7-9f5c-06fc25fa3857'
---

# Django Best Practices

Production-grade guide for Django 5.x and DRF. 40+ rules across 8 categories.

## Core Principles

```
1. ✅ Custom User model BEFORE first migration (can't change later)
2. ✅ One Django app per domain concept (users, orders, payments)
3. ✅ Fat models, thin views — business logic in models/managers, not views
4. ✅ Always use select_related/prefetch_related (prevent N+1)
5. ✅ Settings split by environment (base + dev + prod)
6. ✅ Test with pytest-django + factory_boy (not fixtures)
7. ✅ Never use runserver in production (Gunicorn + Nginx)
```

---

## 1. Project Structure

```
myproject/
├── config/settings/   # base.py, dev.py, prod.py
├── apps/
│   ├── users/         # models, serializers, views, urls, services, selectors, tests/
│   ├── orders/
│   └── payments/
├── requirements/      # base.txt, dev.txt, prod.txt
└── docker-compose.yml
```

**Rules:** One app = one bounded context. Business logic in `services.py` / `selectors.py`, not views. Never import across app boundaries at model level (use IDs).

---

## 2. Models & Migrations

### Custom User Model (Day 1!)

```python
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    class Meta:
        db_table = 'users'

# settings/base.py
AUTH_USER_MODEL = 'users.User'
```

**This MUST be done before `migrate`. Cannot change after.**

### Model Best Practices

```python
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Order(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING, db_index=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'status'])]
```

### Migration Rules

- Review SQL: `python manage.py sqlmigrate app_name 0001`
- Name descriptively: `--name add_status_index_to_orders`
- Separate data from schema migrations
- Never edit/delete applied migrations

---

## 3. Views & Serializers — DRF

### Service Layer Pattern

```python
class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order(user, items_data: list[dict]) -> Order:
        total = sum(item['price'] * item['quantity'] for item in items_data)
        order = Order.objects.create(user=user, total=total)
        OrderItem.objects.bulk_create([OrderItem(order=order, **item) for item in items_data])
        return order
```

### Serializers

```python
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = ['id', 'status', 'total', 'items', 'created_at']
        read_only_fields = ['id', 'total', 'created_at']

class CreateOrderSerializer(serializers.Serializer):
    """Input-only serializer — separate from output."""
    items = serializers.ListField(child=serializers.DictField(), min_length=1)
    def validate_items(self, items):
        for item in items:
            if item.get('quantity', 0) < 1:
                raise serializers.ValidationError("Quantity must be at least 1")
        return items
```

### Views (Thin!)

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    serializer = CreateOrderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    order = OrderService.create_order(request.user, serializer.validated_data['items'])
    return Response({'data': OrderSerializer(order).data}, status=status.HTTP_201_CREATED)
```

**Rules:** Separate input from output serializers. Views only: validate → call service → serialize → respond. Never use ModelSerializer for writes.

---

## 4. Authentication

| Method | When | Frontend |
|--------|------|----------|
| Session | Same-domain, SSR | Django templates / htmx |
| JWT | Different domain, SPA, mobile | React, Vue, mobile |
| OAuth2 | Third-party login | Any |

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

---

## 5. Performance

### N+1 Prevention

```python
# ❌ N+1
orders = Order.objects.all()
for o in orders: print(o.user.email)  # hits DB each time

# ✅ select_related (FK/OneToOne — JOIN)
Order.objects.select_related('user').all()

# ✅ prefetch_related (ManyToMany/reverse FK — 2 queries)
Order.objects.prefetch_related('items').all()

# ✅ Combined
Order.objects.select_related('user').prefetch_related('items').all()
```

### Query Optimization

```python
User.objects.values('id', 'email')                # only needed columns
Order.objects.annotate(item_count=Count('items'))  # DB-level aggregation
OrderItem.objects.bulk_create([...])                # bulk ops
Order.objects.filter(status='pending').update(status='cancelled')  # bulk update
```

### Caching

```python
from django.core.cache import cache

def get_product(product_id: str):
    cache_key = f'product:{product_id}'
    product = cache.get(cache_key)
    if product is None:
        product = Product.objects.get(id=product_id)
        cache.set(cache_key, product, timeout=300)
    return product
```

---

## 6. Testing

```python
# conftest.py
@pytest.fixture
def authenticated_client(api_client, user_factory):
    user = user_factory()
    api_client.force_authenticate(user=user)
    return api_client

# factories.py
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    email = factory.Sequence(lambda n: f'user{n}@example.com')

# test_views.py
@pytest.mark.django_db
class TestListOrders:
    def test_returns_user_orders(self, authenticated_client):
        OrderFactory.create_batch(3, user=authenticated_client.handler._force_user)
        response = authenticated_client.get('/api/orders/')
        assert response.status_code == 200
        assert len(response.data['data']) == 3
```

---

## 7. Admin Customization

```python
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'total', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__email', 'id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
```

---

## 8. Production Deployment

```python
# settings/prod.py
DEBUG = False
ALLOWED_HOSTS = ['example.com']
CSRF_TRUSTED_ORIGINS = ['https://example.com']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
```

**Stack:** Nginx → Gunicorn (`--workers 4 --timeout 120`) → Django → PostgreSQL + Redis → Celery.

**Rules:** `python manage.py check --deploy`. Sentry for error tracking. WhiteNoise for static files. Never runserver/SQLite/DEBUG=True in production.

---

## Anti-Patterns

| # | Don't | Do Instead |
|---|-------|-----------|
| 1 | Business logic in views | Service layer (`services.py`) |
| 2 | One giant app | App-per-domain |
| 3 | Default User model | Custom User before first migrate |
| 4 | No `select_related` | Always eager-load |
| 5 | Django fixtures for tests | `factory_boy` |
| 6 | Single `settings.py` | Split: base + dev + prod |
| 7 | `runserver` in production | Gunicorn + Nginx |
| 8 | ModelSerializer for writes | Explicit input serializer |

---

## Common Issues

- **"Can't change User model after first migration"** — Delete migrations + DB, set custom User, re-migrate. If data exists: complex migration.
- **"Serializer too slow on large querysets"** — Missing `select_related` / `prefetch_related` → N+1 queries.
- **"Circular import between apps"** — Use string references: `ForeignKey('orders.Order', ...)`. Import inside functions for services.

> AI生成