import uuid
from django.db import models
from django.utils import timezone


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Slug (Identificador URL)")
    name = models.CharField("Nome da Empresa", max_length=100)
    phone = models.CharField("Telefone/WhatsApp", max_length=20, null=True, blank=True)
    whatsapp_instance = models.CharField("Instância Evolution", max_length=50, null=True, blank=True)
    logo = models.ImageField("Logo", upload_to="logos/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return self.name


class Plan(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="plans")
    name = models.CharField("Nome do Plano", max_length=100)  # Ex: "10 minutos"
    duration_minutes = models.PositiveSmallIntegerField("Duração (minutos)")
    price = models.DecimalField("Preço", max_digits=6, decimal_places=2)
    is_active = models.BooleanField("Ativo", default=True)

    class Meta:
        ordering = ["duration_minutes"]
        verbose_name = "Plano"
        verbose_name_plural = "Planos"

    def __str__(self):
        return f"{self.name} - R$ {self.price}"


class PaymentMethod(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="payment_methods")
    name = models.CharField("Nome do Método", max_length=50) # Ex: "Pix", "Dinheiro"
    is_active = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Forma de Pagamento"
        verbose_name_plural = "Formas de Pagamento"

    def __str__(self):
        return self.name


class Child(models.Model):
    """Criança cadastrada (pode voltar outras vezes)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="children")
    name = models.CharField("Nome", max_length=100)
    guardian_name = models.CharField("Nome do responsável", max_length=100)
    guardian_whatsapp = models.CharField("WhatsApp", max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Criança"
        verbose_name_plural = "Crianças"

    def __str__(self):
        return f"{self.name} ({self.guardian_whatsapp})"


class SessionStatus(models.TextChoices):
    WAITING = "waiting", "Aguardando início"
    RUNNING = "running", "Em andamento"
    PAUSED = "paused", "Pausado"
    FINISHED = "finished", "Finalizado"
    EXPIRED = "expired", "Expirado (não retirado)"


class Session(models.Model):
    """
    Uma sessão de uso do playground.
    Cada vez que uma criança entra, cria-se uma Session.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="sessions")

    # Link público para o responsável acompanhar
    public_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    child = models.ForeignKey(
        Child, on_delete=models.PROTECT,
        related_name="sessions", verbose_name="Criança"
    )

    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, verbose_name="Plano")
    status = models.CharField(
        "Status", max_length=10,
        choices=SessionStatus.choices,
        default=SessionStatus.WAITING
    )

    # Controle de tempo
    started_at = models.DateTimeField("Iniciado em", null=True, blank=True)
    paused_at = models.DateTimeField("Pausado em", null=True, blank=True)
    total_paused_seconds = models.PositiveIntegerField("Segundos pausados", default=0)
    finished_at = models.DateTimeField("Finalizado em", null=True, blank=True)

    # Pagamento
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Forma de pagamento"
    )
    payment_confirmed = models.BooleanField("Pagamento confirmado", default=False)
    amount_paid = models.DecimalField(
        "Valor pago", max_digits=6, decimal_places=2, null=True, blank=True
    )

    # Observações
    notes = models.TextField("Observações", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Sessão"
        verbose_name_plural = "Sessões"

    def __str__(self):
        return f"{self.child.name} — {self.plan.name} — {self.get_status_display()}"

    added_duration_seconds = models.PositiveIntegerField(default=0, verbose_name="Tempo Extra (segundos)")

    @property
    def plan_duration_seconds(self):
        base_seconds = self.plan.duration_minutes * 60 if self.plan else 0
        return base_seconds + self.added_duration_seconds

    @property
    def elapsed_seconds(self):
        """Segundos realmente decorridos (descontando pausas)."""
        if not self.started_at:
            return 0
        if self.status == SessionStatus.PAUSED and self.paused_at:
            end = self.paused_at
        elif self.finished_at:
            end = self.finished_at
        else:
            end = timezone.now()
        raw = (end - self.started_at).total_seconds()
        return max(0, raw - self.total_paused_seconds)

    @property
    def remaining_seconds(self):
        return max(0, self.plan_duration_seconds - self.elapsed_seconds)

    @property
    def public_url_path(self):
        return f"/{self.company.id}/ver/{self.public_token}"

    def start(self):
        if self.status == SessionStatus.WAITING:
            self.status = SessionStatus.RUNNING
            self.started_at = timezone.now()
            self.save(update_fields=["status", "started_at"])

    def pause(self):
        if self.status == SessionStatus.RUNNING:
            self.status = SessionStatus.PAUSED
            self.paused_at = timezone.now()
            self.save(update_fields=["status", "paused_at"])

    def resume(self):
        if self.status == SessionStatus.PAUSED and self.paused_at:
            paused_duration = (timezone.now() - self.paused_at).total_seconds()
            self.total_paused_seconds += int(paused_duration)
            self.status = SessionStatus.RUNNING
            self.paused_at = None
            self.save(update_fields=["status", "paused_at", "total_paused_seconds"])

    def finish(self):
        if self.status in [SessionStatus.WAITING, SessionStatus.RUNNING, SessionStatus.PAUSED]:
            self.status = SessionStatus.FINISHED
            self.finished_at = timezone.now()
            self.save(update_fields=["status", "finished_at"])
