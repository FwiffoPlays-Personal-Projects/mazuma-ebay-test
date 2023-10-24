from django.urls import path, include
from django.conf.urls import handler404, handler403, handler500
from . import views

app_name = "moodboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("create/", views.create_moodboard, name="create_moodboard"),
    path("detail/<int:pk>/", views.detail, name="detail"),
    path("edit/<int:moodboard_id>/",
         views.edit_moodboard,
         name="edit_moodboard"),
    path("delete/<int:pk>/", views.delete_moodboard, name="delete_moodboard"),
    path('download_all_images/<int:moodboard_id>/', views.download_all_images, name='download_all_images'),
    path('toggle_listed/<int:moodboard_id>/', views.toggle_listed, name='toggle_listed'),
    path('listed/', views.listed_items, name='listed_items'),
    path('not-listed/', views.not_listed_items, name='not_listed_items'),
]