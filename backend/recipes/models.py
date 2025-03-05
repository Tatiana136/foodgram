from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import AbstractUser
from django.conf import settings


MAX = 150


class UserRole:
    """Модель пользователя."""

    USER = 'user'
    ADMIN = 'admin'

    CHOICES = [
        (USER, 'Пользователь'),
        (ADMIN, 'Администратор'),
    ]


class User(AbstractUser):
    """Кастомизированная модель пользователя."""

    email = models.EmailField(
        verbose_name='Адрес электронной почты',
        max_length=254,
        unique=True,)
    username = models.CharField(
        verbose_name='Имя пользователя',
        max_length=MAX,
        null=True,
        unique=True)
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=MAX,
        blank=True,)
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=MAX,
        blank=True,)
    role = models.CharField(
        verbose_name='Роль',
        max_length=20,
        choices=UserRole.CHOICES,
        default=UserRole.USER,)
    password = models.CharField(
        max_length=MAX,
        verbose_name='Пароль')
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True)
    is_subscribed = models.BooleanField(
        default=False,
        help_text='Подписан ли текущий пользователь на этого')
    groups = None
    user_permissions = None
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:

        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    @property
    def admin(self):
        return self.role == UserRole.ADMIN

    def __str__(self):
        return self.email


class Ingredient(models.Model):
    """Модель для ингридиентов."""

    name = models.CharField(
        verbose_name='Назание продукта',
        max_length=100,
        help_text='Введите название ингридиента',
        db_index=True)
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=30,
        help_text='Введите единицу измерения',
        db_index=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Tag(models.Model):
    """Модел для тегов."""

    name = models.CharField(
        verbose_name='Назание тега',
        max_length=32,
        help_text='Введите название тега')
    slug = models.SlugField(
        verbose_name='Slug',
        max_length=32,
        help_text='Укажите уникальный слаг')

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'slug'],
                name='unique_name_slug')]

    def __str__(self):
        return self.name


class Recipes(models.Model):
    """Модель для рецептов."""

    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientAmount',
        related_name='recipes')
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        help_text='Выберите тег')
    image = models.ImageField(
        upload_to='media/',
        help_text='Добавьте изображение')
    name = models.CharField(
        verbose_name='Название рецепта',
        max_length=256,
        help_text='Введите название рецепта',
        db_index=True)
    text = models.TextField(
        verbose_name='Описание рецепта',
        help_text='Распишите поэтапно рецепт')
    cooking_time = models.IntegerField(
        verbose_name='Время',
        validators=[MinValueValidator(1)],
        help_text='Впишите время приготовления (в минутах)')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recipes',
        help_text='Автор рецепта')

    class Meta:
        ordering = ['-id']
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'author'],
                name='unique_name_author')]
    
    def __str__(self):
        return self.name


class IngredientAmount(models.Model):
    """
    Ингредиенты для рецепта.
    Промежуточная таблица Ingredient и Recipes.
    Один рецепт содержит много ингредиентов,
    один ингредиент используется во многих рецептах.
    """

    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
        help_text='Выберите ингредиент')
    recipe = models.ForeignKey(
        Recipes,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        help_text='Выберите рецепт')
    amount = models.PositiveIntegerField(
        verbose_name='Количество',
        validators=[MinValueValidator(1)],
        help_text='Введите количество ингредиента')

    class Meta:
        verbose_name = 'Количество ингредиента'
        verbose_name_plural = 'Количество ингредиентов'
        constraints = [
            models.UniqueConstraint(
                fields=['ingredient', 'recipe'],
                name='unique_ingredient_recipe')]

    def __str__(self):
        return f'{self.ingredient} {self.amount} для {self.recipe.name}'


class ShoppingList(models.Model):
    """Модель списка покупок."""

    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='shopping_cart')
    recipe = models.ForeignKey(
        Recipes,
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        help_text='Выберите рецепт')

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'
        constraints = [
            models.UniqueConstraint(
                fields=['author', 'recipe'],
                name='unique_shoppinglist')]

    def __str__(self):
        return f'{self.recipe}'


class Follower(models.Model):
    """Модель для подписок."""

    user = models.ForeignKey(
        User,
        verbose_name='Подписчик',
        on_delete=models.CASCADE,
        related_name='subscriber')
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='subscribing',
        null=False)

    class Meta:
        verbose_name = 'Мои подписки'
        verbose_name_plural = 'Мои подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_following')]

    def __str__(self):
        return f'{self.user} подписан на {self.author}'


class Favorite(models.Model):
    """Модель дял списка избранного."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор рецепта',
        related_name='favorites')
    recipe = models.ForeignKey(
        Recipes,
        on_delete=models.CASCADE,
        related_name='favorites')

    class Meta:
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        constraints = [
            models.UniqueConstraint(
                fields=['author', 'recipe'],
                name='unique_favorite')]

    def __str__(self):
        return f'{self.recipe}'
