import base64
import hashlib
from collections import defaultdict
from django.db.models import Count, Sum
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.permissions import SAFE_METHODS
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from recipes.models import (User, Ingredient, Tag,
                            Recipes, IngredientAmount, ShoppingList,
                            Follower, Favorite)
from api.serializers import (UserSerializer, RecipesInfoSerializer,
                             ShoppingListSerializer, FollowerSerializer,
                             PasswordSerializer, AvatarSerializer,
                             TagSerializer, IngredientSerializer,
                             RecipesAddSerializer, IngredientRecipeSerializer,
                             FavoriteSerializer)
from api.permissions import AuthorOrReadOnly, IsAdminOrReadOnly
from .filters import RecipesFilter
from .pagination import CustomPagination


short_links_storage = {}


class CustomUserViewSet(viewsets.ModelViewSet):
    """Вьюсет для модели User."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = CustomPagination

    def get_permissions(self):
        if self.action in ['create', 'retrieve']:
            return [permissions.AllowAny()]
        return [IsAuthenticatedOrReadOnly()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
        except Exception as e:
            return Response(
                {'ERROR': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['GET'], url_path='subscriptions')
    def subscriptions(self, request):
        user = request.user
        subscribed_users = (
            Follower.objects
            .filter(user=user)
            .select_related('author')
            .order_by('id')
        )
        print(f"Общее количество подписок: {subscribed_users.count()}")
        page = self.paginate_queryset(subscribed_users)
        if page is not None:
            print(f"Количество подписок на текущей странице: {len(page)}")
            serializer = FollowerSerializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = FollowerSerializer(
            subscribed_users,
            many=True,
            context={'request': request}
        )
        return Response({"results": serializer.data})

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=[IsAuthenticated],
        url_path='subscribe'
    )
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)
        user = request.user
        if user == author:
            return Response(
                {'status': 'Нельзя подписаться на самого себя!'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == 'POST':
            follower, created = Follower.objects.get_or_create(
                user=user,
                author=author
            )
            if created:
                return Response(
                    UserSerializer(author).data,
                    status=status.HTTP_204_NO_CONTENT
                )
            return Response(
                {'status': 'Уже подписан!'},
                status=status.HTTP_400_BAD_REQUEST
            )

        elif request.method == 'DELETE':
            # Обработка отписки
            subscription = Follower.objects.filter(
                user=user,
                author=author
            ).first()
            if subscription:
                subscription.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {'status': 'не подписан'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(
        methods=['GET', 'PATCH'],
        detail=False,
        url_path='me',
        permission_classes=[permissions.IsAuthenticated]
    )
    def me(self, request):
        """Изменение данных пользователя."""
        if request.method == 'GET':
            return Response(
                self.get_serializer(request.user).data,
                status=status.HTTP_200_OK
            )
        if request.method == 'PATCH':
            serializer = self.get_serializer(
                request.user,
                data=request.data,
                partial=True,
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(
        methods=['PUT', 'DELETE'],
        detail=False,
        url_path='me/avatar',
        permission_classes=[permissions.IsAuthenticated]
    )
    def avatar(self, request):
        """Добавление, изменение и удаление аватара."""
        user = request.user
        if request.method == 'PUT':
            serializer = AvatarSerializer(instance=user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {'status': 'аватар загружен'},
                status=status.HTTP_200_OK
            )
        elif request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete(save=False)
                user.avatar = None
                user.save()
                return Response(
                    {'status': 'аватар удален'},
                    status=status.HTTP_204_NO_CONTENT
                )
            return Response(
                {'status': 'аватара нет, удалять нечего'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    # Ставим detail=False, чтобы метод не требовал id
    @action(
        detail=False,
        methods=['POST'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def set_password(self, request):
        # Получаем текущего пользователя на прямую из запроса, меняем пароль
        user = request.user
        serializer = PasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TagViewSet(viewsets.ModelViewSet):
    """Вьюсет для модели тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminOrReadOnly]


class IngredientViewSet(viewsets.ModelViewSet):
    """Вьюсет для модели ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAdminOrReadOnly]


class FavoritesView(APIView):
    def get(self, request):
        user = request.user
        if user.is_anonymous:
            return Response({"detail": "Unauthorized"}, status=401)

        favorites = user.favorites.all()
        serializer = FavoriteSerializer(favorites, many=True)
        return Response(serializer.data)


class RecipesViewSet(viewsets.ModelViewSet):
    """Вьюсет для модели рецептов."""

    queryset = Recipes.objects.all()
    permission_classes = [AuthorOrReadOnly]
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipesFilter

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipesInfoSerializer
        return RecipesAddSerializer

    def get_ingredients(self, recipe_instance):
        ingredient_amounts = IngredientAmount.objects.filter(
            recipe=recipe_instance
        ).select_related('ingredient')
        print(ingredient_amounts)
        return IngredientRecipeSerializer(ingredient_amounts, many=True).data

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        print(f"Request GET parameters: {self.request.GET}")
        queryset = super().get_queryset()
        request = self.request
        author_id = request.query_params.get('author')
        if author_id:
            queryset = queryset.filter(author_id=author_id)
        if request.user.is_authenticated:
            if request.query_params.get('is_favorited'):
                # Фильтрация по избранным рецептам
                queryset = queryset.filter(
                    favorites__author=request.user
                ).distinct()
        tag_slugs = request.query_params.getlist('tags')
        if tag_slugs:
            queryset = (
                queryset
                .filter(tags__slug__in=tag_slugs)
                .annotate(num_tags=Count('tags'))
                .filter(num_tags=len(tag_slugs))
                .distinct()
            )
        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            context={'request': request}
        )
        data = serializer.data
        data['ingredients'] = self.get_ingredients(instance)
        return Response(data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk):
        """Добавить или удалить рецепт из избранного."""
        recipe = get_object_or_404(Recipes, pk=pk)
        if request.method == 'POST':
            favorite, created = Favorite.objects.get_or_create(
                author=request.user,
                recipe=recipe
            )
            if created:
                return Response(
                    {'message': 'Рецепт добавлен в избранное.'},
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {'message': 'Рецепт уже в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif request.method == 'DELETE':
            try:
                favorite = Favorite.objects.get(
                    author=request.user,
                    recipe=recipe
                )
                favorite.delete()
                return Response(
                    {'message': 'Рецепт удален из избранного.'},
                    status=status.HTTP_204_NO_CONTENT
                )
            except Favorite.DoesNotExist:
                return Response(
                    {'message': 'Рецепт не найден в избранном.'},
                    status=status.HTTP_404_NOT_FOUND
                )

    def create(self, request, *args, **kwargs):
        serializer = RecipesAddSerializer(
            data=request.data,
            context={'request': request}
        )
        if not serializer.is_valid():
            print("Ошибки валидации:", serializer.errors)
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer.is_valid(raise_exception=True)
        # Создание рецепта
        recipe = serializer.save(author=request.user)
        # Возвращаем созданный рецепт
        return Response(
            RecipesInfoSerializer(recipe).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None, partial=False):
        """Редактирование рецепта."""

        recipe = get_object_or_404(Recipes, pk=pk)
        if recipe.author != request.user:
            return Response(
                {'detail': 'У вас нет прав для редактирования этого рецепта.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = RecipesAddSerializer(
            recipe,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            RecipesInfoSerializer(recipe).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['GET'], url_path='get-link')
    def short_link(self, request, pk=None):
        recipes = get_object_or_404(Recipes, pk=pk)
        short_link = self.generate_short_link(recipes.pk)
        short_links_storage[short_link] = recipes.pk
        short_url = request.build_absolute_uri(
            f"/api/recipes/redirect/{short_link}/"
        )
        return Response({'short-link': short_url}, status=status.HTTP_200_OK)

    def generate_short_link(self, id):
        hash_object = hashlib.md5(str(id).encode())
        # Кодируем в base64
        short_link = base64.urlsafe_b64encode(hash_object.digest()).decode()
        # Убираем символы '=' и обрезаем до 4 символов
        short_link = short_link.rstrip('=')[:4]
        return short_link

    @action(
        detail=False,
        methods=['GET'],
        url_path='redirect/(?P<short_link>[a-zA-Z0-9_-]+)'
    )
    def redirect_short_link(self, request, short_link):
        try:
            original_id = self.decode_short_link(short_link)
            # Построение полного URL на основе текущего запроса
            return HttpResponseRedirect(
                request.build_absolute_uri(f'/recipes/{original_id}/')
            )
        except Exception:
            return Response(
                {"ERROR": "Неверный формат короткой ссылки."},
                status=status.HTTP_400_BAD_REQUEST
            )

    def decode_short_link(self, short_link):
        if short_link in short_links_storage:
            return short_links_storage[short_link]
        else:
            raise ValueError("Короткая ссылка не найдена")

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk):
        if request.method == 'POST':
            return self.add_to_shopping_cart(request.user, pk)
        else:
            return self.delete_shopping_cart(request.user, pk)

    def add_to_shopping_cart(self, user, id):
        # Проверка, существует ли рецепт
        try:
            recipe = Recipes.objects.get(id=id)
        except Recipes.DoesNotExist:
            return Response(
                {'detail': 'Рецепт не найден.'},
                status=status.HTTP_404_NOT_FOUND
            )
        # Проверка, существует ли уже запись в списке покупок
        if ShoppingList.objects.filter(author=user, recipe=recipe).exists():
            return Response(
                {'detail': 'Рецепт уже добавлен в список покупок.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Создание нового объекта ShoppingList
        shopping_list_item = ShoppingList(author=user, recipe=recipe)
        shopping_list_item.save()
        # Сериализация созданного объекта для ответа
        serializer = ShoppingListSerializer(shopping_list_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_shopping_cart(self, user, id):
        delete_cart = ShoppingList.objects.filter(author=user, recipe__id=id)
        if delete_cart.exists():
            delete_cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'ERROR': 'Рецепт уже удален или не найден!'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=True,
        url_path='shopping_cart',
        permission_classes=[IsAuthenticated]
    )
    def get_shopping_cart(self, request):
        get_shopping_cart = request.user.shopping_cart.all()
        return Response({'recipes': get_shopping_cart})

    @action(detail=False, permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        shopping_cart_recipes = request.user.shopping_cart.values_list(
            'recipe_id',
            flat=True
        )
        ingredients = (
            IngredientAmount.objects
            .filter(recipe_id__in=shopping_cart_recipes)
            .select_related('ingredient')
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(total_amount=Sum('amount'))
        )

        if not ingredients.exists():
            return Response(
                {'ERROR': 'Ингредиент не найден!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        ingredient_summary = defaultdict(int)

        for ingredient in ingredients:
            name = ingredient['ingredient__name']
            total_amount = ingredient['total_amount']
            unit = ingredient['ingredient__measurement_unit']
            ingredient_summary[(name, unit)] += total_amount
        text = 'Список покупок:\n\n'

        for number, ((name, unit), total_amount) in enumerate(
            ingredient_summary.items(), start=1
        ):
            text += f"{number}) {name} - {total_amount} {unit}\n"

        response = HttpResponse(text, content_type='text/plain')
        filename = 'shopping_list.txt'
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response
