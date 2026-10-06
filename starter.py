import requests
from uuid import uuid4


JsonObject = dict[str, object]


class CoffeeApiError(Exception):
    pass


class CoffeeNotFoundError(CoffeeApiError):
    pass


class SampleApisCoffeeClient:
    def __init__(
        self,
        base_url: str = "https://pycourse-2026.duckdns.org/coffee/hot/",
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def list_drinks(self) -> list[JsonObject]:
        response = self._request("GET", "")
        data = self._parse_json(response)
        if not isinstance(data, list):
            raise CoffeeApiError("Ожидался список объектов в ответе list_drinks")
        return data

    def get_drink(self, drink_id: int) -> JsonObject:
        response = self._request("GET", f"{drink_id}")
        data = self._parse_json(response)
        if not isinstance(data, dict):
            raise CoffeeApiError("Ожидался словарь в ответе get_drink")
        return data

    def create_drink(self, payload: JsonObject) -> JsonObject:
        response = self._request("POST", "", payload=payload)
        data = self._parse_json(response)
        if not isinstance(data, dict):
            raise CoffeeApiError("Ожидался словарь в ответе create_drink")
        return data

    def replace_drink(
        self,
        drink_id: int,
        payload: JsonObject,
    ) -> JsonObject:
        response = self._request("PUT", f"{drink_id}", payload=payload)
        data = self._parse_json(response)
        if not isinstance(data, dict):
            raise CoffeeApiError("Ожидался словарь в ответе replace_drink")
        return data

    def update_drink(
        self,
        drink_id: int,
        changes: JsonObject,
    ) -> JsonObject:
        response = self._request("PATCH", f"{drink_id}", payload=changes)
        data = self._parse_json(response)
        if not isinstance(data, dict):
            raise CoffeeApiError("Ожидался словарь в ответе update_drink")
        return data

    def delete_drink(self, drink_id: int) -> None:
        response = self._request("DELETE", f"{drink_id}")
        # Проверяем JSON только если есть тело ответа
        if response.text.strip() and "application/json" in response.headers.get("Content-Type", "").lower():
            try:
                response.json()
            except ValueError as error:
                raise CoffeeApiError(f"Ошибка парсинга JSON ответа DELETE: {error}") from error

    def _request(
        self,
        method: str,
        path: str = "",
        payload: JsonObject | None = None,
    ) -> requests.Response:
        url = f"{self._base_url}/{path.lstrip('/')}" if path else self._base_url
        try:
            response = requests.request(
                method=method,
                url=url,
                json=payload,
                timeout=self._timeout,
            )
        except requests.RequestException as error:
            raise CoffeeApiError(f"Сетевая ошибка при запросе {method} {url}: {error}") from error

        if response.status_code == 404:
            raise CoffeeNotFoundError(f"Ресурс не найден (404): {url}")

        if not response.ok:
            raise CoffeeApiError(
                f"Ошибка API {response.status_code} при запросе {method} {url}: {response.text}"
            )

        return response

    def _parse_json(self, response: requests.Response) -> JsonObject | list[JsonObject]:
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            raise CoffeeApiError(
                f"Ожидался Content-Type application/json, получен '{content_type}'"
            )
        try:
            return response.json()
        except ValueError as error:
            raise CoffeeApiError(f"Ошибка декодирования JSON: {error}") from error

    


def main() -> int:
    client = SampleApisCoffeeClient()
    marker = uuid4().hex[:8]
    created_id = None
    try:
        # GET коллекции.
        # POST: исследуйте поля, добавьте marker в название.
        # Сразу сохраните id из ответа в created_id.
        # GET: сравните сохранённые поля с отправленными.
        # PUT и повторный GET: проверьте все заменённые поля.
        # PATCH и повторный GET: проверьте изменённое поле
        # и убедитесь, что остальные поля сохранились.
        # DELETE и GET: убедитесь, что вернулся ожидаемый 404.
        # После подтверждения удаления: created_id = None.
        # 1. GET коллекции
        print("=== Шаг 1: Получение списка горячих напитков ===")
        drinks = client.list_drinks()
        print(f"Получено напитков: {len(drinks)}")

        # 2. POST с меткой группы в названии
        print(f"\n=== Шаг 2: Создание нового напитка (метка {marker}) ===")
        initial_payload: JsonObject = {
            "title": f"Group [{marker}] Espresso Special",
            "description": "Rich espresso with dense milk foam and sweet syrup",
            "ingredients": ["Espresso", "Steamed milk", "Vanilla syrup"],
            "image": "https://images.unsplash.com/photo-1561882468-9110e03e0f78",
        }
        created_drink = client.create_drink(initial_payload)
        created_id = created_drink.get("id")
        if not isinstance(created_id, int):
            raise CoffeeApiError(f"Сервер вернул некорректный ID: {created_id}")
        print(f"Напиток создан. Сервер присвоил ID: {created_id}")

        # 3. GET по id — сравнение отправленных данных с полученными
        print(f"\n=== Шаг 3: Проверка созданного напитка по ID={created_id} ===")
        fetched_drink = client.get_drink(created_id)
        for key, expected_val in initial_payload.items():
            actual_val = fetched_drink.get(key)
            if actual_val != expected_val:
                raise CoffeeApiError(
                    f"Поле '{key}' не совпадает: ожидалось '{expected_val}', получено '{actual_val}'"
                )
        print("Данные на сервере полностью совпадают с отправленными.")

        # 4. PUT — полная замена
        print(f"\n=== Шаг 4: Полное обновление напитка через PUT ===")
        put_payload: JsonObject = {
            "title": f"Group [{marker}] Replaced Cappuccino",
            "description": "Completely replaced recipe description",
            "ingredients": ["Espresso", "Steamed milk", "Cinnamon"],
            "image": "https://images.unsplash.com/photo-1557006021-b85faa2bc5e2",
        }
        client.replace_drink(created_id, put_payload)

        fetched_after_put = client.get_drink(created_id)
        for key, expected_val in put_payload.items():
            if fetched_after_put.get(key) != expected_val:
                raise CoffeeApiError(f"Поле '{key}' не обновилось после PUT")
        print("Замена всех полей через PUT подтверждена.")

        # 5. PATCH — частичное изменение
        print(f"\n=== Шаг 5: Частичное обновление через PATCH ===")
        patch_payload: JsonObject = {
            "description": "Patched description for testing",
        }
        client.update_drink(created_id, patch_payload)

        # 6. Повторный GET — проверка сохранности остальных полей
        print(f"\n=== Шаг 6: Проверка результатов PATCH ===")
        fetched_after_patch = client.get_drink(created_id)
        if fetched_after_patch.get("description") != patch_payload["description"]:
            raise CoffeeApiError("Описание не обновилось после PATCH")
        if fetched_after_patch.get("title") != put_payload["title"]:
            raise CoffeeApiError("Поле 'title' изменилось, хотя не передавалось в PATCH")
        print("PATCH успешно изменил точечное поле и сохранил остальные.")

        # 7. DELETE
        print(f"\n=== Шаг 7: Удаление напитка ID={created_id} ===")
        client.delete_drink(created_id)
        print("Запрос на удаление выполнен.")

        # 8. Повторный GET — подтверждаем 404
        print(f"\n=== Шаг 8: Проверка отсутствия ресурса после DELETE ===")
        try:
            client.get_drink(created_id)
            raise CoffeeApiError("Ресурс доступен после DELETE!")
        except CoffeeNotFoundError:
            print("Успешно обработана ошибка 404 (CoffeeNotFoundError). Ресурс удалён.")
            created_id = None
    except (CoffeeApiError, ValueError) as error:
        print(f"Ошибка: {error}. Метка группы: {marker}")
        return 1
    finally:
        if created_id is not None:
            try:
                client.delete_drink(created_id)
            except CoffeeNotFoundError:
                pass
            except CoffeeApiError as error:
                print(f"Не удалось удалить id={created_id}: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())