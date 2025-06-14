"""Timezone utilities for robust temporal data handling.

This module provides utilities for timezone conversion, validation, and handling
of edge cases like DST transitions and timezone changes.
"""

import zoneinfo
from datetime import UTC, datetime, timedelta
from typing import Any

from .logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class TimezoneError(Exception):
    """Custom exception for timezone-related errors."""

    pass


class TimezoneUtils:
    """Utility class for timezone operations."""

    # Common timezone mappings for user convenience
    TIMEZONE_ALIASES = {
        "UTC": "UTC",
        "GMT": "UTC",
        "EST": "America/New_York",
        "PST": "America/Los_Angeles",
        "CST": "America/Chicago",
        "MST": "America/Denver",
        "CET": "Europe/Berlin",
        "JST": "Asia/Tokyo",
        "IST": "Asia/Kolkata",
        "AEST": "Australia/Sydney",
    }

    @classmethod
    def validate_timezone(cls, timezone_str: str) -> str:
        """Validate and normalize timezone string.

        Args:
            timezone_str: Timezone string to validate

        Returns:
            Normalized timezone string

        Raises:
            TimezoneError: If timezone is invalid
        """
        if not timezone_str:
            raise TimezoneError("Timezone string cannot be empty")

        # Check if it's an alias
        if timezone_str in cls.TIMEZONE_ALIASES:
            timezone_str = cls.TIMEZONE_ALIASES[timezone_str]

        # Validate timezone exists
        try:
            if timezone_str == "UTC":
                return timezone_str
            zoneinfo.ZoneInfo(timezone_str)
            return timezone_str
        except zoneinfo.ZoneInfoNotFoundError as e:
            raise TimezoneError(f"Invalid timezone: {timezone_str}") from e

    @classmethod
    def ensure_utc(cls, dt: datetime) -> datetime | None:
        """Ensure datetime is in UTC timezone.

        Args:
            dt: Datetime object to convert

        Returns:
            Datetime in UTC timezone

        Raises:
            TimezoneError: If datetime conversion fails
        """
        if dt is None:
            return None

        try:
            if dt.tzinfo is None:
                # Naive datetime - assume UTC
                logger.warning(
                    f"Naive datetime {dt} assumed to be UTC. "
                    "Consider providing timezone-aware datetimes."
                )
                return dt.replace(tzinfo=UTC)
            elif dt.tzinfo == UTC:
                # Already UTC
                return dt
            else:
                # Convert to UTC
                return dt.astimezone(UTC)
        except Exception as e:
            raise TimezoneError(f"Failed to convert datetime to UTC: {e}") from e

    @classmethod
    def convert_to_timezone(cls, dt: datetime, target_timezone: str) -> datetime | None:
        """Convert UTC datetime to target timezone.

        Args:
            dt: UTC datetime to convert
            target_timezone: Target timezone string

        Returns:
            Datetime in target timezone

        Raises:
            TimezoneError: If conversion fails
        """
        if dt is None:
            return None

        try:
            # Validate and normalize timezone
            target_tz_str = cls.validate_timezone(target_timezone)

            # Ensure input is UTC
            utc_dt = cls.ensure_utc(dt)
            if utc_dt is None:
                return None

            # Convert to target timezone
            if target_tz_str == "UTC":
                return utc_dt
            else:
                target_tz = zoneinfo.ZoneInfo(target_tz_str)
                return utc_dt.astimezone(target_tz)

        except Exception as e:
            raise TimezoneError(
                f"Failed to convert datetime to {target_timezone}: {e}"
            ) from e

    @classmethod
    def convert_from_timezone(
        cls, dt: datetime, source_timezone: str
    ) -> datetime | None:
        """Convert datetime from source timezone to UTC.

        Args:
            dt: Datetime in source timezone
            source_timezone: Source timezone string

        Returns:
            Datetime in UTC

        Raises:
            TimezoneError: If conversion fails
        """
        if dt is None:
            return None

        try:
            # Validate and normalize timezone
            source_tz_str = cls.validate_timezone(source_timezone)

            if source_tz_str == "UTC":
                return cls.ensure_utc(dt)

            # If datetime is naive, localize it to source timezone
            if dt.tzinfo is None:
                source_tz = zoneinfo.ZoneInfo(source_tz_str)
                localized_dt = dt.replace(tzinfo=source_tz)
            else:
                localized_dt = dt

            # Convert to UTC
            return localized_dt.astimezone(UTC)

        except Exception as e:
            raise TimezoneError(
                f"Failed to convert datetime from {source_timezone}: {e}"
            ) from e

    @classmethod
    def is_dst_transition(cls, dt: datetime, timezone_str: str) -> dict[str, Any]:
        """Check if datetime falls during a DST transition.

        Args:
            dt: Datetime to check
            timezone_str: Timezone to check in

        Returns:
            Dictionary with DST transition information

        Raises:
            TimezoneError: If timezone validation fails
        """
        if dt is None:
            return {"is_transition": False}

        try:
            # Validate timezone
            tz_str = cls.validate_timezone(timezone_str)

            if tz_str == "UTC":
                return {"is_transition": False, "reason": "UTC has no DST"}

            tz = zoneinfo.ZoneInfo(tz_str)

            # Check the hour before and after for DST changes
            before = dt - timedelta(hours=1)
            after = dt + timedelta(hours=1)

            try:
                before_offset = before.replace(tzinfo=tz).utcoffset()
                current_offset = dt.replace(tzinfo=tz).utcoffset()
                after_offset = after.replace(tzinfo=tz).utcoffset()
            except Exception:
                # Handle non-existent times during spring forward
                # If we can't get the current offset, it's likely a spring forward transition
                try:
                    before_offset = before.replace(tzinfo=tz).utcoffset()
                    after_offset = after.replace(tzinfo=tz).utcoffset()

                    # If before and after have different offsets, it's a transition
                    if (
                        before_offset != after_offset
                        and before_offset is not None
                        and after_offset is not None
                    ):
                        # Spring forward: offset increases (becomes less negative)
                        if before_offset < after_offset:
                            return {
                                "is_transition": True,
                                "transition_type": "spring_forward",
                                "before_offset": str(before_offset),
                                "current_offset": "non-existent",
                                "after_offset": str(after_offset),
                            }
                        # Fall back: offset decreases (becomes more negative)
                        else:
                            return {
                                "is_transition": True,
                                "transition_type": "fall_back",
                                "before_offset": str(before_offset),
                                "current_offset": "ambiguous",
                                "after_offset": str(after_offset),
                            }
                except Exception:
                    return {
                        "is_transition": False,
                        "error": "Could not determine transition",
                    }

            # Check for transitions based on offset changes
            # Spring forward: offset increases (becomes less negative) between any adjacent periods
            spring_forward = (
                before_offset is not None
                and current_offset is not None
                and after_offset is not None
                and (
                    (before_offset < current_offset) or (current_offset < after_offset)
                )
            )
            # Fall back: offset decreases (becomes more negative) between any adjacent periods
            fall_back = (
                before_offset is not None
                and current_offset is not None
                and after_offset is not None
                and (
                    (before_offset > current_offset) or (current_offset > after_offset)
                )
                and not spring_forward
            )

            return {
                "is_transition": spring_forward or fall_back,
                "transition_type": (
                    "spring_forward"
                    if spring_forward
                    else "fall_back" if fall_back else None
                ),
                "before_offset": str(before_offset),
                "current_offset": str(current_offset),
                "after_offset": str(after_offset),
            }

        except Exception as e:
            raise TimezoneError(f"Failed to check DST transition: {e}") from e

    @classmethod
    def get_timezone_info(cls, timezone_str: str) -> dict[str, Any]:
        """Get comprehensive information about a timezone.

        Args:
            timezone_str: Timezone string

        Returns:
            Dictionary with timezone information

        Raises:
            TimezoneError: If timezone validation fails
        """
        try:
            # Validate timezone
            tz_str = cls.validate_timezone(timezone_str)

            if tz_str == "UTC":
                return {
                    "timezone": "UTC",
                    "current_offset": "+00:00",
                    "dst_active": False,
                    "dst_name": None,
                    "standard_name": "UTC",
                }

            tz = zoneinfo.ZoneInfo(tz_str)
            now = datetime.now(tz)

            return {
                "timezone": tz_str,
                "current_offset": now.strftime("%z"),
                "dst_active": bool(now.dst()),
                "dst_name": now.tzname() if now.dst() else None,
                "standard_name": now.tzname(),
                "utc_offset_seconds": (
                    int(offset.total_seconds()) if (offset := now.utcoffset()) else 0
                ),
            }

        except Exception as e:
            raise TimezoneError(f"Failed to get timezone info: {e}") from e

    @classmethod
    def format_datetime_for_timezone(
        cls, dt: datetime, timezone_str: str, format_str: str = "%Y-%m-%d %H:%M:%S %Z"
    ) -> str:
        """Format datetime for display in a specific timezone.

        Args:
            dt: UTC datetime to format
            timezone_str: Target timezone for display
            format_str: Format string for datetime

        Returns:
            Formatted datetime string

        Raises:
            TimezoneError: If formatting fails
        """
        if dt is None:
            return "None"

        try:
            # Convert to target timezone
            local_dt = cls.convert_to_timezone(dt, timezone_str)
            if local_dt is None:
                return "None"
            return local_dt.strftime(format_str)

        except Exception as e:
            raise TimezoneError(f"Failed to format datetime: {e}") from e

    @classmethod
    def parse_datetime_with_timezone(
        cls, datetime_str: str, timezone_str: str, format_str: str = "%Y-%m-%d %H:%M:%S"
    ) -> datetime | None:
        """Parse datetime string in a specific timezone and convert to UTC.

        Args:
            datetime_str: Datetime string to parse
            timezone_str: Timezone of the datetime string
            format_str: Format string for parsing

        Returns:
            UTC datetime

        Raises:
            TimezoneError: If parsing fails
        """
        if not datetime_str:
            return None

        try:
            # Parse the datetime string
            naive_dt = datetime.strptime(datetime_str, format_str)

            # Convert from source timezone to UTC
            return cls.convert_from_timezone(naive_dt, timezone_str)

        except Exception as e:
            raise TimezoneError(f"Failed to parse datetime: {e}") from e

    @classmethod
    def get_available_timezones(cls) -> list[str]:
        """Get list of available timezone identifiers.

        Returns:
            List of timezone identifiers
        """
        try:
            # Get all available timezones
            all_zones = list(zoneinfo.available_timezones())

            # Add common aliases
            aliases = list(cls.TIMEZONE_ALIASES.keys())

            # Combine and sort
            combined = sorted(set(all_zones + aliases))

            return combined

        except Exception as e:
            logger.error(f"Failed to get available timezones: {e}")
            return ["UTC"]  # Fallback to UTC only
