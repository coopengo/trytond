import logging
import os

__all__ = ['SERVER', 'UTC', 'ZoneInfo', 'available_timezones']

logger = logging.getLogger(__name__)

try:
    import zoneinfo
    ZoneInfo = zoneinfo.ZoneInfo
    ZoneInfoNotFoundError = zoneinfo.ZoneInfoNotFoundError
except ImportError:
    import pytz
    from dateutil.tz import gettz as ZoneInfo
    zoneinfo = None

    class ZoneInfoNotFoundError(ValueError):
        pass


_ALL_ZONES = None


def available_timezones():
    global _ALL_ZONES

    if not _ALL_ZONES:
        if zoneinfo:
            _ALL_ZONES = sorted(zoneinfo.available_timezones())
        else:
            _ALL_ZONES = sorted(pytz.all_timezones)
    return _ALL_ZONES[:]


def _get_zoneinfo(key):
    try:
        zi = ZoneInfo(key)
        if not zoneinfo and not zi:
            raise ZoneInfoNotFoundError
    except ZoneInfoNotFoundError:
        logger.error("Timezone %s not found falling back to UTC", key)
        zi = UTC
    return zi


UTC = ZoneInfo('UTC')
SERVER = _get_zoneinfo(os.environ['TRYTOND_TZ'])
