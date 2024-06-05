from datetime import datetime
import pytz

class DayLightSaving:

    def __init__(self) -> None:
        pass

    def is_dst_in_toronto(self):
        toronto_tz = pytz.timezone('America/Toronto')
        toronto_time = datetime.now(toronto_tz)
        return bool(toronto_time.dst())