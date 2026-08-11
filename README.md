# Livro Caixa da Marcenaria

Aplicativo desktop em Python com Tkinter, criado para funcionar diretamente no PyCharm e sem pacotes externos.

A identidade visual utiliza a logo Cozinhas Formatec na barra superior do sistema.

Os lançamentos são armazenados no Supabase e protegidos por autenticação e Row Level Security (RLS).

## Executar no PyCharm

1. Abra a pasta `C:\LivroCaixa` no PyCharm.
2. Confirme que existe um interpretador Python configurado em **Settings > Project > Python Interpreter**.
3. Abra `app.py`.
4. Clique no botão verde **Run** ou pressione `Shift+F10`.

Antes da primeira execução, copie `.env.example` para `.env` e preencha o Project URL e a Publishable key do Supabase. Também é possível executar pelo terminal do PyCharm:

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
- Categorias sincronizadas entre os computadores autorizados.
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
- Login com sessão protegida pelo Windows e opção de manter o acesso conectado.
- Livro diário de lançamentos em formato de planilha, inspirado no modelo em papel.
- Tela de lançamentos sem cabeçalho redundante, deixando mais linhas visíveis.
- Colunas de documento, histórico, categoria, entradas e saídas.
- Navegação entre células com Enter e entre dias pelos botões da folha.

Os dados de cada usuário ficam isolados pelas políticas de segurança do banco. O aplicativo usa somente a Publishable key; chaves administrativas não fazem parte do executável.

## Banco de dados

As migrações do Supabase estão versionadas em `supabase/migrations/`:

1. `20260811_001_initial_schema.sql`: tabelas, índices, categorias padrão e políticas RLS.
2. `20260811_002_sync_functions.sql`: salvamento atômico das folhas e edição segura das categorias.
