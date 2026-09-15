from django.db import models
from decimal import Decimal


class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"


class Produto(models.Model):
    UNIDADE_CHOICES = [
        ('UN', 'Unidade'),
        ('KG', 'Quilograma'),
    ]

    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    unidade = models.CharField(max_length=2, choices=UNIDADE_CHOICES)
    estoque_atual = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('0.000'))
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"


class LoteProducao(models.Model):
    STATUS_CHOICES = [
        ('EM_PRODUCAO', 'Em Produção'),
        ('PRONTO', 'Pronto'),
        ('ESGOTADO', 'Esgotado'),
    ]

    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.DecimalField(max_digits=10, decimal_places=3)
    data_saida = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='EM_PRODUCAO')

    def __str__(self):
        return f"Lote {self.id} - {self.produto.nome}"

    class Meta:
        verbose_name = "Lote de Produção"
        verbose_name_plural = "Lotes de Produção"


class Venda(models.Model):
    STATUS_CHOICES = [
        ('EM_ABERTO', 'Em Aberto'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]

    atendente = models.CharField(max_length=100)
    data_hora = models.DateTimeField(auto_now_add=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='EM_ABERTO')

    def __str__(self):
        return f"Venda {self.id} - {self.atendente}"

    class Meta:
        verbose_name = "Venda"
        verbose_name_plural = "Vendas"


class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.DecimalField(max_digits=10, decimal_places=3)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Item {self.id} - {self.produto.nome}"

    class Meta:
        verbose_name = "Item de Venda"
        verbose_name_plural = "Itens de Vendas"

