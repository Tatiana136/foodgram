from django.contrib import admin
from recipes.models import (Ingredient, Tag,
                    Recipes, IngredientAmount, ShoppingList,
                    Follower, Favorite, User)


class UserAdmin(admin.ModelAdmin):
    """Админка для пользователей"""

    list_display = ('first_name', 'last_name', 'email', 'username', 'role')
    search_fields = ('first_name', 'email',)
    empty_value_display = '-пусто-'


class IngredientAdmin(admin.ModelAdmin):
    """Админка для ингредиентов"""

    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('name',)
    empty_value_display = '-пусто-'


class TagAdmin(admin.ModelAdmin):
    """Админка для тегов."""

    list_display = ('id', 'name', 'slug', )
    search_fields = ('name',)
    list_filter = ('name',)
    empty_value_display = '-пусто-'


class IngredientAmountAdmin(admin.ModelAdmin):
    """Админка для ингредиентов рецептов."""

    list_display = ('id', 'ingredient', 'recipe', 'amount',)
    search_fields = ('name',)
    list_filter = ('ingredient', 'recipe',)
    empty_value_display = '-пусто-'


class RecipesAdmin(admin.ModelAdmin):
    """Админка для рецептов."""

    list_display = ('id', 'name', 'author', 'favorite_count',)
    search_fields = ('author', 'name',)
    list_filter = ('tags',)
    empty_value_display = '-пусто-'

    def favorite_count(self, obj):
        return Favorite.objects.filter(recipe=obj).count()

    favorite_count.short_description = 'Количество добавлений в избранное'


class ShoppingListAdmin(admin.ModelAdmin):
    """Админка для покупок."""

    list_display = ('author', 'recipe',)
    search_fields = ('author',)
    list_filter = ('author',)
    empty_value_display = '-пусто-'


class FollowerAdmin(admin.ModelAdmin):
    """Админка для подписок."""

    list_display = ('user', 'author',)
    search_fields = ('user',)
    list_filter = ('author',)


class FavoriteAdmin(admin.ModelAdmin):
    """Админка для избранного."""

    list_display = ('author', 'recipe',)
    search_fields = ('author',)
    list_filter = ('author',)


admin.site.register(User, UserAdmin)
admin.site.register(Recipes, RecipesAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(IngredientAmount, IngredientAmountAdmin)
admin.site.register(ShoppingList, ShoppingListAdmin)
admin.site.register(Follower, FollowerAdmin)
admin.site.register(Favorite, FavoriteAdmin)
