@echo off
echo =======================================================
echo Re-indexing AI Knowledge Assistant Documentation
echo =======================================================
python manage.py synth
python manage.py ingest
python manage.py index
echo Done!
pause
