begin;

-- Categorias disponíveis para cada usuário do Livro Caixa.
create table if not exists public.categories (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
    name text not null check (char_length(btrim(name)) between 1 and 80),
    active boolean not null default true,
    sort_order integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (id, user_id)
);

create unique index if not exists categories_user_name_unique
    on public.categories (user_id, lower(btrim(name)));

-- Lançamentos de entrada e saída do caixa.
create table if not exists public.entries (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
    entry_date date not null,
    description text not null check (char_length(btrim(description)) between 1 and 240),
    category_id uuid not null,
    entry_type text not null check (entry_type in ('income', 'expense')),
    amount numeric(14, 2) not null check (amount > 0),
    payment_method text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    deleted_at timestamptz,
    constraint entries_category_owner_fk
        foreign key (category_id, user_id)
        references public.categories (id, user_id)
        on update cascade
        on delete restrict
);

create index if not exists entries_user_date_idx
    on public.entries (user_id, entry_date desc)
    where deleted_at is null;

create index if not exists entries_user_category_idx
    on public.entries (user_id, category_id)
    where deleted_at is null;

-- Mantém a data de alteração correta sem depender do aplicativo.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists categories_set_updated_at on public.categories;
create trigger categories_set_updated_at
    before update on public.categories
    for each row execute function public.set_updated_at();

drop trigger if exists entries_set_updated_at on public.entries;
create trigger entries_set_updated_at
    before update on public.entries
    for each row execute function public.set_updated_at();

-- Cria as categorias iniciais automaticamente para cada novo usuário.
create or replace function public.seed_default_categories()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.categories (user_id, name, sort_order)
    values
        (new.id, 'Madeira', 10),
        (new.id, 'Ferragens', 20),
        (new.id, 'Funcionários', 30),
        (new.id, 'Energia', 40),
        (new.id, 'Manutenção', 50),
        (new.id, 'Frete', 60),
        (new.id, 'Venda', 70),
        (new.id, 'Outros', 80)
    on conflict do nothing;
    return new;
end;
$$;

revoke execute on function public.seed_default_categories() from public, anon, authenticated;

drop trigger if exists on_auth_user_created_seed_categories on auth.users;
create trigger on_auth_user_created_seed_categories
    after insert on auth.users
    for each row execute function public.seed_default_categories();

-- Proteção: o aplicativo nunca acessa dados sem um usuário autenticado.
alter table public.categories enable row level security;
alter table public.entries enable row level security;

revoke all on table public.categories from anon, authenticated;
revoke all on table public.entries from anon, authenticated;
grant select, insert, update, delete on table public.categories to authenticated;
grant select, insert, update, delete on table public.entries to authenticated;

drop policy if exists categories_select_own on public.categories;
create policy categories_select_own
    on public.categories for select to authenticated
    using ((select auth.uid()) = user_id);

drop policy if exists categories_insert_own on public.categories;
create policy categories_insert_own
    on public.categories for insert to authenticated
    with check ((select auth.uid()) = user_id);

drop policy if exists categories_update_own on public.categories;
create policy categories_update_own
    on public.categories for update to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

drop policy if exists categories_delete_own on public.categories;
create policy categories_delete_own
    on public.categories for delete to authenticated
    using ((select auth.uid()) = user_id);

drop policy if exists entries_select_own on public.entries;
create policy entries_select_own
    on public.entries for select to authenticated
    using ((select auth.uid()) = user_id);

drop policy if exists entries_insert_own on public.entries;
create policy entries_insert_own
    on public.entries for insert to authenticated
    with check ((select auth.uid()) = user_id);

drop policy if exists entries_update_own on public.entries;
create policy entries_update_own
    on public.entries for update to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

drop policy if exists entries_delete_own on public.entries;
create policy entries_delete_own
    on public.entries for delete to authenticated
    using ((select auth.uid()) = user_id);

-- Caso um usuário tenha sido criado antes desta migração, também recebe as categorias.
insert into public.categories (user_id, name, sort_order)
select users.id, defaults.name, defaults.sort_order
from auth.users as users
cross join (
    values
        ('Madeira', 10),
        ('Ferragens', 20),
        ('Funcionários', 30),
        ('Energia', 40),
        ('Manutenção', 50),
        ('Frete', 60),
        ('Venda', 70),
        ('Outros', 80)
) as defaults(name, sort_order)
on conflict do nothing;

commit;
