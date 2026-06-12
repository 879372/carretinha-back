import os
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Company, Session, Child, SessionStatus, Plan, PaymentMethod
from .serializers import (
    CompanySerializer, PlanSerializer, PaymentMethodSerializer,
    SessionCreateSerializer, SessionDetailSerializer, ChildSerializer
)
from .services import send_whatsapp_message


def broadcast_session(session):
    """Manda atualização via WebSocket para o grupo da sessão."""
    channel_layer = get_channel_layer()
    data = SessionDetailSerializer(session).data
    async_to_sync(channel_layer.group_send)(
        f"session_{session.public_token}",
        {"type": "session.update", "data": data},
    )


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [AllowAny]


class PlanViewSet(viewsets.ModelViewSet):
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Plan.objects.filter(company__id=self.kwargs.get("company_id"))

    def perform_create(self, serializer):
        company = get_object_or_404(Company, id=self.kwargs.get("company_id"))
        serializer.save(company=company)


class PaymentMethodViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentMethodSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return PaymentMethod.objects.filter(company__id=self.kwargs.get("company_id"))

    def perform_create(self, serializer):
        company = get_object_or_404(Company, id=self.kwargs.get("company_id"))
        serializer.save(company=company)


class ChildViewSet(viewsets.ModelViewSet):
    serializer_class = ChildSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Child.objects.filter(company__id=self.kwargs.get("company_id"))
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

    def perform_create(self, serializer):
        company = get_object_or_404(Company, id=self.kwargs.get("company_id"))
        serializer.save(company=company)


class SessionViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "create":
            return SessionCreateSerializer
        return SessionDetailSerializer

    def get_company(self):
        company_id = self.kwargs["company_id"]
        return get_object_or_404(Company, id=company_id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if "company_id" in self.kwargs:
            context["company"] = self.get_company()
        return context

    def get_queryset(self):
        qs = Session.objects.filter(company__id=self.kwargs.get("company_id")).select_related("child", "plan", "payment_method")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        date = self.request.query_params.get("date")
        if date:
            qs = qs.filter(created_at__date=date)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save()
        return Response(
            SessionDetailSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None, company_id=None):
        session = self.get_object()
        if session.status != SessionStatus.WAITING:
            return Response({"detail": "Sessão não está em espera."}, status=400)
        session.start()
        broadcast_session(session)
        
        # Enviar WhatsApp pelo backend usando Evolution API
        if session.child.guardian_whatsapp:
            frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5174")
            public_url = f"{frontend_url.rstrip('/')}{session.public_url_path}"
            msg = f"Olá! Acompanhe o tempo de brincadeira de {session.child.name} aqui: {public_url}"
            send_whatsapp_message(session.child.guardian_whatsapp, msg, session.company.whatsapp_instance)
            
        return Response(SessionDetailSerializer(session).data)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None, company_id=None):
        session = self.get_object()
        if session.status != SessionStatus.RUNNING:
            return Response({"detail": "Sessão não está em andamento."}, status=400)
        session.pause()
        broadcast_session(session)
        return Response(SessionDetailSerializer(session).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None, company_id=None):
        session = self.get_object()
        if session.status != SessionStatus.PAUSED:
            return Response({"detail": "Sessão não está pausada."}, status=400)
        session.resume()
        broadcast_session(session)
        return Response(SessionDetailSerializer(session).data)

    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None, company_id=None):
        session = self.get_object()
        session.finish()
        broadcast_session(session)
        return Response(SessionDetailSerializer(session).data)

    @action(detail=True, methods=["post"])
    def add_time(self, request, pk=None, company_id=None):
        session = self.get_object()
        plan_id = request.data.get("plan")

        if not plan_id:
            return Response({"detail": "Informe o plano para adicionar tempo."}, status=status.HTTP_400_BAD_REQUEST)

        plan = get_object_or_404(Plan, id=plan_id, company=session.company)
        
        # Calcular se há "dívida" de tempo (tempo que a criança ficou a mais)
        debt = session.elapsed_seconds - session.plan_duration_seconds
        if debt > 0:
            session.added_duration_seconds += debt
            
        session.added_duration_seconds += plan.duration_minutes * 60
        
        if session.amount_paid is None:
            session.amount_paid = plan.price
        else:
            session.amount_paid += plan.price
            
        if session.status == SessionStatus.EXPIRED:
            session.status = SessionStatus.RUNNING

        session.save()
        broadcast_session(session)
        return Response(SessionDetailSerializer(session).data)

    @action(detail=True, methods=["patch"])
    def confirm_payment(self, request, pk=None, company_id=None):
        session = self.get_object()
        session.payment_confirmed = True
        payment_method_id = request.data.get("payment_method")
        if payment_method_id:
            try:
                pm = PaymentMethod.objects.get(id=payment_method_id, company=session.company)
                session.payment_method = pm
            except PaymentMethod.DoesNotExist:
                pass
        
        session.amount_paid = request.data.get("amount_paid", session.amount_paid)
        session.save(update_fields=["payment_confirmed", "payment_method", "amount_paid"])
        return Response(SessionDetailSerializer(session).data)

    # ── Link público (sem autenticação) ─────────────────────────────────────
    @action(
        detail=False, methods=["get"],
        url_path="public/(?P<public_token>[^/.]+)",
        permission_classes=[AllowAny],
    )
    def public(self, request, public_token=None, company_id=None):
        session = get_object_or_404(Session, public_token=public_token, company__id=company_id)
        return Response(SessionDetailSerializer(session).data)
