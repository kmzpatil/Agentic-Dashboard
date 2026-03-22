from __future__ import annotations

from backend.analytics.overview_service import get_overview_snapshot
from backend.analytics.trends_service import get_trends_snapshot
from backend.contracts import InsightAction, InsightCard
from backend.middleware.auth import AuthContext


SEVERITY_SCORE = {"critical": 3, "warning": 2, "info": 1}


def _cta(label: str, target: str, **filter_state) -> InsightAction:
    return InsightAction(
        type="navigate",
        label=label,
        target=target,
        filter_state={"view": target, **filter_state},
    )


def build_insights(auth: AuthContext, surface: str = "mission-control", limit: int = 6) -> list[InsightCard]:
    overview = get_overview_snapshot(auth)
    trend = get_trends_snapshot(auth, metric="publish_conversion_rate", granularity="month")
    kpis = overview.get("kpis", {})
    cards: list[InsightCard] = []

    publish_conversion = float(kpis.get("publish_conversion_rate") or 0)
    creation_rate = float(kpis.get("creation_rate") or 0)
    efficiency = float(kpis.get("processing_efficiency") or 0)

    if publish_conversion < 50:
        cards.append(
            InsightCard(
                id="publish-conversion-gap",
                surface=surface,
                title="Publishing conversion needs attention",
                summary=(
                    f"Only {publish_conversion:.1f}% of created assets are being published. "
                    "Inspect the funnel to see where assets stall before publish."
                ),
                severity="critical",
                confidence=0.96,
                evidence=[
                    f"Publish conversion: {publish_conversion:.1f}%",
                    f"Creation rate: {creation_rate:.1f}%",
                ],
                cta=_cta("Open Funnel", "funnel", breakdown="channel"),
            )
        )

    if creation_rate - publish_conversion > 10:
        cards.append(
            InsightCard(
                id="creation-publish-gap",
                surface=surface,
                title="Created assets are outpacing publication",
                summary=(
                    "Assets are being produced faster than they are published. "
                    "Break down the funnel by output type to see where the drop-off clusters."
                ),
                severity="warning",
                confidence=0.9,
                evidence=[
                    f"Creation rate: {creation_rate:.1f}%",
                    f"Publish conversion: {publish_conversion:.1f}%",
                ],
                cta=_cta("Review Output Funnel", "funnel", breakdown="output_type"),
            )
        )

    top_performer = (overview.get("topPerformers") or [None])[0]
    if top_performer and top_performer.get("label"):
        cards.append(
            InsightCard(
                id="top-performer",
                surface=surface,
                title=f"{top_performer['label']} is the strongest performer",
                summary=(
                    f"{top_performer['dimension']} is leading with "
                    f"{float(top_performer.get('conversion') or 0):.1f}% conversion."
                ),
                severity="info",
                confidence=0.83,
                evidence=[f"Dimension: {top_performer['dimension']}"],
                cta=_cta("Explore Breakdown", "explorer", dim1="channel", dim2="language"),
            )
        )

    for anomaly in trend.get("anomalies", [])[:2]:
        cards.append(
            InsightCard(
                id=f"trend-{anomaly['period']}",
                surface=surface,
                title=f"{anomaly['direction'].title()} detected in conversion trend",
                summary=(
                    f"{trend['metricLabel']} showed a {anomaly['direction']} around {anomaly['period']} "
                    f"with a z-score of {anomaly['zScore']}."
                ),
                severity="warning" if anomaly["severity"] == "high" else "info",
                confidence=0.79,
                evidence=[f"Value: {anomaly['value']}", f"Period: {anomaly['period']}"],
                cta=_cta("Open Trends", "trends", metric="publish_conversion_rate", granularity="month"),
            )
        )

    if efficiency > 100:
        cards.append(
            InsightCard(
                id="efficiency-upside",
                surface=surface,
                title="Processing efficiency is healthy",
                summary=(
                    f"Published duration is running at {efficiency:.1f}% of created duration. "
                    "Use ATLAS to break down which teams or channels are driving that efficiency."
                ),
                severity="info",
                confidence=0.72,
                evidence=[f"Processing efficiency: {efficiency:.1f}%"],
                cta=_cta("Ask ATLAS", "atlas", prompt="Which teams are driving processing efficiency?"),
            )
        )

    ranked = sorted(cards, key=lambda item: (SEVERITY_SCORE.get(item.severity, 0), item.confidence), reverse=True)
    return ranked[:limit]
