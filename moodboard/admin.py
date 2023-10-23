from django.contrib import admin
from .models import Moodboard, Image

@admin.register(Moodboard)
class MoodboardAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'tags', 'manufacturer', 'model_number', 'stock_id', 'listed', 'created_at', 'updated_at', 'listed_at')  # Columns to display in admin
    search_fields = ('title', 'user', 'tags', 'manufacturer', 'model_number', 'stock_id', 'listed', 'created_at', 'updated_at', 'listed_at')  # Searchable fields
    list_filter = ('user', 'tags')  # Fields to filter by

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('moodboard', 'pk')  # Columns to display in admin
    search_fields = ('moodboard__title',)  # Searchable fields
    list_filter = ('moodboard',)  # Fields to filter by
