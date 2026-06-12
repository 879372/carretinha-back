from django.contrib import admin
from .models import Company, Plan, PaymentMethod, Child, Session

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "phone", "whatsapp_instance", "created_at")
    search_fields = ("name", "slug", "phone")
    readonly_fields = ("id", "created_at")

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "price", "duration_minutes")
    list_filter = ("company",)

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "company")
    list_filter = ("company",)

@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "guardian_name", "guardian_whatsapp")
    list_filter = ("company",)
    search_fields = ("name", "guardian_name", "guardian_whatsapp")

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("child", "company", "status", "started_at", "finished_at")
    list_filter = ("company", "status")
    search_fields = ("child__name",)
