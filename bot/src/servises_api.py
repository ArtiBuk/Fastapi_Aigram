from datetime import datetime

from httpx import AsyncClient

from src.schemas import UserCreateApi, UpdateForAdminApi, UpdateUserApi, ObjectCreateApi
from src.settings import settings

client = AsyncClient()


async def get_user_api(tg_id: int, is_admin: bool, tg_id_by_search: int | None) -> dict | str:
    headers = {
        "tg_id": f"{str(tg_id)}",
    }
    if is_admin:
        params = {"tg_id_by_search": tg_id_by_search}
        response = await client.get(
            url=f'{settings.base_root}/user/me',
            headers=headers,
            params=params
        )
    else:
        response = await client.get(
            url=f'{settings.base_root}/user/me',
            headers=headers
        )
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        return "Unauthorized"
    elif response.status_code == 400:
        return "Ваш аккаунт удален администратором"
    else:
        return "Что-то пошло не так"


async def create_user_api(user_data: UserCreateApi) -> dict | int:
    response = await client.post(
        url=f'{settings.base_root}/user/create',
        json=user_data.dict()
    )
    if response.status_code == 200:
        return response.json()
    else:
        return response.status_code


async def get_all_users_api(tg_id: int, with_right: bool) -> list | str:
    headers = {
        "tg_id": f"{str(tg_id)}",
    }
    params = {"with_right": with_right}
    response = await client.get(
        url=f'{settings.base_root}/user/get_all',
        headers=headers,
        params=params
    )
    if response.status_code == 200:
        data = response.json()
        user_list = []
        for user in data['users']:
            fio = f"{user['last_name']} {user['first_name']} {user['middle_name']} (tg_id: {user['tg_id']})" if user[
                'middle_name'] else f"{user['last_name']} {user['first_name']}"
            user_list.append(fio)
        return user_list
    else:
        return "Что-то пошло не так"


async def update_user_api(tg_id: int, user_update: UpdateForAdminApi | UpdateUserApi,
                          tg_for_update: int | None) -> dict | str:
    headers = {
        "tg_id": f"{str(tg_id)}",
    }
    if tg_for_update:
        params = {"user_tg_id": tg_for_update}
        response = await client.put(
            url=f'{settings.base_root}/user/update_by_admin',
            json=user_update.dict(),
            headers=headers,
            params=params
        )
    else:
        response = await client.put(
            url=f'{settings.base_root}/user/update_me',
            json=user_update.dict(),
            headers=headers
        )
    data = response.json()
    print(data)
    if response.status_code == 200:
        return data
    else:
        return "Что-пошло не так"


async def delete_user_api(tg_id: int, tg_for_delete: int) -> str | None:
    headers = {
        "tg_id": f"{str(tg_id)}",
    }
    params = {"tg_id": tg_for_delete}
    response = await client.delete(
        url=f'{settings.base_root}/user/soft_removal',
        headers=headers,
        params=params
    )
    if response.status_code == 200:
        return response.text
    else:
        return None


async def time_control_api(tg_id: int, is_started: bool) -> str | None:
    headers = {
        "tg_id": f"{str(tg_id)}",
    }
    params = {"is_started": is_started}
    response = await client.post(
        url=f'{settings.base_root}/user/start_work',
        headers=headers,
        params=params
    )
    print(response)
    if response.status_code == 200:
        return response.text
    elif response.status_code == 400:
        return response.text
    else:
        return None


async def get_report_time_control_api(tg_id: int, date_start: datetime, date_end: datetime,
                                      tg_id_by_search: int | None) -> dict | None:
    headers = {
        "tg_id": f"{str(tg_id)}",
    }
    if tg_id_by_search:
        params = {
            "date_start": date_start,
            "date_end": date_end,
            "tg_id_by_search": tg_id_by_search
        }
    else:
        params = {
            "date_start": date_start,
            "date_end": date_end,
        }
    response = await client.get(
        url=f'{settings.base_root}/user/get_time_control',
        headers=headers,
        params=params
    )
    print(response)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 400:
        return response.json()
    else:
        return None


async def get_all_objects_api(tg_id: int) -> list | str:
    headers = {
        "tg_id": f"{str(tg_id)}",
    }
    response = await client.get(
        url=f'{settings.base_root}/object/all',
        headers=headers,
    )
    if response.status_code == 200:
        data = response.json()
        print(data)
        obj_list = []
        for obj in data['objects']:
            obj_bt = f":{obj['name']} ({obj['city']}) - ID: {obj['id']}; Кол-во отчетов: {obj['count_report'] if obj['count_report'] else '0'}"
            obj_list.append(obj_bt)
        return obj_list
    else:
        return "Что-то пошло не так"


async def get_report_profit_api(tg_id: int, date_start: datetime, date_end: datetime,
                                object_id: int | None) -> dict | None:
    headers = {
        "tg_id": f"{str(tg_id)}",
    }
    params = {
        "date_start": date_start,
        "date_end": date_end,
        "object_id": object_id
    }
    response = await client.get(
        url=f'{settings.base_root}/object/{object_id}/report_profit',
        headers=headers,
        params=params
    )
    data = response.json()
    print(data)
    if response.status_code == 200:
        return data
    elif response.status_code == 400:
        return data
    else:
        return None


async def delete_object_api(tg_id: int, object_id: int | None) -> str:
    headers = {
        "tg_id": f"{str(tg_id)}",
    }
    params = {
        "object_id": object_id
    }
    response = await client.delete(
        url=f'{settings.base_root}/object/soft_removal',
        headers=headers,
        params=params
    )
    print(response.text)
    return response.text


async def create_object_api(tg_id: int, object_in: ObjectCreateApi) -> dict | str:
    headers = {
        "tg_id": f"{str(tg_id)}",
    }
    response = await client.post(
        url=f'{settings.base_root}/object/create',
        headers=headers,
        json=object_in.dict()
    )
    print(response.json())
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 403:
        return "Вы не являетесь админом"
    else:
        return response.text
