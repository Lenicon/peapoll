from django.urls import path

from . import views

app_name = 'polls'

urlpatterns = [
    path('', views.poll_list, name='list'),
    path('mine/', views.my_polls, name='mine'),
    path('new/', views.poll_create, name='create'),
    path('<int:pk>/', views.poll_detail, name='detail'),
    path('<int:pk>/vote/', views.poll_vote, name='vote'),
    path('<int:pk>/toggle/', views.poll_toggle, name='toggle'),
    path('<int:pk>/delete/', views.poll_delete, name='delete'),
]
