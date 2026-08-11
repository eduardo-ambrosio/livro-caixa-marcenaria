# Livro Caixa da Marcenaria

Protótipo em Python com Tkinter, criado para funcionar diretamente no PyCharm e sem pacotes externos.

A identidade visual utiliza a logo Cozinhas Formatec na barra superior do sistema.

> Todos os nomes, valores e lançamentos exibidos nesta versão são dados fictícios de demonstração.

## Executar no PyCharm

1. Abra a pasta `C:\LivroCaixa` no PyCharm.
2. Confirme que existe um interpretador Python configurado em **Settings > Project > Python Interpreter**.
3. Abra `app.py`.
4. Clique no botão verde **Run** ou pressione `Shift+F10`.

Também é possível executar pelo terminal do PyCharm:

```powershell
python app.py
```

Se o comando `python` não for reconhecido, selecione o interpretador do projeto no PyCharm e execute `app.py` pelo botão **Run**.

## Abrir com dois cliques

Dê dois cliques no arquivo `Abrir Livro Caixa.cmd` existente na pasta principal. Ele localiza o aplicativo automaticamente e abre sem manter uma janela de terminal.

## O que já funciona

- Interface no estilo **Oficina clean**.
- Resumo mensal de entradas, saídas e saldo.
- Visualização de despesas por categoria.
- Lista dos últimos lançamentos.
- Formulário para adicionar uma entrada ou saída.
- Atualização dos totais e do gráfico durante a execução.
- Navegação pelas áreas planejadas do sistema.
- Navegação compacta no topo com apenas Resumo e Lançamentos.
- Resumo filtrado pelo mês escolhido, com atalhos para mês anterior, próximo e mês atual.
- Sincronização do mês selecionado com a folha de lançamentos.
- Categorias personalizáveis: adicionar, renomear e excluir diretamente nos Lançamentos.
- Lista de categorias salva localmente para as próximas aberturas.
- Fontes ampliadas e linhas mais altas para facilitar a leitura.
- Linha inteira destacada ao selecionar qualquer célula, com indicação do número da linha.
- Data ampliada e em negrito na folha de lançamentos.
- Categorias protegidas contra alterações acidentais pela roda do mouse.
- Coluna de documento removida para simplificar a folha e ampliar o histórico.
- Seletores de data, categoria e mês com fontes maiores.
- Todos os campos editáveis dos lançamentos usam fonte tamanho 14.
- O gráfico reserva espaço automaticamente para nomes maiores de categorias.
- Alternância no Resumo entre gráfico de linhas e gráfico de pizza com percentuais.
- Gráfico de pizza ampliado e centralizado na área disponível.
- Fatias e legendas clicáveis para consultar datas, históricos e valores da categoria.
- Livro diário de lançamentos em formato de planilha, inspirado no modelo em papel.
- Tela de lançamentos sem cabeçalho redundante, deixando mais linhas visíveis.
- Colunas de documento, histórico, categoria, entradas e saídas.
- Navegação entre células com Enter e entre dias pelos botões da folha.

Os dados ainda são demonstrativos e não permanecem depois que o programa fecha. A próxima etapa será conectar o aplicativo ao Supabase para persistência e sincronização entre computadores.

## Banco de dados

O esquema inicial seguro do Supabase está versionado em
`supabase/migrations/20260811_001_initial_schema.sql`. Ele cria as categorias,
os lançamentos, os índices e as políticas de acesso por usuário.
