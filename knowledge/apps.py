from django.apps import AppConfig


class KnowledgeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'knowledge'

    def ready(self):
        # Import file signals để Django đăng ký các sự kiện post_save / pre_delete
        import knowledge.signals