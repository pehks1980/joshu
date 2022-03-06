import datetime


# вычисление времени с учетом часового пояса пользователя только для вывода в чат-бот
def get_calc_time_tz(inst_task, default_time):
    if default_time:
        new_time = default_time
        if not inst_task.task_user.user_time_zone:
            return default_time
        user_tz_value = datetime.timedelta(0, inst_task.task_user.user_time_zone)  # datetime.timedelta([дни], [сек])
        print(f'user_tz_value = {user_tz_value}, new_time={new_time}')
        if inst_task.task_user.user_time_zone_character:
            new_time += user_tz_value
        else:
            new_time -= user_tz_value
        # print(f'new_time = {new_time}')
        return new_time
    return None


def text_massage_about_the_task(current_task):
    time_format = "%d.%m.%Y %H:%M"

    if current_task.dateTime:
        user_time_value = current_task.dateTime.astimezone(current_task.task_user.tz)
        text_messg = f'{current_task.id} - {current_task.text}, ' \
                     f'\nсрок исполнения: {user_time_value.strftime(time_format)}'
    else:
        text_messg = f'{current_task.id} - "{current_task.text}", ' \
                     f'срок исполнения задачи не указан, укажите срок исполнения!'
    return text_messg
