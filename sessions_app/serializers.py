from rest_framework import serializers
from .models import Company, Session, Child, Plan, PaymentMethod


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "slug", "name", "phone", "whatsapp_instance", "logo", "created_at"]


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "name", "duration_minutes", "price", "is_active"]


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["id", "name", "is_active"]


class ChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = Child
        fields = ["id", "name", "guardian_name", "guardian_whatsapp", "created_at"]


class SessionCreateSerializer(serializers.ModelSerializer):
    """Usado pelo operador para abrir uma nova sessão."""
    child_id = serializers.UUIDField(required=False)
    child_name = serializers.CharField(required=False, write_only=True)
    guardian_name = serializers.CharField(required=False, write_only=True)
    guardian_whatsapp = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = Session
        fields = [
            "id", "public_token",
            "child_id", "child_name", "guardian_name", "guardian_whatsapp",
            "plan", "payment_method", "payment_confirmed", "amount_paid", "notes",
        ]
        read_only_fields = ["id", "public_token"]

    def validate(self, data):
        has_child_id = "child_id" in data
        has_inline = all(k in data for k in ["child_name", "guardian_whatsapp"])
        if not has_child_id and not has_inline:
            raise serializers.ValidationError(
                "Informe child_id (criança existente) ou os dados da criança (child_name, guardian_whatsapp)."
            )
        return data

    def create(self, validated_data):
        company = self.context['company']
        
        child_id = validated_data.pop("child_id", None)
        child_name = validated_data.pop("child_name", None)
        guardian_name = validated_data.pop("guardian_name", "")
        guardian_whatsapp = validated_data.pop("guardian_whatsapp", None)

        if child_id:
            child = Child.objects.get(id=child_id, company=company)
        else:
            child, _ = Child.objects.get_or_create(
                company=company,
                guardian_whatsapp=guardian_whatsapp,
                name=child_name,
                defaults={
                    "guardian_name": guardian_name,
                },
            )

        if "plan" in validated_data and "amount_paid" not in validated_data:
            validated_data["amount_paid"] = validated_data["plan"].price
            validated_data["payment_confirmed"] = True

        session = Session.objects.create(company=company, child=child, **validated_data)
        return session


class SessionDetailSerializer(serializers.ModelSerializer):
    """Retornado nas listagens e no link público."""
    child = ChildSerializer(read_only=True)
    elapsed_seconds = serializers.IntegerField(read_only=True)
    remaining_seconds = serializers.IntegerField(read_only=True)
    plan_duration_seconds = serializers.IntegerField(read_only=True)
    public_url_path = serializers.CharField(read_only=True)
    plan_label = serializers.CharField(source="plan.name", read_only=True)
    plan_price = serializers.DecimalField(source="plan.price", max_digits=8, decimal_places=2, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Session
        fields = [
            "id", "public_token", "public_url_path",
            "child",
            "plan", "plan_label", "plan_duration_seconds", "plan_price",
            "status", "status_label",
            "started_at", "finished_at",
            "elapsed_seconds", "remaining_seconds",
            "payment_method", "payment_confirmed", "amount_paid",
            "notes", "created_at",
        ]
