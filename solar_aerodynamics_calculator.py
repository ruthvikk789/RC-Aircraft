#!/usr/bin/env python3
"""First-order sizing model for an albatross-inspired solar RC aircraft.

The model is deliberately transparent: values absent from the sketch are
explicit assumptions and can be changed in ``DEFAULTS`` or with CLI options.
It is not a substitute for measured mass, airfoil polars, or flight testing.
Only the Python standard library is required.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Sequence

GRAVITY_M_S2 = 9.80665


@dataclass(frozen=True)
class Aircraft:
    base_mass_kg: float = 1.2
    wing_area_m2: float = 0.4
    air_density_kg_m3: float = 1.225
    added_mass_kg: float = 0.0
    max_lift_coefficient: float = 1.2


@dataclass(frozen=True)
class SolarSystem:
    active_panel_area_m2: float = 0.4
    rated_power_density_w_m2: float = 150.0
    motor_power_w: float = 120.0
    auxiliary_power_w: float = 5.0
    panel_efficiency_factor: float = 1.0
    battery_capacity_wh: float = 0.0
    initial_battery_wh: float = 0.0
    battery_charge_efficiency: float = 0.90
    irradiance_fractions: tuple[float, ...] = (0.0, 0.15, 0.4, 0.65, 0.8, 0.9,
                                                 0.95, 0.9, 0.8, 0.6, 0.35, 0.1)


DEFAULTS = Aircraft()


def calculate_structural_mass_and_lift_profiles(
    base_mass_kg: float = 1.2,
    panel_area_m2: float = 0.4,
    air_density: float = 1.225,
    *,
    added_mass_kg: float = 0.0,
    max_lift_coefficient: float = 1.2,
    velocities_m_s: Sequence[float] = (8.0, 10.0, 12.0, 15.0, 18.0),
) -> dict[str, object]:
    """Return mass, stall speed estimate, and required CL at target speeds.

    ``added_mass_kg`` is the combined measured/estimated mass of added spars,
    servos, linkages, solar laminate, regulator, wiring and battery. It defaults
    to zero because component masses were not supplied. ``max_lift_coefficient``
    is an assumed clean-wing value, not a verified GOE 174 polar.
    """
    if base_mass_kg <= 0 or panel_area_m2 <= 0 or air_density <= 0:
        raise ValueError("mass, wing area and air density must be positive")
    if added_mass_kg < 0 or max_lift_coefficient <= 0:
        raise ValueError("added mass must be nonnegative and max CL positive")
    mass = base_mass_kg + added_mass_kg
    weight_n = mass * GRAVITY_M_S2
    stall_speed = math.sqrt(2.0 * weight_n / (air_density * panel_area_m2 * max_lift_coefficient))
    profiles = []
    for speed in velocities_m_s:
        if speed <= 0:
            raise ValueError("target velocities must be positive")
        cl = 2.0 * weight_n / (air_density * speed**2 * panel_area_m2)
        profiles.append({"velocity_m_s": speed, "required_cl": cl,
                         "below_assumed_stall": speed < stall_speed})
    return {"updated_mass_kg": mass, "weight_n": weight_n,
            "estimated_stall_speed_m_s": stall_speed,
            "estimated_stall_speed_km_h": stall_speed * 3.6,
            "profiles": profiles}


def evaluate_dihedral_solar_power_balance(
    efficiency_watts_m2: float = 150.0,
    motor_draw_watts: float = 120.0,
    *,
    panel_area_m2: float = 0.4,
    auxiliary_power_w: float = 5.0,
    panel_efficiency_factor: float = 1.0,
    battery_capacity_wh: float = 0.0,
    initial_battery_wh: float = 0.0,
    battery_charge_efficiency: float = 0.90,
    irradiance_fractions: Sequence[float] = SolarSystem().irradiance_fractions,
) -> dict[str, object]:
    """Simulate hourly solar generation and battery energy for one day.

    Rated power density is treated as available electrical output at reference
    irradiance; hourly fractions encode irradiance and incidence losses together.
    Net power is PV output minus motor and avionics draw. Positive surplus is
    stored at the specified charge efficiency; deficits draw from the buffer.
    No thermal-flight drain is modeled: no thermal load or thermal coupling data
    were supplied. Battery depletion is reported as an unmet-power interval.
    """
    if efficiency_watts_m2 < 0 or motor_draw_watts < 0 or auxiliary_power_w < 0:
        raise ValueError("power values must be nonnegative")
    if panel_area_m2 < 0 or not 0 <= panel_efficiency_factor <= 1:
        raise ValueError("panel area must be nonnegative and factor in [0, 1]")
    if battery_capacity_wh < 0 or not 0 <= initial_battery_wh <= battery_capacity_wh:
        raise ValueError("battery state must be between zero and capacity")
    if not 0 < battery_charge_efficiency <= 1:
        raise ValueError("battery charge efficiency must be in (0, 1]")
    if any(not 0 <= f <= 1 for f in irradiance_fractions):
        raise ValueError("irradiance fractions must be in [0, 1]")

    state = initial_battery_wh
    rows = []
    unmet_hours = 0.0
    for hour, fraction in enumerate(irradiance_fractions):
        pv = efficiency_watts_m2 * panel_area_m2 * panel_efficiency_factor * fraction
        load = motor_draw_watts + auxiliary_power_w
        net = pv - load
        if net >= 0:
            accepted = min(net * battery_charge_efficiency, battery_capacity_wh - state)
            state += accepted
            unaccepted = net - accepted / battery_charge_efficiency
            battery_delta = accepted
            unmet = 0.0
        else:
            deficit_wh = -net
            supplied = min(deficit_wh, state)
            state -= supplied
            battery_delta = -supplied
            unmet = max(0.0, deficit_wh - supplied)
            if unmet > 0:
                unmet_hours += 1.0
            unaccepted = 0.0
        rows.append({"hour": hour, "irradiance_fraction": fraction,
                     "pv_power_w": pv, "load_power_w": load, "net_power_w": net,
                     "battery_change_wh": battery_delta, "battery_state_wh": state,
                     "unmet_energy_wh": unmet, "curtailed_pv_wh": unaccepted})
    return {"hours_simulated": len(rows), "generation_wh": sum(r["pv_power_w"] for r in rows),
            "load_wh": sum(r["load_power_w"] for r in rows),
            "net_energy_before_storage_wh": sum(r["net_power_w"] for r in rows),
            "ending_battery_wh": state, "unmet_power_hours": unmet_hours,
            "direct_sustain_hours": sum(1 for r in rows if r["pv_power_w"] >= r["load_power_w"]),
            "hourly": rows}


def _report(air: dict[str, object], power: dict[str, object]) -> str:
    lines = [
        "Open-Source Albatross-Inspired Solar RC Aircraft Optimization Tool",
        "First-order engineering estimate; validate all inputs before flight.",
        "",
        f"Updated mass: {air['updated_mass_kg']:.3f} kg (weight {air['weight_n']:.2f} N)",
        f"Estimated stall speed: {air['estimated_stall_speed_m_s']:.2f} m/s "
        f"({air['estimated_stall_speed_km_h']:.1f} km/h), assuming CLmax=1.20",
        "Required lift coefficient by target speed:",
    ]
    for p in air["profiles"]:
        lines.append(f"  {p['velocity_m_s']:5.1f} m/s: CL={p['required_cl']:.3f}"
                     + (" (below estimated stall)" if p["below_assumed_stall"] else ""))
    lines += ["", f"Solar generation: {power['generation_wh']:.1f} Wh across "
              f"{power['hours_simulated']} simulated hours",
              f"Aircraft load: {power['load_wh']:.1f} Wh; net before storage: "
              f"{power['net_energy_before_storage_wh']:.1f} Wh",
              f"PV directly meets motor and avionics load in {power['direct_sustain_hours']} hours",
              f"Buffer energy at end: {power['ending_battery_wh']:.1f} Wh; "
              f"unmet-power intervals: {power['unmet_power_hours']:.0f}",
              "Maximum flight-time extension: not established by this model. "
              "It requires measured propulsive power, usable battery energy, and a defined flight profile.",
              "Thermal load/drain: not modeled; no thermal subsystem parameters were provided.",
              "Hourly balance (0-23 local-independent simulation hour):"]
    for row in power["hourly"]:
        lines.append(f"  {row['hour']:02d}: PV {row['pv_power_w']:6.1f} W | "
                     f"load {row['load_power_w']:6.1f} W | net {row['net_power_w']:7.1f} W | "
                     f"battery {row['battery_state_wh']:6.1f} Wh | "
                     f"unmet {row['unmet_energy_wh']:6.1f} Wh")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-mass-kg", type=float, default=1.2)
    parser.add_argument("--added-mass-kg", type=float, default=0.0,
                        help="measured mass of all additions (kg); default 0")
    parser.add_argument("--wing-area-m2", type=float, default=0.4)
    parser.add_argument("--cl-max", type=float, default=1.2,
                        help="assumed maximum lift coefficient")
    parser.add_argument("--solar-area-m2", type=float, default=0.4)
    parser.add_argument("--solar-w-m2", type=float, default=150.0)
    parser.add_argument("--motor-w", type=float, default=120.0)
    parser.add_argument("--aux-w", type=float, default=5.0)
    parser.add_argument("--battery-wh", type=float, default=0.0)
    parser.add_argument("--battery-initial-wh", type=float, default=0.0)
    parser.add_argument("--solar-factor", type=float, default=1.0,
                        help="lumped orientation, mismatch and wiring factor (0-1)")
    args = parser.parse_args()
    air = calculate_structural_mass_and_lift_profiles(
        args.base_mass_kg, args.wing_area_m2, added_mass_kg=args.added_mass_kg,
        max_lift_coefficient=args.cl_max)
    power = evaluate_dihedral_solar_power_balance(
        args.solar_w_m2, args.motor_w, panel_area_m2=args.solar_area_m2,
        auxiliary_power_w=args.aux_w, panel_efficiency_factor=args.solar_factor,
        battery_capacity_wh=args.battery_wh, initial_battery_wh=args.battery_initial_wh)
    print(_report(air, power))


if __name__ == "__main__":
    main()
