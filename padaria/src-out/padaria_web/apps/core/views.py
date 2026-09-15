from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Categoria, Produto, LoteProducao, Venda, ItemVenda
from .forms import CategoriaForm, ProdutoForm, LoteProducaoForm, VendaForm
from .services import criar_lote_producao, adicionar_item_venda, processar_pagamento, cancelar_venda

def pdv_list(request):
    """Página principal do PDV"""
    vendas = Venda.objects.filter(status='EM_ABERTO').order_by('-data_hora')
    
    context = {
        'vendas': vendas
    }
    
    return render(request, 'pdv/list.html', context)

def produto_list(request):
    """Lista todos os produtos"""
    produtos = Produto.objects.select_related('categoria').all()
    
    context = {
        'produtos': produtos
    }
    
    return render(request, 'produtos/list.html', context)

def lote_list(request):
    """Lista todos os lotes de produção"""
    lotes = LoteProducao.objects.select_related('produto__categoria').all()
    
    context = {
        'lotes': lotes
    }
    
    return render(request, 'lotes/list.html', context)

def produto_create(request):
    """Cria um novo produto"""
    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto criado com sucesso!')
            return redirect('produto_list')
    else:
        form = ProdutoForm()
    
    context = {
        'form': form,
        'title': 'Novo Produto'
    }
    
    return render(request, 'produtos/create.html', context)

def lote_create(request):
    """Cria um novo lote de produção"""
    if request.method == 'POST':
        form = LoteProducaoForm(request.POST)
        if form.is_valid():
            produto_id = form.cleaned_data['produto'].id
            quantidade = form.cleaned_data['quantidade']
            
            success, result = criar_lote_producao(produto_id, quantidade)
            
            if success:
                messages.success(request, 'Lote de produção criado com sucesso!')
                return redirect('lote_list')
            else:
                messages.error(request, result)
    else:
        form = LoteProducaoForm()
    
    context = {
        'form': form,
        'title': 'Novo Lote de Produção'
    }
    
    return render(request, 'lotes/create.html', context)

def venda_create(request):
    """Cria uma nova venda"""
    if request.method == 'POST':
        form = VendaForm(request.POST)
        if form.is_valid():
            venda = form.save()
            messages.success(request, 'Nova venda criada!')
            return redirect('pdv_list')
    else:
        form = VendaForm()
    
    context = {
        'form': form,
        'title': 'Nova Venda'
    }
    
    return render(request, 'vendas/create.html', context)

def venda_detail(request, venda_id):
    """Detalhes da venda"""
    venda = get_object_or_404(Venda, id=venda_id)
    itens = ItemVenda.objects.filter(venda=venda).select_related('produto')
    
    if request.method == 'POST':
        # Adicionar item à venda
        produto_id = int(request.POST.get('produto'))
        quantidade = float(request.POST.get('quantidade'))
        
        success, message = adicionar_item_venda(venda.id, produto_id, quantidade)
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
            
        return redirect('venda_detail', venda_id=venda.id)
    
    context = {
        'venda': venda,
        'itens': itens
    }
    
    return render(request, 'vendas/detail.html', context)

def produto_detail(request, produto_id):
    """Detalhes do produto"""
    produto = get_object_or_404(Produto, id=produto_id)
    
    context = {
        'produto': produto
    }
    
    return render(request, 'produtos/detail.html', context)

def checkout_venda(request, venda_id):
    """Processa o pagamento da venda"""
    if request.method == 'POST':
        success, message = processar_pagamento(venda_id)
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
            
        return redirect('pdv_list')

def cancelar_venda_view(request, venda_id):
    """Cancela uma venda"""
    if request.method == 'POST':
        success, message = cancelar_venda(venda_id)
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
            
        return redirect('pdv_list')

