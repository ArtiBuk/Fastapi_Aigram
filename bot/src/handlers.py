import re
from datetime import datetime

from aiogram import Dispatcher, types
from aiogram.client import bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.markdown import hbold

from src.button import get_main_button, get_time_control_button, get_update_user_for_admin_button
from src.schemas import UserCreateApi
from src.servises import get_id_from_message, parse_update_by_admin_message, parse_update_message, format_user_get_me, \
    parse_dates_from_message, parse_date_from_response
from src.servises_api import get_user_api, create_user_api, get_all_users_api, update_user_api, \
    delete_user_api, time_control_api, get_report_time_control_api
from src.states import MainMenuStates, RegistrationState, TimeControl, UpdateUserDataForAdmin, UpdateUserData, \
    DeleteUserForAdmin, SelectUserData
from email_validator import validate_email, EmailNotValidError

dp = Dispatcher()
USER = {}


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    tg_id = message.from_user.id
    if tg_id in USER:
        bt = get_main_button(True, tg_id)
        await state.set_state(MainMenuStates.waiting_action)
        await message.answer(
            f"Вы уже авторизовались\n"
            f"Могу вам чем-то помочь?",
            reply_markup=bt
        )
    else:
        response = await get_user_api(tg_id, False, None)
        if isinstance(response, dict):
            USER[tg_id] = response["is_admin"]
            bt = get_main_button(True, tg_id)
            await state.set_state(MainMenuStates.waiting_action)
            await message.answer(
                f"Привет, {hbold(message.from_user.full_name)}\n"
                f"Могу вам чем-то помочь?",
                reply_markup=bt
            )
        elif response == "Unauthorized":
            await state.set_state(RegistrationState.waiting_username)
            markup = types.ReplyKeyboardRemove()
            await message.answer(
                f"Привет, {hbold(message.from_user.full_name)}"
                f"Вы еще не авторизированны. Пройдите регистрацию \n"
                f"Введите ваш username",
                reply_markup=markup
            )
        else:
            await message.answer(f"Привет, {hbold(message.from_user.full_name)}"
                                 f"Произошла неприведенная ошибка. Обратитесь к администратору (@artibuk)")


@dp.message(RegistrationState.waiting_username)
async def reg_username_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(username=message.text)
    await state.set_state(RegistrationState.waiting_fio)
    await message.answer("Креативно! А теперь ФИО (обязательно через пробел)."
                         " Если ошибётесь, то прийдется просить душного администратора менять ФИО, а оно вам надо?)")


@dp.message(RegistrationState.waiting_fio)
async def reg_fio_handler(message: Message, state: FSMContext) -> None:
    fio_parts = message.text.split()
    if len(fio_parts) != 3:
        await state.set_state(RegistrationState.waiting_fio)
        await message.answer(
            "А я предупреждал, а вы меня не послушали. Ладно, я никому не расскажу. Введите ФИО еще раз:")
    else:
        await state.set_state(RegistrationState.waiting_email)
        await state.update_data(first_name=fio_parts[0], last_name=fio_parts[1], middle_name=fio_parts[2])
        await message.answer("Приятно познакомиться! Осталось ввести только ваш email.")


@dp.message(RegistrationState.waiting_email)
async def reg_email_handler(message: Message, state: FSMContext) -> None:
    try:
        validate_email(message.text)
        user_data = await state.get_data()
        user_create = UserCreateApi(
            username=user_data["username"],
            email=message.text,
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            middle_name=user_data["middle_name"],
            tg_id=message.from_user.id
        )
        response = await create_user_api(user_create)
        await state.clear()
        if isinstance(response, dict):
            USER[int(response.get('tg_id'))] = response.get('is_admin')
            await state.set_state(MainMenuStates.waiting_action)
            bt = get_main_button(True, int(response.get('tg_id')))
            await message.reply(
                f"Успешная регистрация. Твои данные в базе:\n"
                f"Логин: {response.get('username')}\n"
                f"Фамилия: {response.get('first_name')}\n"
                f"Имя: {response.get('last_name')}\n"
                f"Отчетсво: {response.get('middle_name')}\n"
                f"Твой ID в телеграм: {response.get('tg_id')}\n"
                f"Email: {response.get('email')}\n"
                f"Являешься ли ты админом: {'Да' if response.get('is_admin') else 'Нет'}\n"
                f"\nЧем я вам могу помочь",
                reply_markup=bt
            )
        else:
            await message.answer(f"Произошла неприведенная ошибка. Обратитесь к администратору (@artibuk)")

    except EmailNotValidError:
        await state.set_state(RegistrationState.waiting_email)
        await message.answer("Некорректный email. Попробуйте еще раз.")


@dp.message(MainMenuStates.waiting_action)
async def action_selection_handler(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    if message.text == "TimeControl":
        bt = get_time_control_button(user_id)
        await state.set_state(TimeControl.waiting_action)
        await message.reply(
            f"Это раздел учета времени сотрудников. Выберете действие",
            reply_markup=bt
        )
    elif message.text == "Отчеты объектов":
        bt = get_main_button(True, user_id)
        await state.set_state(MainMenuStates.waiting_action)
        await message.reply("Пока недоступно", reply_markup=bt)
    elif message.text == "Информация о пользователях":
        users = await get_all_users_api(user_id, False)
        if isinstance(users, list):
            bt = get_update_user_for_admin_button(user_id, users)
            await state.set_state(SelectUserData.waiting_what_to_get)
            await message.reply("Выберите пользователя", reply_markup=bt)
    elif message.text == "Редактировать свои данные":
        await state.set_state(UpdateUserData.waiting_what_to_update)
        markup = types.ReplyKeyboardRemove()
        await message.reply(
            f"Выберите какие поля хотите обновить в следующем порядке (если не хотите менять поля, просто '0'). Поля надо писать через Enter\n"
            f"Фамилия\n"
            f"Имя\n"
            f"Отчетсво\n"
            f"Email\n",
            reply_markup=markup
        )
    elif message.text == "Редактировать пользователя":
        users = await get_all_users_api(user_id, False)
        if isinstance(users, list):
            bt = get_update_user_for_admin_button(user_id, users)
            await state.set_state(UpdateUserDataForAdmin.waiting_user)
            await message.reply("Выберите пользователя", reply_markup=bt)
    elif message.text == "Удалить пользователя":
        users = await get_all_users_api(user_id, False)
        if isinstance(users, list):
            bt = get_update_user_for_admin_button(user_id, users)
            await state.set_state(DeleteUserForAdmin.waiting_user)
            await message.reply("Выберите пользователя", reply_markup=bt)
    elif message.text == "Посмотреть свои данные":
        response = await get_user_api(user_id, False, None)
        bt = get_main_button(True, user_id)
        await state.set_state(MainMenuStates.waiting_action)
        if isinstance(response, dict):
            answer = format_user_get_me(response)
            await message.reply(
                f"{answer}",
                reply_markup=bt
            )
    else:
        bt = get_main_button(True, user_id)
        await state.set_state(MainMenuStates.waiting_action)
        await message.reply("Чет вы ошиблись. Введите корректную команду.", reply_markup=bt)


@dp.message(UpdateUserDataForAdmin.waiting_user)
async def update_select_user_handler(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    tg_id = get_id_from_message(message.text)
    if isinstance(tg_id, int):
        await state.update_data(tg_id=tg_id)
        await state.set_state(UpdateUserDataForAdmin.waiting_what_to_update)
        markup = types.ReplyKeyboardRemove()
        await message.reply(
            f"Выберите какие поля хотите обновить в следующем порядке (если не хотите менять поля, просто '0'). Поля надо писать через Enter\n"
            f"Логин\n"
            f"Фамилия\n"
            f"Имя\n"
            f"Отчетсво\n"
            f"Email\n"
            f"Является администратором (Да/Нет)",
            reply_markup=markup
        )
    else:
        bt = get_main_button(True, user_id)
        await state.set_state(MainMenuStates.waiting_action)
        await message.reply("Чет вы ошиблись. Введите корректную команду.", reply_markup=bt)


@dp.message(UpdateUserDataForAdmin.waiting_what_to_update)
async def finish_update_for_admin_handler(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    state_data = await state.get_data()
    tg_user_for_update = state_data.get("tg_id")
    user_update = parse_update_by_admin_message(message.text)
    response = await update_user_api(user_id, user_update, int(tg_user_for_update))
    await state.clear()
    if isinstance(response, dict):
        await state.set_state(MainMenuStates.waiting_action)
        bt = get_main_button(True, user_id)
        answer = format_user_get_me(response)
        await message.reply(
            f"Успешное редактирование:"
            f"{answer}",

            reply_markup=bt
        )


@dp.message(UpdateUserData.waiting_what_to_update)
async def finish_update_for_user_handler(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    user_update = parse_update_message(message.text)
    response = await update_user_api(user_id, user_update, None)
    await state.clear()
    if isinstance(response, dict):
        await state.set_state(MainMenuStates.waiting_action)
        bt = get_main_button(True, user_id)
        answer = format_user_get_me(response)
        await message.reply(
            f"Успех!. Новые данные в базе:\n"
            f"{answer}",
            reply_markup=bt
        )


@dp.message(DeleteUserForAdmin.waiting_user)
async def delete_for_admin_handler(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    tg_id_for_delete = get_id_from_message(message.text)
    if isinstance(tg_id_for_delete, int):
        await state.clear()
        response = await delete_user_api(user_id, tg_id_for_delete)
        if response:
            await state.set_state(MainMenuStates.waiting_action)
            bt = get_main_button(True, user_id)
            await message.reply(
                f"{response}\n"
                f"Что-то еще?",
                reply_markup=bt
            )
        else:
            await state.set_state(MainMenuStates.waiting_action)
            bt = get_main_button(True, user_id)
            await message.reply(
                f"Что-то пошло не так.",
                reply_markup=bt
            )


@dp.message(SelectUserData.waiting_what_to_get)
async def get_user_for_admin_handler(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    tg_id_for_get = get_id_from_message(message.text)
    if isinstance(tg_id_for_get, int):
        await state.clear()
        response = await get_user_api(user_id, True, tg_id_for_get)
        if isinstance(response, dict):
            bt = get_main_button(True, user_id)
            await state.set_state(MainMenuStates.waiting_action)
            answer = format_user_get_me(response)
            await message.reply(
                f"{answer}",
                reply_markup=bt
            )


@dp.message(TimeControl.waiting_action)
async def timecontrol_action_selection_handler(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    if message.text == "Поставить отметку о начале работы":
        bt = get_main_button(True, user_id)
        await state.set_state(MainMenuStates.waiting_action)
        response = await time_control_api(user_id, True)
        if isinstance(response, str):
            await message.reply(
                f"{response}",
                reply_markup=bt
            )
    elif message.text == "Поставить отметку о конце работы":
        bt = get_main_button(True, user_id)
        await state.set_state(MainMenuStates.waiting_action)
        response = await time_control_api(user_id, False)
        if isinstance(response, str):
            await message.reply(
                f"{response}",
                reply_markup=bt
            )
    elif message.text == "Посмотреть свои отчеты за период":
        await state.set_state(TimeControl.waiting_date_report)
        markup = types.ReplyKeyboardRemove()
        await message.reply("Введите период в формате:\n"
                            "c dd/mm/yyyy\n"
                            "по dd/mm/yyyy\n"
                            "('c' и 'по' писать не нужно)", reply_markup=markup)
    elif message.text == "Посмотреть отчеты выбранного пользователя":
        users = await get_all_users_api(user_id, False)
        if isinstance(users, list):
            bt = get_update_user_for_admin_button(user_id, users)
            await state.set_state(TimeControl.waiting_select_user)
            await message.reply("Выберите пользователя", reply_markup=bt)


@dp.message(TimeControl.waiting_select_user)
async def user_for_report_selection_handler(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    tg_id = get_id_from_message(message.text)
    if isinstance(tg_id, int):
        await state.update_data(tg_id=tg_id)
        await state.set_state(TimeControl.waiting_date_report)
        markup = types.ReplyKeyboardRemove()
        await message.reply("Введите период в формате:\n"
                            "c dd/mm/yyyy\n"
                            "по dd/mm/yyyy\n"
                            "('c' и 'по' писать не нужно)", reply_markup=markup)


@dp.message(TimeControl.waiting_date_report)
async def period_selection_handler(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    date_start, date_end = parse_dates_from_message(message.text)
    state_data = await state.get_data()
    tg_user_get_report = state_data.get("tg_id")
    await state.clear()
    response = await get_report_time_control_api(user_id, date_start, date_end, tg_user_get_report)
    if isinstance(response, dict):
        if response.get("reports"):
            answer = parse_date_from_response(response.get("reports"))
        else:
            answer = "Нет отчетов за данный период"
        bt = get_main_button(True, user_id)
        await state.set_state(MainMenuStates.waiting_action)
        await message.answer(
            f"{answer}",
            reply_markup=bt
        )