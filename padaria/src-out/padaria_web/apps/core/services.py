from decimal import Decimal
from django.db import transaction
from .models import Produto, LoteProducao, Venda, ItemVenda


def atualizar_estoque_lote(lote_id):
    """Atualiza o estoque do produto após alteração no lote"""
    with transaction.atomic():
        try:
            lote = LoteProducao.objects.select_for_update().get(id=lote_id)
            
            if lote.status == 'PRONTO':
                produto = lote.produto
                produto.estoque_atual += lote.quantidade
                produto.save(update_fields=['estoque_atual'])
                
            return True
        except LoteProducao.DoesNotExist:
            return False


def adicionar_item_venda(venda_id, produto_id, quantidade):
    """Adiciona um item à venda"""
    with transaction.atomic():
        try:
            venda = Venda.objects.select_for_update().get(id=venda_id)
            produto = Produto.objects.select_for_update().get(id=produto_id)
            
            # Verifica se há estoque suficiente
            if produto.estoque_atual < quantidade:
                return False, "Estoque insuficiente"
            
            # Calcula o preço total do item
            preco_total = produto.preco * quantidade
            
            # Cria o item de venda
            item = ItemVenda.objects.create(
                venda=venda,
                produto=produto,
                quantidade=quantidade,
                preco_unitario=produto.preco
            )
            
            # Atualiza o estoque do produto
            produto.estoque_atual -= quantidade
            produto.save(update_fields=['estoque_atual'])
            
            # Atualiza o valor total da venda
            venda.valor_total += preco_total
            venda.save(update_fields=['valor_total'])
            
            return True, "Item adicionado com sucesso"
        except (Venda.DoesNotExist, Produto.DoesNotExist) as e:
            return False, f"Erro ao adicionar item: {str(e)}"


def processar_pagamento(venda_id):
    """Finaliza uma venda e marca como concluída"""
    with transaction.atomic():
        try:
            venda = Venda.objects.select_for_update().get(id=venda_id)
            
            if venda.status != 'EM_ABERTO':
                return False, "Venda já está finalizada ou cancelada"
            
            venda.status = 'CONCLUIDA'
            venda.save(update_fields=['status'])
            
            return True, "Pagamento processado com sucesso"
        except Venda.DoesNotExist:
            return False, "Venda não encontrada"


def cancelar_venda(venda_id):
    """Cancela uma venda e reestabelece o estoque"""
    with transaction.atomic():
        try:
            venda = Venda.objects.select_for_update().get(id=venda_id)
            
            if venda.status == 'CANCELADA':
                return False, "Venda já está cancelada"
            
            if venda.status == 'CONCLUIDA':
                # Reestabelece o estoque dos produtos vendidos
                for item in ItemVenda.objects.filter(venda=venda):
                    produto = item.produto
                    produto.estoque_atual += item.quantidade
                    produto.save(update_fields=['estoque_atual'])
            
            venda.status = 'CANCELADA'
            venda.save(update_fields=['status'])
            
            return True, "Venda cancelada com sucesso"
        except Venda.DoesNotExist:
            return False, "Venda não encontrada"


def criar_lote_producao(produto_id, quantidade):
    """Cria um novo lote de produção"""
    with transaction.atomic():
        try:
            produto = Produto.objects.select_for_update().get(id=produto_id)
            
            lote = LoteProducao.objects.create(
                produto=produto,
                quantidade=quantidade
            )
            
            return True, lote
        except Produto.DoesNotExist:
            return False, "Produto não encontrado"
