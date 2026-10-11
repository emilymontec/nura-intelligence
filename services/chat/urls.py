from django.urls import path, re_path
from . import views


urlpatterns = [
    path('test/', views.test_endpoint, name='test'),
    path('test', views.test_endpoint, name='test-no-slash'),
    path('analyze/', views.analyze_endpoint, name='analyze'),
    path('analyze', views.analyze_endpoint, name='analyze-no-slash'),
    path('chat/', views.chat_endpoint, name='chat'),
    path('chat', views.chat_endpoint, name='chat-no-slash'),
    path('sessions/', views.list_sessions, name='list_sessions'),
    path('sessions', views.list_sessions, name='list_sessions-no-slash'),
    path('sessions/<str:session_id>/', views.get_session_history, name='get_session_history'),
    path('sessions/<str:session_id>', views.get_session_history, name='get_session_history-no-slash'),
    path('sessions/<str:session_id>/rename/', views.rename_session, name='rename_session'),
    path('sessions/<str:session_id>/rename', views.rename_session, name='rename_session-no-slash'),
    path('sessions/<str:session_id>/delete/', views.delete_session, name='delete_session'),
    path('sessions/<str:session_id>/delete', views.delete_session, name='delete_session-no-slash'),
    path('sessions/<str:session_id>/report/pdf/', views.export_session_report_pdf, name='export_session_report_pdf'),
    path('sessions/<str:session_id>/report/pdf', views.export_session_report_pdf, name='export_session_report_pdf-no-slash'),
    path('sessions/<str:session_id>/report/docx/', views.export_session_report_docx, name='export_session_report_docx'),
    path('sessions/<str:session_id>/report/docx', views.export_session_report_docx, name='export_session_report_docx-no-slash'),
    path('sessions/<str:session_id>/report/pptx/', views.export_session_report_pptx, name='export_session_report_pptx'),
    path('sessions/<str:session_id>/report/pptx', views.export_session_report_pptx, name='export_session_report_pptx-no-slash'),
    path('profile/', views.user_profile, name='user_profile'),
    path('profile', views.user_profile, name='user_profile-no-slash'),
    path('workspace/', views.user_workspace, name='user_workspace'),
    path('workspace', views.user_workspace, name='user_workspace-no-slash'),
    path('workspace/usage/', views.workspace_usage, name='workspace_usage'),
    path('workspace/usage', views.workspace_usage, name='workspace_usage-no-slash'),

    # Dataset endpoints
    path('datasets/', views.dataset_list_create, name='dataset_list_create'),
    path('datasets', views.dataset_list_create, name='dataset_list_create-no-slash'),
    path('datasets/import-url/', views.dataset_import_url, name='dataset_import_url'),
    path('datasets/import-url', views.dataset_import_url, name='dataset_import_url-no-slash'),
    path('datasets/import-graphql/', views.dataset_import_graphql, name='dataset_import_graphql'),
    path('datasets/import-graphql', views.dataset_import_graphql, name='dataset_import_graphql-no-slash'),
    path('datasets/import-db/', views.dataset_import_db, name='dataset_import_db'),
    path('datasets/import-db', views.dataset_import_db, name='dataset_import_db-no-slash'),
    path('datasets/upload-chunk/', views.dataset_upload_chunk, name='dataset_upload_chunk'),
    path('datasets/upload-chunk', views.dataset_upload_chunk, name='dataset_upload_chunk-no-slash'),
    path('datasets/<int:pk>/', views.dataset_detail, name='dataset_detail'),
    path('datasets/<int:pk>', views.dataset_detail, name='dataset_detail-no-slash'),
    path('datasets/<int:pk>/activate/', views.dataset_activate, name='dataset_activate'),
    path('datasets/<int:pk>/activate', views.dataset_activate, name='dataset_activate-no-slash'),

    # File management endpoints
    path('datasets/<int:pk>/rename/', views.dataset_rename, name='dataset_rename'),
    path('datasets/<int:pk>/rename', views.dataset_rename, name='dataset_rename-no-slash'),
    path('datasets/<int:pk>/move/', views.dataset_move, name='dataset_move'),
    path('datasets/<int:pk>/move', views.dataset_move, name='dataset_move-no-slash'),
    path('datasets/<int:pk>/star/', views.dataset_toggle_star, name='dataset_toggle_star'),
    path('datasets/<int:pk>/star', views.dataset_toggle_star, name='dataset_toggle_star-no-slash'),
    path('datasets/bulk-delete/', views.dataset_bulk_delete, name='dataset_bulk_delete'),
    path('datasets/bulk-delete', views.dataset_bulk_delete, name='dataset_bulk_delete-no-slash'),
    path('datasets/stats/', views.dataset_stats, name='dataset_stats'),
    path('datasets/stats', views.dataset_stats, name='dataset_stats-no-slash'),

    # New dataset management endpoints
    path('datasets/<int:pk>/duplicate/', views.dataset_duplicate, name='dataset_duplicate'),
    path('datasets/<int:pk>/duplicate', views.dataset_duplicate, name='dataset_duplicate-no-slash'),
    path('datasets/<int:pk>/archive/', views.dataset_archive, name='dataset_archive'),
    path('datasets/<int:pk>/archive', views.dataset_archive, name='dataset_archive-no-slash'),
    path('datasets/<int:pk>/reanalyze/', views.dataset_reanalyze, name='dataset_reanalyze'),
    path('datasets/<int:pk>/reanalyze', views.dataset_reanalyze, name='dataset_reanalyze-no-slash'),
    path('datasets/<int:pk>/download/', views.dataset_download, name='dataset_download'),
    path('datasets/<int:pk>/download', views.dataset_download, name='dataset_download-no-slash'),
    path('datasets/merge/', views.dataset_merge, name='dataset_merge'),
    path('datasets/merge', views.dataset_merge, name='dataset_merge-no-slash'),

    # Versioning endpoints
    path('datasets/<int:pk>/versions/', views.dataset_versions, name='dataset_versions'),
    path('datasets/<int:pk>/versions', views.dataset_versions, name='dataset_versions-no-slash'),
    path('datasets/<int:pk>/versions/<int:version_pk>/restore/', views.dataset_restore_version, name='dataset_restore_version'),
    path('datasets/<int:pk>/versions/<int:version_pk>/restore', views.dataset_restore_version, name='dataset_restore_version-no-slash'),

    # Exploration endpoints
    path('datasets/<int:pk>/explore/', views.dataset_explore, name='dataset_explore'),
    path('datasets/<int:pk>/explore', views.dataset_explore, name='dataset_explore-no-slash'),
    path('datasets/<int:pk>/preview/', views.dataset_preview, name='dataset_preview'),
    path('datasets/<int:pk>/preview', views.dataset_preview, name='dataset_preview-no-slash'),
    path('datasets/<int:pk>/columns/', views.dataset_columns, name='dataset_columns'),
    path('datasets/<int:pk>/columns', views.dataset_columns, name='dataset_columns-no-slash'),
    path('datasets/<int:pk>/statistics/', views.dataset_statistics, name='dataset_statistics'),
    path('datasets/<int:pk>/statistics', views.dataset_statistics, name='dataset_statistics-no-slash'),
    path('datasets/<int:pk>/search/', views.dataset_search, name='dataset_search'),
    path('datasets/<int:pk>/search', views.dataset_search, name='dataset_search-no-slash'),
    path('datasets/<int:pk>/what-if/', views.dataset_what_if, name='dataset_what_if'),
    path('datasets/<int:pk>/what-if', views.dataset_what_if, name='dataset_what_if-no-slash'),
    path('datasets/<int:pk>/filter/', views.dataset_filter, name='dataset_filter'),
    path('datasets/<int:pk>/filter', views.dataset_filter, name='dataset_filter-no-slash'),

    # Tag endpoints
    path('datasets/<int:pk>/tags/add/', views.dataset_add_tags, name='dataset_add_tags'),
    path('datasets/<int:pk>/tags/add', views.dataset_add_tags, name='dataset_add_tags-no-slash'),
    path('datasets/<int:pk>/tags/remove/', views.dataset_remove_tags, name='dataset_remove_tags'),
    path('datasets/<int:pk>/tags/remove', views.dataset_remove_tags, name='dataset_remove_tags-no-slash'),

    # Tag management
    path('tags/', views.tag_list_create, name='tag_list_create'),
    path('tags', views.tag_list_create, name='tag_list_create-no-slash'),
    path('tags/<int:pk>/', views.tag_detail, name='tag_detail'),
    path('tags/<int:pk>', views.tag_detail, name='tag_detail-no-slash'),

    # Category endpoints
    path('categories/', views.category_list_create, name='category_list_create'),
    path('categories', views.category_list_create, name='category_list_create-no-slash'),
    path('categories/<int:pk>/', views.category_detail, name='category_detail'),
    path('categories/<int:pk>', views.category_detail, name='category_detail-no-slash'),

    # Organizations & roles (Módulo 1)
    path('organizations/', views.organization_list_create, name='organization_list_create'),
    path('organizations', views.organization_list_create, name='organization_list_create-no-slash'),
    path('organizations/<int:pk>/', views.organization_detail, name='organization_detail'),
    path('organizations/<int:pk>', views.organization_detail, name='organization_detail-no-slash'),
    path('organizations/<int:pk>/members/', views.organization_members, name='organization_members'),
    path('organizations/<int:pk>/members', views.organization_members, name='organization_members-no-slash'),
    path('organizations/<int:pk>/members/<int:user_id>/', views.organization_member_detail, name='organization_member_detail'),
    path('organizations/<int:pk>/members/<int:user_id>', views.organization_member_detail, name='organization_member_detail-no-slash'),

    # MFA / 2FA (Módulo 1)
    # Este login personalizado se registra ANTES que dj_rest_auth.urls en
    # nura/urls.py, así que Django lo usa para 'auth/login/' en vez del
    # login por defecto — necesario para exigir el 2º factor cuando el
    # usuario tiene MFA activado.
    path('auth/login/', views.custom_login_view, name='custom_login'),
    path('auth/login', views.custom_login_view, name='custom_login-no-slash'),
    path('auth/mfa/setup/', views.mfa_setup, name='mfa_setup'),
    path('auth/mfa/setup', views.mfa_setup, name='mfa_setup-no-slash'),
    path('auth/mfa/enable/', views.mfa_enable, name='mfa_enable'),
    path('auth/mfa/enable', views.mfa_enable, name='mfa_enable-no-slash'),
    path('auth/mfa/disable/', views.mfa_disable, name='mfa_disable'),
    path('auth/mfa/disable', views.mfa_disable, name='mfa_disable-no-slash'),
    path('auth/mfa/verify-login/', views.mfa_verify_login, name='mfa_verify_login'),
    path('auth/mfa/verify-login', views.mfa_verify_login, name='mfa_verify_login-no-slash'),

    # Dashboards armables (Módulo 4)
    path('dashboards/', views.dashboard_list_create, name='dashboard_list_create'),
    path('dashboards', views.dashboard_list_create, name='dashboard_list_create-no-slash'),
    path('dashboards/generate-ai/', views.dashboard_generate_ai, name='dashboard_generate_ai'),
    path('dashboards/generate-ai', views.dashboard_generate_ai, name='dashboard_generate_ai-no-slash'),
    path('dashboards/<int:pk>/', views.dashboard_detail, name='dashboard_detail'),
    path('dashboards/<int:pk>', views.dashboard_detail, name='dashboard_detail-no-slash'),

    # Triggers configurables (Módulo 5)
    path('triggers/', views.trigger_list_create, name='trigger_list_create'),
    path('triggers', views.trigger_list_create, name='trigger_list_create-no-slash'),
    path('triggers/check-scheduled/', views.trigger_check_scheduled, name='trigger_check_scheduled'),
    path('triggers/check-scheduled', views.trigger_check_scheduled, name='trigger_check_scheduled-no-slash'),
    path('triggers/<int:pk>/', views.trigger_detail, name='trigger_detail'),
    path('triggers/<int:pk>', views.trigger_detail, name='trigger_detail-no-slash'),

    # Compartir (Módulo 5)
    path('shares/', views.share_list, name='share_list'),
    path('shares', views.share_list, name='share_list-no-slash'),
    path('shares/create/', views.share_create, name='share_create'),
    path('shares/create', views.share_create, name='share_create-no-slash'),
    path('shares/<int:pk>/', views.share_revoke, name='share_revoke'),
    path('shares/<int:pk>', views.share_revoke, name='share_revoke-no-slash'),
    path('datasets/shared-with-me/', views.shared_datasets_list, name='shared_datasets_list'),
    path('datasets/shared-with-me', views.shared_datasets_list, name='shared_datasets_list-no-slash'),
    path('dashboards/shared-with-me/', views.shared_dashboards_list, name='shared_dashboards_list'),
    path('dashboards/shared-with-me', views.shared_dashboards_list, name='shared_dashboards_list-no-slash'),

    # Comentarios (Módulo 5)
    path('comments/', views.comment_list_create, name='comment_list_create'),
    path('comments', views.comment_list_create, name='comment_list_create-no-slash'),
    path('comments/<int:pk>/', views.comment_delete, name='comment_delete'),
    path('comments/<int:pk>', views.comment_delete, name='comment_delete-no-slash'),

    # Agentes por área de negocio (Módulo 6)
    path('agents/by-area/', views.agents_by_area, name='agents_by_area'),
    path('agents/by-area', views.agents_by_area, name='agents_by_area-no-slash'),

    # Recomendaciones proactivas (Módulo 6)
    path('recommendations/', views.recommendation_list, name='recommendation_list'),
    path('recommendations', views.recommendation_list, name='recommendation_list-no-slash'),
    path('recommendations/<int:pk>/dismiss/', views.recommendation_dismiss, name='recommendation_dismiss'),
    path('recommendations/<int:pk>/dismiss', views.recommendation_dismiss, name='recommendation_dismiss-no-slash'),
    path('datasets/<int:pk>/generate-recommendations/', views.dataset_generate_recommendations, name='dataset_generate_recommendations'),
    path('datasets/<int:pk>/generate-recommendations', views.dataset_generate_recommendations, name='dataset_generate_recommendations-no-slash'),
]
