@ECHO OFF
TITLE "QCoDeS Monitor"
CALL activate qcodes
CAll python -m qcodes.monitor.monitor
pause