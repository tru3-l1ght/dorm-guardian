def decide_fan_state(
    temperature_c: float,
    current_state: bool,
    automation_enabled: bool = True,
) -> tuple[bool, str]:
    if not automation_enabled:
        return current_state, "Automation disabled"

    if temperature_c >= 28.0:
        return True, "Temperature is at or above 28.0°C"

    if temperature_c <= 26.5:
        return False, "Temperature is at or below 26.5°C"

    return current_state, "Temperature is within hysteresis range"