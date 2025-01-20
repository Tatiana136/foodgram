from django_filters import rest_framework as filters
from recipes.models import Recipes, Tag


class TagFilter(filters.FilterSet):
    """Фильтр для управления тегами рецептов."""

    tags = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name='tags__slug',
        to_field_name='slug',
        label='Теги'
    )

    class Meta:
        model = Recipes
        fields = ('tags',)

class RecipesFilter(filters.FilterSet):
    """Фильтр для управления рецептами с возможностью фильтрации по тегам и другим параметрам."""

    tags = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name='tags__slug',
        to_field_name='slug',
        label='Теги'
    )
    
    is_favorited = filters.BooleanFilter(method='filter_favorites', label='Избранное')
    is_in_shopping_cart = filters.BooleanFilter(method='filter_cart', label='В корзине')

    class Meta:
        model = Recipes
        fields = ('tags', 'author', 'is_favorited', 'is_in_shopping_cart')

    def filter_favorites(self, queryset, name, value):
        """Фильтрует рецепты, добавленные в избранное пользователем."""
        if value:
            return queryset.filter(favorites__user=self.request.user)
        return queryset

    def filter_cart(self, queryset, name, value):
        """Фильтрует рецепты, находящиеся в корзине пользователя."""
        if value:
            return queryset.filter(shopping_cart__author=self.request.user)
        return queryset
