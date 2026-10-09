@echo off
echo =======================================================
echo Running AI Knowledge Assistant Evaluation Benchmark
echo =======================================================
python manage.py eval
echo Evaluation complete! Visual chart saved in eval\reports\eval_metrics_chart.png
pause
