from datetime import timedelta, date


class Weekday():
    MON = 0
    TUE = 1
    WED = 2
    THU = 3
    FRI = 4
    SAT = 5
    SUN = 6


class BusinessHoliday():
    def __init__(o, month, day_or_week_day):
        o.month = month
        o.week = None
        o.day = None
        if type(day_or_week_day) == int:
            o.day = day_or_week_day
        elif type(day_or_week_day) == tuple:
            (o.week, o.weekday) = day_or_week_day
        else:
            raise Exception()

    def occurs_in(o, year):
        if o.day:
            return date(year, o.month, o.day)
        else:
            dateIndex = date(year, o.month, 1)
            weekIndex = 0
            while True:
                if dateIndex.weekday() == o.weekday:
                    weekIndex += 1
                    if (weekIndex == o.week):
                        return date(year, o.month, dateIndex.day)
                dateIndex = dateIndex + timedelta(days=1)
                if dateIndex.month != o.month:
                    return None


class BusinessCalendar():
    def __init__(o, workdays=None, holidays=None):
        if not workdays:
            o.workdays = [Weekday.MON,
                          Weekday.TUE,
                          Weekday.WED,
                          Weekday.THU,
                          Weekday.FRI]
        else:
            o.workdays = workdays
        o.holidays = holidays

    def workdays_between(o, from_date, thru_date):
        from_date = date(from_date.year, from_date.month, from_date.day)
        thru_date = date(thru_date.year, thru_date.month, thru_date.day)
        startDate = from_date
        if from_date.year == thru_date.year:
            if from_date.month == thru_date.month:
                if from_date.day == thru_date.day:
                    return 0
        while from_date.weekday() not in o.workdays:
            from_date = from_date + timedelta(days=1)
        while thru_date.weekday() not in o.workdays:
            thru_date = thru_date - timedelta(days=1)
        if thru_date <= from_date:
            return 1
        else:
            dayCount = 0
            currentYear = None
            yearHolidays = []
            while from_date <= thru_date:
                if from_date.year != currentYear:
                    currentYear = from_date.year
                    yearHolidays = map(lambda x: x.occurs_in(currentYear),
                                       o.holidays)
                if (from_date.weekday() in o.workdays) and  \
                   (from_date not in yearHolidays) and  \
                   (from_date != startDate):
                    dayCount += 1
                from_date = from_date + timedelta(days=1)
            return dayCount
