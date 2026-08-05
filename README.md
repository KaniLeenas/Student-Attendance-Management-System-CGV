# Student-Attendance-Management-System-CGV
Student Attendance Management System (SAMS) that uses image processing, data visualization, and optionally signature recognition.
shakeef
# Student Attendance Management System (SAMS)

SAMS is an automated attendance management system using Computer Vision & Graphics (CVG) techniques for processing attendance sheets, table detection, signature detection, verification, and web-based management.

## Project Structure & Modules

- **M1: Core Setup & Auth**: Configuration, Database management, Authentication (`config.py`, `manage_users.py`, `core/database.py`, `core/auth.py`)
- **M2: Preprocessing & Utilities**: Image processing helpers (`core/utils.py`, `core/preprocess.py`)
- **M3: Table Detection**: Detecting attendance grid tables (`core/table_detector.py`)
- **M4: Signature Detection**: Extraction & detection of signatures (`core/signature_detector.py`)
- **M5: XML Parser & CLI Pipeline**: Data parsing & main execution pipeline (`info.xml`, `sams.py`, `core/xml_parser.py`, `core/pipeline.py`)
- **M6: Visualization & Analytics**: Info visualization scripts (`infovis.py`, `core/visualization.py`, `static/js/app.js`)
- **M7: Signature Verification**: Verification & investigation routines (`investigate.py`, `core/signature_verify.py`)
- **M8: Web Application**: Flask web application & templates (`app.py`, `templates/`, `static/css/style.css`)
