import re
from django.contrib.auth import authenticate
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField
from rest_framework.exceptions import ValidationError
from rest_framework.fields import IntegerField, SerializerMethodField
from recipes.models import (User, Ingredient, Tag,
                            Recipes, IngredientAmount,
                            ShoppingList, Follower, Favorite)


class CustomAuthTokenSerializer(serializers.Serializer):
    email = serializers.EmailField(label='Email')
    password = serializers.CharField(
        label='password',
        trim_whitespace=False
    )

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'),
                                email=email, password=password)
            if not user:
                raise serializers.ValidationError(
                    'Невозможно войти в систему с предоставленными данными.'
                )
        else:
            raise serializers.ValidationError('Должны быть email и пароль.')
        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.BooleanField(required=False)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
            'password',
        )
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate_username(self, value):
        if not re.match(r'^[\w.@+-]+$', value):
            raise serializers.ValidationError(
                'Неверный формат имени пользователя.'
            )
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                'Это имя пользователя уже занято.'
            )
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'Этот адрес электронной почты уже занят.'
            )
        return value

    def create(self, validated_data):
        print("Создание пользователя с данными:", validated_data)
        # Пароль не должен храниться в обычном виде.
        # Поэтому сначала извлекаем пароль из validated_data
        # и удаляем его из словаря, потом передаем данные без пароля.
        password = validated_data.pop('password')
        user = super().create(validated_data)
        # Устанавливаем пароль с помощью метода set_password,
        # который преобразует его в хеш.
        user.set_password(password)
        user.save()
        return user

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.avatar:
            representation['avatar'] = instance.avatar.url
        else:
            representation['avatar'] = None  # Если аватар отсутствует
        representation['is_subscribed'] = self.get_is_subscribed(instance)
        return representation

    def get_is_subscribed(self, instance):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follower.objects.filter(
                user=request.user,
                author=instance
            ).exists()
        return False


class PasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Текущий пароль неверный.')
        return value

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(
                'Новый пароль должен содержать не менее 8 символов.'
            )
        return value


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ['avatar']

    def update(self, instance, validated_data):
        instance.avatar = validated_data.get('avatar', instance.avatar)
        instance.save()
        return instance


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class IngredientRecipeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=True)
    amount = serializers.IntegerField(required=True)
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )

    class Meta:
        model = IngredientAmount
        fields = ['id', 'amount', 'name', 'measurement_unit']


class CompactRecipesInfoSerializer(serializers.ModelSerializer):
    """Сериализатор для компактного представления данных о рецептах."""

    ingredients = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipes
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
        )

    def get_ingredients(self, recipe_instance):
        ingredient_amounts = IngredientAmount.objects.filter(
            recipe=recipe_instance
        ).select_related('ingredient')
        return [
            {
                'id': ia.ingredient.id,
                'amount': ia.amount,
                'measurement_unit': ia.ingredient.measurement_unit
            }
            for ia in ingredient_amounts
        ]

    def get_tags(self, recipe_instance):
        return [tag.id for tag in recipe_instance.tags.all()]


class RecipesInfoSerializer(serializers.ModelSerializer):
    """Представление данных о рецептах."""

    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = serializers.SerializerMethodField()
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Recipes
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_ingredients(self, recipe_instance):
        ingredient_amounts = IngredientAmount.objects.filter(
            recipe=recipe_instance
        ).select_related('ingredient')
        return [
            {
                'id': ia.ingredient.id,
                'amount': ia.amount,
                'measurement_unit': ia.ingredient.measurement_unit,
                'name': ia.ingredient.name
            }
            for ia in ingredient_amounts
        ]

    def get_tags(self, recipe_instance):
        return [
            {
                'id': tag.id,
                'name': tag.name
            }
            for tag in recipe_instance.tags.all()
        ]

    def get_list(self, recipe_instance, list_name):
        # Добавлен ли рецепт в избранное или корзину пользователя
        request = self.context.get('request')
        if request is None:
            return False

        user = request.user
        if user.is_anonymous:
            return False
        if list_name == 'favorites':
            return user.favorites.filter(recipe=recipe_instance).exists()
        elif list_name == 'shopping_cart':
            return user.shopping_cart.filter(recipe=recipe_instance).exists()
        return False

    def get_is_favorited(self, recipe_instance):
        # Избранное
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        is_favorited = request.user.favorites.filter(
            recipe=recipe_instance
        ).exists()
        return is_favorited

    def get_is_in_shopping_cart(self, recipe_instance):
        # Корзина
        return self.get_list(recipe_instance, 'shopping_cart')


class RecipesAddSerializer(serializers.ModelSerializer):
    """Сериализатор для создания новых рецептов."""

    tags = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )
    author = UserSerializer(read_only=True)
    ingredients = IngredientRecipeSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipes
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def validate_ingredients(self, value):
        for ingredient in value:
            if 'id' not in ingredient:
                raise serializers.ValidationError(
                    'Каждый ингредиент должен содержать id.'
                )
            if 'amount' not in ingredient:
                raise serializers.ValidationError(
                    'Каждый ингредиент должен содержать amount.'
                )
        return value

    @transaction.atomic
    def _add_ingredients(self, ingredients, recipe):
        if not ingredients:
            raise ValidationError({
                'ingredients': 'Нужен хотя бы один ингредиент!'
            })

        ingredient_objects = []

        for item in ingredients:
            ingredient = get_object_or_404(Ingredient, id=item['id'])
            amount = item['amount']
            ingredient_objects.append(IngredientAmount(
                recipe=recipe,
                ingredient=ingredient,
                amount=amount
            ))
        IngredientAmount.objects.bulk_create(ingredient_objects)

    def _add_tags(self, recipe, tags_data):
        """Добавляет теги к рецепту."""
        existing_tags = Tag.objects.filter(id__in=tags_data)
        recipe.tags.set(existing_tags)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            raise ValidationError('Пользователь не авторизован.')
        validated_data['author'] = request.user
        recipe = Recipes.objects.create(**validated_data)
        self._add_ingredients(ingredients_data, recipe)
        self._add_tags(recipe, tags_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients', None)
        tags = validated_data.pop('tags', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if ingredients is not None:
            self._update_ingredients(ingredients, instance)
        if tags is not None:
            self._update_tags(instance, tags)
        return RecipesInfoSerializer(instance).data

    def _update_ingredients(self, ingredients_data, recipe):
        recipe.ingredients.clear()
        self._add_ingredients(ingredients_data, recipe)

    def _update_tags(self, recipe, tags_data):
        recipe.tags.clear()
        self._add_tags(recipe, tags_data)


class RecipesFoFollowerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipes
        fields = ['id', 'name', 'image', 'cooking_time']


class FollowerSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='author.recipes.count',
        default=0
    )
    avatar = serializers.ImageField(source='author.avatar', default=None)
    email = serializers.EmailField(source='author.email')
    id = serializers.IntegerField(source='author.id')
    username = serializers.CharField(source='author.username')
    first_name = serializers.CharField(source='author.first_name')
    last_name = serializers.CharField(source='author.last_name')
    is_subscribed = serializers.BooleanField(default=True)

    class Meta:
        model = Follower
        fields = [
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar']

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit', None)
        recipes_queryset = obj.author.recipes.all()

        # Если задан лимит, обрезаем queryset
        if recipes_limit is not None:
            try:
                recipes_limit = int(recipes_limit)
                recipes_queryset = recipes_queryset[:recipes_limit]
            except ValueError:
                pass

        return RecipesFoFollowerSerializer(recipes_queryset, many=True).data


class ShoppingListSerializer(serializers.ModelSerializer):
    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipes.objects.all())

    class Meta:
        model = ShoppingList
        fields = ['id', 'recipe']
