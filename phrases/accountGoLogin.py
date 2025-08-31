# phrases/accountGoLogin.py

go_login_menu_text = '<b>⚙️ Управление GoLogin аккаунтами</b>'
paginator_gologin_text = lambda page, pages: f'<b>Страница {page} из {pages}</b>'

create_go_login_text = '<b>Выберите способ добавления GoLogin аккаунта:</b>'
token_create_go_login_text = '<b>Введите API токен вашего GoLogin аккаунта:</b>'
create_go_login_success_text = '✅ Аккаунт GoLogin успешно добавлен!'
create_go_login_error_text = '<b>❌ Ошибка при добавлении аккаунта GoLogin.</b>'
wait_create_go_login_text = '<b>🤖 Создаю новый аккаунт GoLogin, это может занять несколько минут...</b>'

# Красочное оформление для просмотра аккаунта
go_login_account_text = lambda account: (
    f"<b>✨ Аккаунт GoLogin ID: {account.id} ✨</b>\n\n"
    f"<b>📧 Почта:</b> <code>{account.email_address}</code>\n"
    f"<b>🔑 Токен:</b> <code>{account.api_token}</code>\n" # Показываем только часть токена
    f"<b>📅 Дата добавления:</b> {account.registration_date.strftime('%d.%m.%Y')}\n"
    f"<b>🚦 Статус:</b> {'✅ Активен' if account.valid else '⚠️ Исчерпан лимит'}"
)

# Фразы для удаления
confirm_delete_gologin_text = lambda account_id: f'<b>🗑 Вы уверены, что хотите удалить GoLogin аккаунт ID {account_id}?\n\nЭто действие необратимо!</b>'
gologin_deleted_text = '<b>✅ Аккаунт GoLogin успешно удален.</b>'