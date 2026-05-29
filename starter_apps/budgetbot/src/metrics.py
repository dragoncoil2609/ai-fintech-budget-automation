"""Custom CloudWatch metrics for BudgetBot W7."""

import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError

NAMESPACE = "BudgetBot/W7"

_cloudwatch = boto3.client(
    "cloudwatch",
    region_name=(
        os.getenv("AWS_REGION_NAME")
        or os.getenv("AWS_DEFAULT_REGION")
        or "us-west-2"
    ),
)


def _dimensions(route: str | None = None, user_id: str | None = None) -> list[dict]:
    dims = [
        {"Name": "Service", "Value": "BudgetBot"},
        {"Name": "Env", "Value": os.getenv("APP_ENV", "dev")},
    ]

    if route:
        dims.append({"Name": "Route", "Value": route})

    if user_id:
        dims.append({"Name": "UserId", "Value": user_id})

    return dims


def put_metric(
    name: str,
    value: float = 1,
    unit: str = "Count",
    route: str | None = None,
    user_id: str | None = None,
) -> None:
    try:
        metric_data = [
            {
                "MetricName": name,
                "Value": value,
                "Unit": unit,
                "Dimensions": _dimensions(route=route, user_id=user_id),
            }
        ]

        # Emit thêm một metric tổng hợp không có UserId để dashboard/alarm không bị phụ thuộc từng user/job.
        if user_id:
            metric_data.append(
                {
                    "MetricName": name,
                    "Value": value,
                    "Unit": unit,
                    "Dimensions": _dimensions(route=route, user_id=None),
                }
            )

        _cloudwatch.put_metric_data(
            Namespace=NAMESPACE,
            MetricData=metric_data,
        )

    except (BotoCoreError, ClientError, Exception) as exc:
        print(
            f"[CloudWatchMetricError] "
            f"metric={name} value={value} unit={unit} "
            f"route={route} user_id={user_id} "
            f"error={type(exc).__name__}: {exc}"
        )