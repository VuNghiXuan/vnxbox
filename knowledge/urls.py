from rest_framework.routers import DefaultRouter
from .views import KnowledgeChapterViewSet

router = DefaultRouter()
router.register(r'chapters', KnowledgeChapterViewSet, basename='knowledge-chapter')

urlpatterns = router.urls