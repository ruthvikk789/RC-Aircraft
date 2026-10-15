# Open-Source Albatross-Inspired Solar RC Aircraft Optimization Tool

A lightweight, first-order Python calculator and engineering record for a 2.0 m span RC aircraft concept using a three-segment dihedral wing and thin-film photovoltaic (PV) surface. The reference section is GOE 174 (ALBATROS 5020). The calculator estimates wing loading effects through required lift coefficient and stall-speed equations, then tracks a simplified hourly solar, propulsion, avionics, and battery energy balance.

This repository describes a design study, not a flight-certified aircraft. Validate dimensions, mass properties, aerodynamic coefficients, electrical ratings, structural strength, radio range, and control direction before flight. Conduct initial flights in a suitable test area and within applicable local model-aircraft rules.

## Concept and engineering principles

The albatross-inspired concept seeks low induced drag through a high-aspect-ratio wing and efficient cruise. A three-panel dihedral arrangement can provide lateral restoring stability and accommodate the desired planform, but changes local flow, torsional stiffness, and load paths. The center panel and joints carry substantial bending and torsion; wooden spars, shear webs, and reinforced panel joins must be sized from design loads and verified by inspection and ground testing. Foam board alone is not a primary spar.

The GOE 174 profile identifies the intended section shape. The airfoil name by itself does not establish lift, drag, pitching moment, or stall behavior on this aircraft. Those depend on Reynolds number, surface finish, construction accuracy, angle of attack, and control-surface geometry. The script therefore uses the familiar lift relation

`L = 0.5 × rho × V² × S × CL`

and solves for required `CL` at each requested speed. Its estimated stall speed uses a user-selected `CLmax`; the default 1.2 is an explicit preliminary assumption, not a measured GOE 174 result. Obtain or measure airfoil polars and verify the finished aircraft's stall characteristics before relying on these estimates.

Solar contribution is modeled as `rated power density × active cell area × orientation/derating factor × hourly irradiance fraction`. The hourly energy balance compares PV output against motor and avionics loads, then stores surplus subject to a battery charge-efficiency assumption. The model does not infer motor input from airspeed, propeller efficiency, or aircraft drag. It does not model clouds, cell temperature, MPPT behavior, voltage sag, discharge limits, transient motor demand, thermal loads, or maximum flight-time extension. The supplied 100–200 W/m² is treated as electrical output density at reference conditions; confirm whether the panel specification is electrical output, incident solar power, or another rating before use.

## Supplied concept specifications

| Item | Concept value | Modeling treatment |
|---|---:|---|
| Airfoil | GOE 174 (ALBATROS 5020) | Reference geometry; no verified polar embedded |
| Wingspan | 2.0 m (also described as 6.0 ft) | Reference only; note 2.0 m is about 6.56 ft |
| Dihedral | Three progressive panel segments | No geometry or joint angles supplied |
| “Relative surface area” | 91.34 units² | Units/scale unspecified; not used as physical area |
| Base mass | 1.2 kg default | Replace with measured all-up baseline mass |
| Wing area | 0.4 m² default | Provisional executable default; measure actual planform |
| Added mass | 0 kg default | Enter measured combined additions with `--added-mass-kg` |
| Solar active area | 0.4 m² default | Provisional; set to actual cell coverage |
| PV output density | 100–200 W/m² | Default 150 W/m²; verify rating and test conditions |
| Motor draw | 120 W default | Illustrative input, not a prediction of cruise draw |
| Avionics load | 5 W default | Illustrative receiver/servo/regulator allowance |
| Buffer battery | 0 Wh default | Enter measured usable capacity and initial energy |

The listed 2.0 m span, 6.0 ft span, 91.34 relative area units, and 0.4 m² provisional wing area do not uniquely define a consistent wing planform. Reconcile dimensions and units before structural or performance sizing.

## Bill of materials and tools

### Airframe and controls

- Foam-board fuselage, wing skins, and formers
- Internal wooden spars and suitable shear-web/reinforcement stock
- Adhesive suitable for the selected foam and wood (hot glue for compatible joints)
- Two analog servos, matched to control-surface loads
- Metal control rods, clevises or secure link ends, and control horns
- Radio receiver and transmitter with failsafe configured
- Brushless hobby motor, ESC, plastic propeller, and motor mount matched as a system
- Hinges or flexible hinge material for the two control surfaces
- Fasteners, wire, connectors, and strain relief appropriate to current and vibration

### Solar and power system

- Flexible photovoltaic film/panels, 2–3 mm nominal thickness as specified; confirm actual cell and encapsulation thickness
- MPPT or voltage-regulation hardware compatible with the panel's voltage/current curve and battery chemistry
- Lightweight buffer battery with protected charging/discharging and a documented usable energy rating
- Wiring, connectors, fuse/current protection, and telemetry sensors appropriate to measured current and voltage
- Optional irradiance and temperature sensors for validating the power model

### Workshop and validation tools

- Exacto knife with spare blades, straightedge, cutting mat, and measuring tape
- Hot-glue gun and compatible glue sticks
- Square, angle gauge, and incidence/dihedral measurement jig
- Digital scale, calipers, and center-of-gravity balancing stand
- Multimeter and wattmeter/current logger; battery charger with chemistry-appropriate settings
- Soldering equipment and heat-shrink for electrical assembly
- Propeller balancing tool and eye protection
- Low-speed airflow or flight-test instrumentation as available

Choose every component by its datasheet and measured operating limits. Verify that panel/controller/battery voltage and current ratings are compatible. Secure the propeller and remove it during bench electrical checks where practical. Keep hands and loose materials clear of a powered propeller.

## Calculator

### Requirements

- Python 3.10 or newer
- No third-party packages required (the implementation uses the Python standard library)

### Run

From this directory:

```console
python solar_aerodynamics_calculator.py
```

Provide measured project values as command-line options, for example:

```console
python solar_aerodynamics_calculator.py --base-mass-kg 1.35 --added-mass-kg 0.28 --wing-area-m2 0.52 --solar-area-m2 0.38 --solar-w-m2 150 --motor-w 95 --aux-w 4 --battery-wh 40 --battery-initial-wh 30
```

Use `python solar_aerodynamics_calculator.py --help` for all options. `--solar-factor` represents a lumped derating factor from 0 to 1 for orientation, mismatch, and wiring. The built-in hourly fractions are a generic daylight curve, not a location-specific weather forecast. The zero-capacity default intentionally shows the PV-only balance and will report unmet load whenever PV cannot supply it.

The output reports estimated aircraft mass, assumed stall speed, required lift coefficients, hourly PV and load power, net power, buffer state, unmet energy, and the number of modeled hours where instantaneous PV equals or exceeds the modeled load. Direct support in a given hour does not demonstrate sustainable flight: validate actual cruise power and continuous solar output in representative conditions. The script does not claim a precise flight-time extension because the required measured inputs and flight profile are not specified.

## Model scope and assumptions

- `updated mass = base mass + added mass`; added mass should include solar film, structural reinforcement, servos, wiring, regulator, battery, and any hardware not already in base mass.
- Required `CL` assumes steady, level flight, no gusts, and the supplied density and wing area.
- Stall speed is a preliminary estimate from assumed `CLmax`; it is not a safe operating target or flight-test result.
- Solar area is active cell area, not necessarily total wing planform area.
- Hourly generation and load are treated as average watts sustained for each one-hour interval, numerically equal to Wh for that interval.
- Buffer state is energy-based and does not model voltage, current limits, battery chemistry, temperature, or reserve policy.
- Thermal flight-system drain is not calculated because no thermal subsystem or load data were supplied.

## License

No license has been selected for this project. Add a license file before declaring the software, documentation, or hardware design open for reuse; do not assume that repository visibility alone grants reuse rights.
