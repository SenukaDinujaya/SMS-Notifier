from datetime import datetime, timezone, timedelta
from pytz import timezone as tz

class EpochToDateTime:
    def __init__(self) -> None:
        pass
        
    def epoch_to_datetime(self, epoch_time):
        # Convert epoch time to datetime
        eastern = tz('America/Toronto')
        dt_object = datetime.fromtimestamp(epoch_time, tz=eastern)
        return dt_object.strftime('%Y-%m-%d %H:%M:%S')