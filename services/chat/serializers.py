from datetime import date
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    UserProfile, ChatSession, ChatMessage, Workspace, Dataset, FileCategory, DatasetTag, DatasetVersion,
    Organization, Membership, Dashboard, Trigger, TriggerLog, SharedAccess, Comment, Recommendation,
)
from . import quotas

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'email']


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    daily_message_limit = serializers.SerializerMethodField()
    messages_remaining_today = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'avatar', 'phone', 'bio', 'created_at', 'updated_at',
            'plan', 'daily_messages', 'last_message_date',
            'daily_message_limit', 'messages_remaining_today',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'daily_messages', 'last_message_date',
            'daily_message_limit', 'messages_remaining_today',
        ]

    def get_daily_message_limit(self, obj):
        return quotas.get_plan_limits(obj.plan)["daily_messages"]

    def get_messages_remaining_today(self, obj):
        limit = quotas.get_plan_limits(obj.plan)["daily_messages"]
        if limit is None:
            return None
        used = obj.daily_messages if obj.last_message_date == date.today() else 0
        return max(limit - used, 0)


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'created_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = ['id', 'session_id', 'title', 'created_at', 'updated_at', 'messages']


class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = Membership
        fields = ['id', 'user_id', 'user_email', 'role', 'created_at']
        read_only_fields = ['id', 'user_id', 'user_email', 'created_at']


class OrganizationSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    member_count = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ['id', 'name', 'owner_email', 'member_count', 'my_role', 'created_at']
        read_only_fields = ['id', 'owner_email', 'member_count', 'my_role', 'created_at']

    def get_member_count(self, obj):
        return obj.memberships.count()

    def get_my_role(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        m = obj.memberships.filter(user=request.user).first()
        return m.role if m else None


class WorkspaceSerializer(serializers.ModelSerializer):
    usage = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ['id', 'name', 'owner', 'description', 'created_at', 'updated_at', 'usage']
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at', 'usage']

    def get_usage(self, obj):
        return quotas.workspace_usage_summary(obj)


class FileCategorySerializer(serializers.ModelSerializer):
    dataset_count = serializers.SerializerMethodField()

    class Meta:
        model = FileCategory
        fields = ['id', 'name', 'color', 'workspace', 'created_at', 'dataset_count']
        read_only_fields = ['id', 'workspace', 'created_at']

    def get_dataset_count(self, obj):
        return obj.datasets.count()


class DatasetTagSerializer(serializers.ModelSerializer):
    dataset_count = serializers.SerializerMethodField()

    class Meta:
        model = DatasetTag
        fields = ['id', 'name', 'color', 'workspace', 'created_at', 'dataset_count']
        read_only_fields = ['id', 'workspace', 'created_at']

    def get_dataset_count(self, obj):
        return obj.datasets.count()


class DatasetVersionSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = DatasetVersion
        fields = [
            'id', 'dataset', 'version_number', 'file_url', 'file_name',
            'file_size', 'file_hash', 'analysis_context', 'description',
            'tags', 'created_at', 'created_by', 'note'
        ]
        read_only_fields = [
            'id', 'dataset', 'version_number', 'file_name',
            'file_size', 'file_hash', 'created_at', 'created_by'
        ]

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class DatasetSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    category_detail = FileCategorySerializer(source='category', read_only=True)
    tag_details = DatasetTagSerializer(source='tag_objects', many=True, read_only=True)
    latest_version = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = [
            'id', 'file', 'file_url', 'original_name', 'file_name', 'source_url',
            'file_size', 'file_type', 'file_hash', 'uploaded_at',
            'updated_at', 'uploaded_by', 'workspace', 'status',
            'validation_errors', 'analysis_context',
            'description', 'tags', 'tag_objects', 'tag_details',
            'category', 'category_detail', 'starred',
            'archived', 'archived_at',
            'version', 'parent_version', 'latest_version'
        ]
        read_only_fields = [
            'id', 'original_name', 'file_name', 'file_size',
            'file_type', 'file_hash', 'uploaded_at', 'updated_at',
            'uploaded_by', 'workspace', 'status', 'validation_errors',
            'analysis_context', 'archived_at', 'version'
        ]

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None

    def get_latest_version(self, obj):
        return obj.versions.first().version_number if obj.versions.exists() else obj.version


class DashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = ['id', 'name', 'layout', 'dataset', 'is_ai_generated', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class TriggerLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriggerLog
        fields = ['id', 'trigger', 'dataset', 'fired_at', 'status', 'message']
        read_only_fields = fields


class TriggerSerializer(serializers.ModelSerializer):
    last_logs = serializers.SerializerMethodField()

    class Meta:
        model = Trigger
        fields = [
            'id', 'name', 'event_type', 'action_type', 'config', 'active',
            'created_by', 'created_at', 'updated_at', 'last_triggered_at', 'last_logs',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at', 'last_triggered_at']

    def get_last_logs(self, obj):
        return TriggerLogSerializer(obj.logs.all()[:5], many=True).data


class SharedAccessSerializer(serializers.ModelSerializer):
    shared_with_email = serializers.CharField(source='shared_with.email', read_only=True, default=None)
    shared_with_org_name = serializers.CharField(source='shared_with_org.name', read_only=True, default=None)

    class Meta:
        model = SharedAccess
        fields = [
            'id', 'dataset', 'dashboard', 'shared_with', 'shared_with_email',
            'shared_with_org', 'shared_with_org_name', 'shared_by', 'permission', 'created_at',
        ]
        read_only_fields = ['id', 'shared_by', 'created_at']


class CommentSerializer(serializers.ModelSerializer):
    author_email = serializers.CharField(source='author.email', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'dataset', 'dashboard', 'author', 'author_email', 'body', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']


class RecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = ['id', 'dataset', 'title', 'body', 'category', 'generated_at', 'dismissed']
        read_only_fields = ['id', 'generated_at']
