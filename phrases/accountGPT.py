gpt_menu_text = '🤖 Управление ChatGPT аккаунтами'
choice_create_gpt_account_text = 'Выберите способ создания ChatGPT аккаунта:'
gpt_manual_prompt_text = 'Введите данные аккаунта в формате:\n\n`email:пароль:имя_в_боте`\n\nили нажмите «Назад».'

wait_manual_create_gpt_account_text = 'Захожу в аккаунт, ожидайте...'

create_gpt_account_success_text = '✅ Аккаунт ChatGPT успешно добавлен.\n'
gpt_account_text = lambda account: (f'Аккаунт: {account.id}\n'
                                    f'Имя: {account.name}\n'
                                    f'Почта: {account.email_address}\n'
                                    f'Пароль: {account.password}\n')
choose_go_login_account_text = 'Выберите аккаунт для входа:'
create_gpt_account_error_text = 'Создать аккаунт не удалось, попробуйте позже'

chatgpt_error_format_text = "⚠️ Формат неверный, введите: email:пароль:имя_в_боте"
launch_account_gpt_text = 'Аккаунт запущен! \n'
error_launch_account_gpt_text = 'Ошибка запуска аккаунта, попробуйте позже\n'