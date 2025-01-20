from rest_framework.routers import DefaultRouter
from django.urls import include, path
from .views import (
    CustomUserViewSet,
    RecipesViewSet,
    TagViewSet,
    IngredientViewSet,
)

router = DefaultRouter()
router.register(r'users', CustomUserViewSet)
router.register(r'recipes', RecipesViewSet)
router.register(r'tags', TagViewSet)
router.register(r'ingredients', IngredientViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
