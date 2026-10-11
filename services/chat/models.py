import hashlib
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Organization(models.Model):
    """Módulo 1 — soporte multiusuario real (antes: 1 usuario = 1 workspace, sin jerarquías)."""
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_organizations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Membership(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Propietario'),
        ('admin', 'Administrador'),
        ('member', 'Miembro'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['organization', 'user']
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.email} @ {self.organization.name} ({self.role})"


class Workspace(models.Model):
    name = models.CharField(max_length=200)
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='workspace')
    # Un workspace personal puede opcionalmente pertenecer a una organización
    # (colaboración de equipo); si es null, sigue siendo 100% personal.
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='workspaces')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.owner.email}'s Workspace"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.URLField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    plan = models.CharField(max_length=100, default="free")
    daily_messages = models.IntegerField(default=0)
    last_message_date = models.DateField(blank=True, null=True)

    # --- MFA (Módulo 1) ---
    mfa_secret = models.CharField(max_length=64, blank=True, default='')
    mfa_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - Profile"


class FileCategory(models.Model):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#6366f1')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='file_categories')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ['name', 'workspace']

    def __str__(self):
        return self.name


class DatasetTag(models.Model):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#6366f1')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='tags')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ['name', 'workspace']

    def __str__(self):
        return self.name


class Dataset(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('valid', 'Válido'),
        ('invalid', 'Inválido'),
        ('processing', 'Procesando'),
    ]

    file = models.FileField(upload_to='datasets/%Y/%m/%d/')

    original_name = models.CharField(max_length=255)
    source_url = models.URLField(blank=True, null=True)  # si se importó desde una API externa (Módulo 2)
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    file_type = models.CharField(max_length=50)
    file_hash = models.CharField(max_length=64, unique=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='datasets')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='datasets')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    validation_errors = models.JSONField(default=list, blank=True)

    analysis_context = models.JSONField(default=dict, blank=True)

    description = models.TextField(blank=True, default='')
    tags = models.JSONField(default=list, blank=True)
    tag_objects = models.ManyToManyField(DatasetTag, blank=True, related_name='datasets')
    category = models.ForeignKey(FileCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='datasets')
    starred = models.BooleanField(default=False)

    archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    version = models.PositiveIntegerField(default=1)
    parent_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_versions')

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.file_name} - {self.uploaded_by.email}"

    def save(self, *args, **kwargs):
        if self.file and not self.file_hash:
            self.file_hash = self._calculate_file_hash()
        if self.file:
            try:
                self.file.seek(0)
            except (AttributeError, OSError):
                pass
        super().save(*args, **kwargs)

    def _calculate_file_hash(self):
        sha256_hash = hashlib.sha256()
        for chunk in self.file.chunks():
            sha256_hash.update(chunk)
        try:
            self.file.seek(0)
        except (AttributeError, OSError):
            pass
        return sha256_hash.hexdigest()

    @staticmethod
    def compute_file_hash_static(file_obj):
        sha256_hash = hashlib.sha256()
        for chunk in file_obj.chunks():
            sha256_hash.update(chunk)
        try:
            file_obj.seek(0)
        except (AttributeError, OSError):
            pass
        return sha256_hash.hexdigest()


class DatasetVersion(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to='datasets/versions/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    file_hash = models.CharField(max_length=64)
    analysis_context = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True, default='')
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-version_number']
        unique_together = ['dataset', 'version_number']

    def __str__(self):
        return f"{self.dataset.file_name} v{self.version_number}"


class Dashboard(models.Model):
    """
    Módulo 4 — dashboards armables. `layout` guarda una lista ordenada de
    widgets (KPIs o gráficos) con su configuración; el orden de la lista ES
    la posición en la grilla, así que "drag & drop" en el frontend se
    traduce simplemente en reordenar esta lista. Puede crearse a mano o
    generarse automáticamente a partir del último análisis de un dataset
    (`is_ai_generated=True`).

    Forma de cada elemento de `layout`:
        {"id": str, "kind": "kpi" | "chart", "title": str,
         "chart_type": str (solo si kind="chart"), "source": dict}
    """
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='dashboards')
    dataset = models.ForeignKey(Dataset, on_delete=models.SET_NULL, null=True, blank=True, related_name='dashboards')
    name = models.CharField(max_length=200, default='Mi Dashboard')
    layout = models.JSONField(default=list, blank=True)
    is_ai_generated = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.name} ({self.workspace.owner.email})"


class ChatSession(models.Model):
    # NOTA DE SEGURIDAD: session_id ya NO es único a nivel global. El frontend
    # usa 'default' como id inicial para todos los usuarios, por lo que un
    # unique=True global causaba que TODOS los usuarios compartieran la misma
    # fila de chat (fuga de datos entre cuentas). Ahora la unicidad es por
    # (user, session_id), y toda sesión creada después de este cambio exige
    # un usuario autenticado.
    session_id = models.CharField(max_length=120)
    title = models.CharField(max_length=200, default="Nueva sesión")
    rolling_summary = models.TextField(blank=True, default="")
    dataset_context = models.JSONField(default=dict, blank=True)
    dataset_history = models.JSONField(default=list, blank=True)
    decision_notes = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_temporary = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_sessions')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_sessions')
    dataset = models.ForeignKey(Dataset, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_sessions')

    class Meta:
        ordering = ["-updated_at"]
        # Un mismo session_id puede repetirse entre usuarios distintos
        # (p. ej. 'default'), pero nunca dos veces para el mismo usuario.
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'session_id'],
                name='unique_session_id_per_user',
            ),
        ]

    def __str__(self):
        owner = self.user.email if self.user_id else "sin-usuario"
        return f"{self.session_id} ({owner})"


class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ("system", "System"),
        ("user", "User"),
        ("assistant", "Assistant"),
    )

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.session.session_id}:{self.role}"
