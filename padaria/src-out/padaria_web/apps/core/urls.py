from django.urls import path
from . import views

urlpatterns = [
    # Páginas principais
    path('', views.pdv_list, name='pdv_list'),
    path('produtos/', views.produto_list, name='produto_list'),
    path('lotes/', views.lote_list, name='lote_list'),
    
    # Formulários
    path('produtos/novo/', views.produto_create, name='produto_create'),
    path('lotes/novo/', views.lote_create, name='lote_create'),
    path('vendas/nova/', views.venda_create, name='venda_create'),
    
    # Detalhes
    path('vendas/<int:venda_id>/', views.venda_detail, name='venda_detail'),
    path('produtos/<int:produto_id>/', views.produto_detail, name='produto_detail'),
]
