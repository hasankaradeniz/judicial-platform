# faiss_query/urls.py

from django.urls import path
from . import views

app_name = 'faiss_query'

urlpatterns = [
    path('', views.olay_gir, name='olay_gir'),
    path('karar_listesi/', views.karar_listesi, name='karar_listesi'),
    path('detay/<str:alan>/<int:index>/', views.karar_detay, name='karar_detay'),
]
