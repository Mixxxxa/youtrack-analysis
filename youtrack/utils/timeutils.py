import pandas as pd
import datetime as dt


class UTC_BUSINESS_DAY_CONSTANTS:
    """Константы времени работы

    #TODO Вынести в конфиг
    """
    HOUR_BEGIN = 6
    HOUR_LUNCH_BEGIN = 10
    HOUR_LUNCH_END = 11
    HOUR_END = 15


def is_working_hour(dt: pd.Timestamp) -> bool:
    """Функция проверки что timestamp входит в рабочее время"""
    if dt.weekday() >= 5:  # Суббота и Воскресенье
        return False
    return (dt.hour >= UTC_BUSINESS_DAY_CONSTANTS.HOUR_BEGIN and dt.hour < UTC_BUSINESS_DAY_CONSTANTS.HOUR_LUNCH_BEGIN) or (dt.hour >= UTC_BUSINESS_DAY_CONSTANTS.HOUR_LUNCH_END and dt.hour < UTC_BUSINESS_DAY_CONSTANTS.HOUR_END)


def count_working_minutes(begin: dt.datetime, end: dt.datetime) -> int:
    """Возвращает количество рабочих минут между двумя точками во времени"""
    # Because date_range will create at least one element even if begin and end are equal
    if begin == end:
        return 0
    
    time_index: pd.Timestamp = pd.date_range(start=pd.to_datetime(begin), 
                                             end=pd.to_datetime(end), 
                                             freq='min',
                                             inclusive='left')
    return sum([is_working_hour(dt) for dt in time_index])