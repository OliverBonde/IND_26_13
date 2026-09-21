
# A1 submission

1. Group 13

2. Focus area: Indoor (acoustics)

3. issue: Thermal transmittance of new outer walls = 0,12

4. solution: Check if the walls have the same thermal transmittance (U-value) as stated in the report

5. The report 26-01-D-MEP-Anon - page 2 section 2.1 & 
ifc model:26-01-D-ARCH

## Description of script

The report contains a description of the new exterior wall to be constructed as part of their project. The description states that they aim to achieve an exterior wall with a U-value of 0.12 W/m²K.

To check whether this information is included in the IFC model, a script has been developed that examines all walls using IfcOpenShell's `get_psets` function. This identifies the property sets for walls categorized as "New Wall", after which the `ThermalTransmittance` value is printed for all walls that meet the "New Wall" category.

Result from the script: U-value of wall: **0.88 W/(m²·K)**


