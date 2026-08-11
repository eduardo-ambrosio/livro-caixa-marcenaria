begin;

-- Substitui uma folha diária inteira em uma transação atômica.
-- Se qualquer linha for inválida, nenhuma alteração do dia é aplicada.
create or replace function public.replace_day_entries(
    p_entry_date date,
    p_entries jsonb
)
returns setof public.entries
language plpgsql
security invoker
set search_path = ''
as $$
declare
    actor_id uuid := auth.uid();
begin
    if actor_id is null then
        raise exception using errcode = '42501', message = 'Usuário não autenticado.';
    end if;
    if p_entry_date is null then
        raise exception using errcode = '22023', message = 'A data da folha é obrigatória.';
    end if;
    if jsonb_typeof(coalesce(p_entries, '[]'::jsonb)) <> 'array' then
        raise exception using errcode = '22023', message = 'A lista de lançamentos é inválida.';
    end if;

    update public.entries
    set deleted_at = now()
    where user_id = actor_id
      and entry_date = p_entry_date
      and deleted_at is null;

    insert into public.entries (
        user_id,
        entry_date,
        description,
        category_id,
        entry_type,
        amount,
        payment_method
    )
    select
        actor_id,
        p_entry_date,
        btrim(item.description),
        item.category_id,
        item.entry_type,
        item.amount,
        coalesce(nullif(btrim(item.payment_method), ''), 'Não informado')
    from jsonb_to_recordset(coalesce(p_entries, '[]'::jsonb)) as item(
        description text,
        category_id uuid,
        entry_type text,
        amount numeric,
        payment_method text
    );

    return query
    select entry.*
    from public.entries as entry
    where entry.user_id = actor_id
      and entry.entry_date = p_entry_date
      and entry.deleted_at is null
    order by entry.created_at, entry.id;
end;
$$;

revoke execute on function public.replace_day_entries(date, jsonb) from public, anon;
grant execute on function public.replace_day_entries(date, jsonb) to authenticated;

-- Aplica inclusões, renomeações e exclusões de categorias em conjunto.
create or replace function public.manage_categories(p_operations jsonb)
returns setof public.categories
language plpgsql
security invoker
set search_path = ''
as $$
declare
    actor_id uuid := auth.uid();
    operation jsonb;
    action_name text;
    old_name text;
    new_name text;
    target_id uuid;
    fallback_id uuid;
    next_order integer;
begin
    if actor_id is null then
        raise exception using errcode = '42501', message = 'Usuário não autenticado.';
    end if;
    if jsonb_typeof(coalesce(p_operations, '[]'::jsonb)) <> 'array' then
        raise exception using errcode = '22023', message = 'A lista de alterações é inválida.';
    end if;

    for operation in
        select value from jsonb_array_elements(coalesce(p_operations, '[]'::jsonb))
    loop
        action_name := operation ->> 'action';
        old_name := btrim(coalesce(operation ->> 'old_name', ''));
        new_name := btrim(coalesce(operation ->> 'new_name', ''));

        if action_name = 'add' then
            if new_name = '' then
                raise exception using errcode = '22023', message = 'O nome da categoria é obrigatório.';
            end if;
            select coalesce(max(category.sort_order), 0) + 10
            into next_order
            from public.categories as category
            where category.user_id = actor_id;

            insert into public.categories (user_id, name, sort_order)
            values (actor_id, new_name, next_order);

        elsif action_name = 'rename' then
            if old_name = '' or new_name = '' then
                raise exception using errcode = '22023', message = 'Os nomes da categoria são obrigatórios.';
            end if;
            update public.categories as category
            set name = new_name
            where category.user_id = actor_id
              and lower(category.name) = lower(old_name)
              and category.active
            returning category.id into target_id;

            if target_id is null then
                raise exception using errcode = 'P0002', message = 'Categoria não encontrada.';
            end if;

        elsif action_name = 'delete' then
            select category.id
            into target_id
            from public.categories as category
            where category.user_id = actor_id
              and lower(category.name) = lower(old_name)
              and category.active
            limit 1;

            if target_id is null then
                raise exception using errcode = 'P0002', message = 'Categoria não encontrada.';
            end if;
            if (select count(*) from public.categories where user_id = actor_id and active) <= 1 then
                raise exception using errcode = '22023', message = 'É necessário manter pelo menos uma categoria.';
            end if;

            select category.id
            into fallback_id
            from public.categories as category
            where category.user_id = actor_id
              and category.active
              and category.id <> target_id
            order by (lower(category.name) = 'outros') desc, category.sort_order, category.name
            limit 1;

            update public.entries
            set category_id = fallback_id
            where user_id = actor_id
              and category_id = target_id;

            delete from public.categories
            where user_id = actor_id
              and id = target_id;

        else
            raise exception using errcode = '22023', message = 'Operação de categoria desconhecida.';
        end if;

        target_id := null;
        fallback_id := null;
    end loop;

    return query
    select category.*
    from public.categories as category
    where category.user_id = actor_id
      and category.active
    order by category.sort_order, category.name;
end;
$$;

revoke execute on function public.manage_categories(jsonb) from public, anon;
grant execute on function public.manage_categories(jsonb) to authenticated;

commit;
