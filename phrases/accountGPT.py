# phrases/accountGPT.py

gpt_menu_text = '<b>🤖 Управление аккаунтами ChatGPT</b>'
paginator_text = lambda page, pages: f'<b>Страница {page} из {pages}</b>'

# --- Создание ---
choice_create_gpt_account_text = '<b>Выберите способ создания аккаунта:</b>'
auto_create_sb_text = '<b>⚙️ Автоматическое создание</b>' # Новое имя для кнопки
auto_create_name_prompt_text = '<b>Введите имя для нового аккаунта:</b>'

# --- Ручное создание ---
gpt_manual_prompt_text = '<b>Введите данные аккаунта в формате:\n\n<code>email:пароль:имя_в_боте</code></b>'
wait_manual_create_gpt_account_text = '<b>⚙️ Создаю профиль и захожу в аккаунт, ожидайте...</b>'
create_gpt_account_success_text = '<b>✅ Аккаунт успешно создан и запущен!</b>'
create_gpt_account_error_text = '<b>❌ Создать аккаунт не удалось, попробуйте позже.</b>'
no_valid_gologin_accounts_error = '<b>❌ Не найдено ни одного активного GoLogin аккаунта. Сначала добавьте его в соответствующем меню.</b>'
gologin_link_error_text = '<b>❌ Привязанный GoLogin аккаунт не найден или невалиден.</b>' # Новая фраза

# --- Просмотр аккаунта ---
# Более красочное оформление с использованием HTML
gpt_account_text = lambda account: (f'<b>✨ Аккаунт: «{account.name}» ✨</b>\n\n'
                                    f'<b>📧 Почта:</b> <code>{account.email_address}</code>\n'
                                    f'<b>🔑 Пароль:</b> <code>{account.password}</code>\n'
                                    f'<b>🆔 ID профиля:</b> <code>{account.id}</code>')

# --- Переименование ---
rename_prompt_text = '<b>✏️ Введите новое имя для аккаунта:</b>'
rename_success_text = '<b>✅ Аккаунт успешно переименован!</b>'

# --- Удаление ---
confirm_delete_text = lambda account_name: f'<b>🗑 Вы уверены, что хотите удалить аккаунт «{account_name}»?\n\nЭто действие необратимо!</b>'
account_deleted_text = '✅ Аккаунт успешно удален.'

# --- Запуск ---
launch_account_gpt_text = '<b>🚀 Запускаю профиль, это может занять до минуты...</b>'
error_launch_account_gpt_text = '<b>❌ Ошибка запуска аккаунта, попробуйте позже\n</b>'

# --- Прочее ---
chatgpt_error_format_text = "<b>⚠️ Формат неверный, введите: <code>email:пароль:имя_в_боте</code></b>"
code_input_text = '<b>⚠️ Требуется код 2FA. Отправьте его следующим сообщением.</b>' # Перенесено из хэндлера

# --- AutoGoLogin ---
gologin_autocreate_start_text = "<b>⚠️ Свободные GoLogin аккаунты закончились.\n\n🤖 Запускаю процесс автоматического создания нового аккаунта...</b>"
gologin_autocreate_success_text = lambda email: f"<b>✅ Новый GoLogin аккаунт успешно создан и готов к работе!\n\n📧 Почта: <code>{email}</code></b>"
