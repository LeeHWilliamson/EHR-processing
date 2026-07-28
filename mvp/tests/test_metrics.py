'''
Unit tests for performance and workflow evals
Precision, Recall, F1, and workflow adherence
'''
from mvp.evaluation.performance.calc_output_metrics import calc_metrics

def test_medication_task_metrics():
    assert calc_metrics(8, 2) == 0.8