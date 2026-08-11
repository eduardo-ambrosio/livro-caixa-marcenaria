from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import SupabaseConfig
from .models import Entry


class SupabaseError(RuntimeError):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(slots=True)
class AuthSession:
    access_token: str
    refresh_token: str
    user_id: str
    email: str


@dataclass(frozen=True, slots=True)
class CategoryRecord:
    id: str
    name: str
    active: bool
    sort_order: int


class SupabaseClient:
    def __init__(self, config: SupabaseConfig, timeout: int = 15) -> None:
        self.config = config
        self.timeout = timeout
        self.session: AuthSession | None = None
        self.on_session_updated: Callable[[AuthSession], None] | None = None

    def sign_in(self, email: str, password: str) -> AuthSession:
        response = self._request(
            "POST",
            "/auth/v1/token",
            query={"grant_type": "password"},
            payload={"email": email.strip(), "password": password},
        )
        self.session = self._session_from_response(response, fallback_email=email.strip())
        self._notify_session_updated()
        return self.session

    def restore_session(self, refresh_token: str) -> AuthSession:
        return self._refresh_session(refresh_token)

    def sign_out(self) -> None:
        if self.session is not None:
            try:
                self._request("POST", "/auth/v1/logout", authenticated=True)
            except SupabaseError:
                pass
        self.session = None

    def rest(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        payload=None,
        prefer: str | None = None,
    ):
        headers = {"Prefer": prefer} if prefer else None
        return self._request(
            method,
            f"/rest/v1/{path.lstrip('/')}",
            query=query,
            payload=payload,
            authenticated=True,
            extra_headers=headers,
        )

    def _refresh_session(self, refresh_token: str) -> AuthSession:
        previous = self.session
        response = self._request(
            "POST",
            "/auth/v1/token",
            query={"grant_type": "refresh_token"},
            payload={"refresh_token": refresh_token},
        )
        fallback_email = previous.email if previous else ""
        fallback_user_id = previous.user_id if previous else ""
        self.session = self._session_from_response(
            response,
            fallback_email=fallback_email,
            fallback_user_id=fallback_user_id,
        )
        self._notify_session_updated()
        return self.session

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        payload=None,
        authenticated: bool = False,
        extra_headers: dict[str, str] | None = None,
        retry_after_refresh: bool = True,
    ):
        url = f"{self.config.url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"

        headers = {
            "Accept": "application/json",
            "apikey": self.config.publishable_key,
        }
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if authenticated:
            if self.session is None:
                raise SupabaseError("A sessão expirou. Entre novamente no sistema.", 401)
            headers["Authorization"] = f"Bearer {self.session.access_token}"
        if extra_headers:
            headers.update(extra_headers)

        request = Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except HTTPError as error:
            raw_error = error.read()
            if (
                authenticated
                and error.code == 401
                and retry_after_refresh
                and self.session is not None
                and self.session.refresh_token
            ):
                refresh_token = self.session.refresh_token
                self._refresh_session(refresh_token)
                return self._request(
                    method,
                    path,
                    query=query,
                    payload=payload,
                    authenticated=True,
                    extra_headers=extra_headers,
                    retry_after_refresh=False,
                )
            raise SupabaseError(self._error_message(raw_error, error.code), error.code) from error
        except (URLError, TimeoutError) as error:
            raise SupabaseError(
                "Não foi possível conectar ao banco. Verifique a internet e tente novamente."
            ) from error

        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SupabaseError("O banco retornou uma resposta que o aplicativo não reconheceu.") from error

    @staticmethod
    def _session_from_response(
        response,
        *,
        fallback_email: str = "",
        fallback_user_id: str = "",
    ) -> AuthSession:
        if not isinstance(response, dict):
            raise SupabaseError("O Supabase não retornou uma sessão válida.")
        user = response.get("user") or {}
        access_token = str(response.get("access_token") or "")
        refresh_token = str(response.get("refresh_token") or "")
        user_id = str(user.get("id") or fallback_user_id)
        email = str(user.get("email") or fallback_email)
        if not access_token or not refresh_token or not user_id:
            raise SupabaseError("O Supabase não retornou uma sessão completa.")
        return AuthSession(access_token, refresh_token, user_id, email)

    @staticmethod
    def _error_message(raw: bytes, status: int) -> str:
        details = ""
        try:
            payload = json.loads(raw.decode("utf-8"))
            if isinstance(payload, dict):
                details = str(
                    payload.get("msg")
                    or payload.get("message")
                    or payload.get("error_description")
                    or payload.get("error")
                    or ""
                )
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass

        normalized = details.casefold()
        if status in (400, 401) and (
            "invalid login" in normalized
            or "invalid credentials" in normalized
            or "email not confirmed" in normalized
        ):
            return "E-mail ou senha incorretos. Confira os dados e tente novamente."
        if status == 401:
            return "Seu acesso não foi autorizado. Entre novamente no sistema."
        if status == 403:
            return "Este usuário não tem permissão para realizar essa operação."
        return details or f"O banco retornou um erro (HTTP {status})."

    def _notify_session_updated(self) -> None:
        if self.session is not None and self.on_session_updated is not None:
            self.on_session_updated(self.session)


class SupabaseRepository:
    def __init__(self, client: SupabaseClient) -> None:
        self.client = client

    def load_categories(self) -> list[CategoryRecord]:
        rows = self.client.rest(
            "GET",
            "categories",
            query={
                "select": "id,name,active,sort_order",
                "active": "eq.true",
                "order": "sort_order.asc,name.asc",
            },
        )
        return [
            CategoryRecord(
                id=str(row["id"]),
                name=str(row["name"]),
                active=bool(row["active"]),
                sort_order=int(row["sort_order"]),
            )
            for row in rows or []
        ]

    def load_month_entries(
        self,
        month: date,
        categories: Iterable[CategoryRecord],
    ) -> list[Entry]:
        next_month = self._add_month(month, 1)
        rows = self.client.rest(
            "GET",
            "entries",
            query={
                "select": "id,entry_date,description,category_id,entry_type,amount,payment_method",
                "entry_date": f"gte.{month.isoformat()}",
                "and": f"(entry_date.lt.{next_month.isoformat()},deleted_at.is.null)",
                "order": "entry_date.desc,created_at.asc",
            },
        )
        category_names = {item.id: item.name for item in categories}
        return [self._entry_from_row(row, category_names) for row in rows or []]

    def create_entry(
        self,
        entry: Entry,
        categories: Iterable[CategoryRecord],
    ) -> Entry:
        category_id = self._category_id(entry.category, categories)
        rows = self.client.rest(
            "POST",
            "entries",
            payload={
                "entry_date": entry.date.isoformat(),
                "description": entry.description,
                "category_id": category_id,
                "entry_type": "income" if entry.is_income else "expense",
                "amount": str(entry.value),
                "payment_method": entry.payment_method,
            },
            prefer="return=representation",
        )
        if not rows:
            raise SupabaseError("O banco não confirmou o novo lançamento.")
        names = {item.id: item.name for item in categories}
        return self._entry_from_row(rows[0], names)

    def replace_day_entries(
        self,
        selected_date: date,
        entries: list[Entry],
        categories: Iterable[CategoryRecord],
    ) -> list[Entry]:
        category_list = list(categories)
        payload_entries = [
            {
                "description": entry.description,
                "category_id": self._category_id(entry.category, category_list),
                "entry_type": "income" if entry.is_income else "expense",
                "amount": str(entry.value),
                "payment_method": entry.payment_method,
            }
            for entry in entries
        ]
        rows = self.client.rest(
            "POST",
            "rpc/replace_day_entries",
            payload={
                "p_entry_date": selected_date.isoformat(),
                "p_entries": payload_entries,
            },
        )
        names = {item.id: item.name for item in category_list}
        return [self._entry_from_row(row, names) for row in rows or []]

    def manage_categories(
        self,
        operations: list[tuple[str, str, str | None]],
    ) -> list[CategoryRecord]:
        payload = [
            {"action": action, "old_name": old_name, "new_name": new_name}
            for action, old_name, new_name in operations
        ]
        rows = self.client.rest(
            "POST",
            "rpc/manage_categories",
            payload={"p_operations": payload},
        )
        return [
            CategoryRecord(
                id=str(row["id"]),
                name=str(row["name"]),
                active=bool(row["active"]),
                sort_order=int(row["sort_order"]),
            )
            for row in rows or []
        ]

    @staticmethod
    def _entry_from_row(row: dict, category_names: dict[str, str]) -> Entry:
        category_id = str(row["category_id"])
        return Entry(
            date=date.fromisoformat(str(row["entry_date"])),
            description=str(row["description"]),
            category=category_names.get(category_id, "Sem categoria"),
            is_income=str(row["entry_type"]) == "income",
            value=Decimal(str(row["amount"])),
            payment_method=str(row.get("payment_method") or "Não informado"),
            id=str(row["id"]),
            category_id=category_id,
        )

    @staticmethod
    def _category_id(name: str, categories: Iterable[CategoryRecord]) -> str:
        key = name.casefold()
        for category in categories:
            if category.name.casefold() == key:
                return category.id
        raise SupabaseError(f'A categoria "{name}" não existe mais. Atualize a lista e tente novamente.')

    @staticmethod
    def _add_month(value: date, amount: int) -> date:
        month_index = value.year * 12 + value.month - 1 + amount
        return date(month_index // 12, month_index % 12 + 1, 1)
