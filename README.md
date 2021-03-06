# SC MPS Display

## Directory Structure
.  
|-- README  
|-- RELEASE_NOTES  
|-- sc_mps_gui.bash  
|-- mps_gui_main.ui  
|-- mps_gui_main.py  
|-- mps_permit_panel.ui  
|-- mps_model.py  
`-- widget_constructors.py  


### sc_mps_gui.bash
  - Run the MPS Display with the specified DB file (if one is specified)
  - Usage:  
    `` sc_mps_gui.bash [filename] ``

  - Examples:  
    `` sc_mps_gui.bash ``
    `` sc_mps_gui.bash faults.db ``


### mps_gui_main.py / mps_gui_main.ui
  - This is the main display for the SC MPS Display
  - Contains a tab widget with 2 tabs:
    - The Summary tab contains 6 embedded displays and 2 tables, one containg faulted PVs and one containing bypassed faults
    - The Logic tab contains a table of all faults in the database


### mps_permit_panel.ui
  - The permit panel display embedded in the Summary tab
  - Shows the Beam Class, Timing Beam Class, and Timing Rate


### mps_model.py
  - Using MPSConfig, establish a connection to the MPS Database
    - If a filename is not provided, then MPSModel will locate the default file to use
  - The object stores all necessary information from the database


### widget_constructors.py 
  - Functions used by mps_gui_main.py to create widgets for a given fault
  - Contains constructors for:
    - State Widget
    - Cell Widget
    - Bypass Widget
    - Bypass Table Row
    - Summary/Logic Table Row
