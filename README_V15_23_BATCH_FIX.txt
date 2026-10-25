VERSION 15.23 - WINDOWS LAUNCHER FIX

Important: This package is in a folder named Administrative_AI_System_v15_23_BATCH_FIX.
Do not run START_HERE.bat from the older v15_19 folder.

The Windows .bat launch, backup, diagnostics, and dependency-install scripts were rewritten using ASCII-only commands to avoid command prompt encoding issues. The archive application source is retained from v15.22, including the batch-import checkbox UI and basket thumbnail updates.

Start:
1. Stop any running instance.
2. Back up the existing database and document folder before replacing anything.
3. Extract this ZIP to a new folder.
4. Run START_HERE.bat.
5. If startup fails, run DIAGNOSTICS.bat and share diagnostics_report.txt.

Python syntax checks passed. This package has not been executed on the user's Windows machine. Offline startup still requires Python and all required libraries to be present locally; if they are missing, the launcher will explain this instead of trying to parse garbled commands. This does not include a full offline Python installer or guarantee that all dependency wheels are bundled.
