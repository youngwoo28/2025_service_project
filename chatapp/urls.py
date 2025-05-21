from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('summary/', views.summary, name='summary'),
    path('journal/', views.journal_list, name='journal_list'),  # 🔹 감정일지 목록
    path('journal/<str:date>/', views.journal_detail, name='journal_detail'),  # 🔹 날짜별 상세
]
