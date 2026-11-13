from .metrics import evaluate_model


def analyze_false_alarms(y_true, scores, threshold):
    result = evaluate_model(y_true, scores, threshold)

    matrix = result["confusion_matrix"]

    return {
        "false_positives": matrix["fp"],
        "true_negatives": matrix["tn"],
        "false_alarm_rate": result["false_alarm_rate"],
        "specificity": result["specificity"],
        "precision": result["precision"],
        "recall": result["recall"]
    }