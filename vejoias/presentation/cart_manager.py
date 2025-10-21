# vejoias/presentation/cart_manager.py
# Gerencia a persistência e manipulação do Carrinho de Compras na sessão do Django.

import json
from decimal import Decimal
from typing import Dict, Any, Optional

from django.http import HttpRequest
from vejoias.core.entities import Carrinho, ItemCarrinho
from vejoias.infrastructure.repositories import JoiaRepository

class CartManager:
    """
    Gerencia a lógica de negócio do carrinho de compras, utilizando a sessão do Django
    para persistir o estado do carrinho entre requisições.
    """
    
    SESSION_KEY = 'carrinho_vejoias'
    
    def __init__(self, request: HttpRequest):
        """Inicializa o CartManager e carrega o carrinho da sessão."""
        self.request = request
        self.joia_repository = JoiaRepository()
        self.carrinho: Carrinho = self._load_carrinho_from_session()

    # --- Métodos de Persistência ---

    def _load_carrinho_from_session(self) -> Carrinho:
        """
        Carrega o Carrinho da sessão do Django. 
        Se não existir, cria um novo objeto Carrinho vazio.
        """
        raw_cart = self.request.session.get(self.SESSION_KEY)
        
        if not raw_cart:
            return Carrinho()

        itens = []
        # O carrinho armazenado é um dicionário {joia_id: quantidade}
        for joia_id, quantidade in raw_cart.items():
            joia_id = int(joia_id) # Garante que a chave seja int
            
            # Busca os detalhes mais recentes da Joia no banco de dados
            joia_entity = self.joia_repository.get_joia_by_id(joia_id)
            
            if joia_entity and joia_entity.ativa and joia_entity.estoque > 0:
                # Atualiza os dados do item com o preço atual e verifica o limite de estoque
                quantidade_real = min(quantidade, joia_entity.estoque)
                
                item = ItemCarrinho(
                    joia_id=joia_entity.id,
                    nome=joia_entity.nome,
                    preco_unitario=joia_entity.preco,
                    quantidade=quantidade_real
                )
                itens.append(item)
        
        # Cria a entidade Carrinho com os itens atualizados
        return Carrinho(itens=itens)

    def _save_carrinho_to_session(self):
        """
        Serializa o Carrinho para um formato simples e salva na sessão.
        Apenas o ID e a quantidade são armazenados para evitar dados desatualizados.
        """
        cart_data = {}
        for item in self.carrinho.itens:
            # Armazena {ID da Joia: Quantidade}
            cart_data[str(item.joia_id)] = item.quantidade
            
        self.request.session[self.SESSION_KEY] = cart_data
        self.request.session.modified = True
        
    def clear_carrinho(self):
        """Limpa o carrinho na sessão (usado após o checkout)."""
        if self.SESSION_KEY in self.request.session:
            del self.request.session[self.SESSION_KEY]
            self.request.session.modified = True
            self.carrinho = Carrinho() # Reseta o objeto manager
            

    # --- Métodos de Manipulação ---

    def add_item(self, joia_id: int, quantidade: int = 1):
        """Adiciona ou atualiza a quantidade de uma joia no carrinho."""
        joia_entity = self.joia_repository.get_joia_by_id(joia_id)
        
        if not joia_entity or not joia_entity.ativa:
            # Não faz nada se a joia não existir ou estiver inativa
            return
            
        # Tenta encontrar o item existente
        existing_item = self.carrinho.get_item(joia_id)

        if existing_item:
            nova_quantidade = existing_item.quantidade + quantidade
        else:
            nova_quantidade = quantidade
            
        # Verifica o estoque máximo
        if nova_quantidade > joia_entity.estoque:
            nova_quantidade = joia_entity.estoque
            # Em uma aplicação real, você deve retornar uma mensagem de erro aqui

        if existing_item:
            existing_item.quantidade = nova_quantidade
        else:
            new_item = ItemCarrinho(
                joia_id=joia_entity.id,
                nome=joia_entity.nome,
                preco_unitario=joia_entity.preco,
                quantidade=nova_quantidade
            )
            self.carrinho.itens.append(new_item)

        self._save_carrinho_to_session()

    def remove_item(self, joia_id: int):
        """Remove completamente um item do carrinho."""
        self.carrinho.itens = [item for item in self.carrinho.itens if item.joia_id != joia_id]
        self._save_carrinho_to_session()

    def update_quantity(self, joia_id: int, quantidade: int):
        """Atualiza a quantidade de um item existente."""
        joia_entity = self.joia_repository.get_joia_by_id(joia_id)
        
        if not joia_entity or not joia_entity.ativa:
            return

        if quantidade <= 0:
            self.remove_item(joia_id)
            return

        # Verifica o estoque
        quantidade_final = min(quantidade, joia_entity.estoque)

        existing_item = self.carrinho.get_item(joia_id)
        if existing_item:
            existing_item.quantidade = quantidade_final
            self._save_carrinho_to_session()
        # Se não existir, a função add_item pode ser usada, mas para update, só fazemos se já estiver lá.


    # --- Métodos de Consulta ---

    def get_carrinho(self) -> Carrinho:
        """Retorna o objeto Carrinho atualizado."""
        return self.carrinho
    
    def get_total_items(self) -> int:
        """Retorna a contagem total de itens (unidades) no carrinho."""
        return self.carrinho.get_total_itens()
    
    def is_empty(self) -> bool:
        """Verifica se o carrinho está vazio."""
        return self.carrinho.is_empty()

    def get_carrinho_context(self) -> Dict[str, Any]:
        """
        Retorna o contexto do carrinho para uso em templates (Carrinho e total).
        """
        carrinho = self.get_carrinho()
        return {
            'carrinho': carrinho,
            'total_geral': carrinho.total_geral,
            'total_itens': self.get_total_items(),
        }
