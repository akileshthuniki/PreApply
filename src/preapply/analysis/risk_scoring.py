"""Production-grade multi-dimensional risk scoring (deterministic)."""

import math
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional
from ..ingest.models import NormalizedResource, ResourceAction
from ..graph.dependency_graph import DependencyGraph
from .shared_resources import detect_shared_resources
from .blast_radius import calculate_blast_radius
from .risk_reasons import generate_risk_reason, generate_critical_risk_reason
from ..contracts.risk_attributes import (
    RiskAttributes,
    BlastRadiusMetrics,
    SharedDependency,
    CriticalInfrastructure,
    SensitiveDeletion,
    SecurityExposure,
    CostAlert,
    RiskBreakdown,
)
from ..utils.logging import get_logger

logger = get_logger("analysis.risk_scoring")

DEFAULT_SENSITIVE_PORTS = [22, 3389, 1433, 3306, 5432, 5439, 27017]
DEFAULT_CRITICAL_TYPES = [
    "aws_lb", "aws_alb", "aws_nlb", "aws_vpc", "aws_subnet",
    "aws_eks_cluster", "aws_ecs_cluster", "aws_rds_cluster",
    "aws_elasticache_replication_group",
]
DEFAULT_SENSITIVE_DELETE_TYPES = [
    "aws_db_instance", "aws_rds_cluster", "aws_s3_bucket", "aws_dynamodb_table",
]


@dataclass
class RiskConfig:
    """All tunables for production scorer (from config or defaults)."""
    data_loss_base: float = 50.0
    data_loss_decay: float = 0.85
    state_destructive_multiplier: float = 0.6
    security_exposure_base: float = 40.0
    security_exposure_decay: float = 0.90
    security_sensitive_port_penalty: float = 20.0
    infrastructure_shared_base: float = 30.0
    infrastructure_critical_mult: float = 1.3
    cost_creation_weight: float = 15.0
    cost_scaling_weight: float = 10.0
    cost_decay: float = 0.90
    delete_multiplier: float = 2.0
    update_multiplier: float = 1.5
    create_multiplier: float = 1.0
    data_security_threshold: Tuple[float, float] = (40, 40)
    data_security_bonus: float = 0.35
    infra_security_threshold: Tuple[float, float] = (60, 40)
    infra_security_bonus: float = 0.30
    data_infra_threshold: Tuple[float, float] = (40, 60)
    data_infra_bonus: float = 0.25
    cost_infra_threshold: Tuple[float, float] = (30, 60)
    cost_infra_bonus: float = 0.20
    multi_dimension_threshold: float = 35.0
    three_dimension_bonus: float = 0.40
    two_dimension_bonus: float = 0.15
    blast_radius_base_multiplier: float = 10.0
    blast_radius_weight_infrastructure: float = 1.0
    blast_radius_weight_security: float = 0.4
    blast_radius_weight_data: float = 0.2
    blast_radius_weight_cost: float = 0.5
    critical_catastrophic_threshold: float = 200.0
    critical_threshold: float = 150.0
    high_severe_threshold: float = 100.0
    high_threshold: float = 70.0
    medium_threshold: float = 40.0
    sensitive_ports: List[int] = None
    critical_types: List[str] = None
    sensitive_delete_types: List[str] = None

    def __post_init__(self):
        if self.sensitive_ports is None:
            self.sensitive_ports = DEFAULT_SENSITIVE_PORTS
        if self.critical_types is None:
            self.critical_types = DEFAULT_CRITICAL_TYPES
        if self.sensitive_delete_types is None:
            self.sensitive_delete_types = DEFAULT_SENSITIVE_DELETE_TYPES


class ProductionRiskScorer:
    """Production-grade multi-dimensional risk scorer."""

    def __init__(self, config: RiskConfig = None):
        self.config = config or RiskConfig()

    def calculate_data_loss_dimension(
        self,
        deletions: List[Dict],
        state_destructive_updates: List[Dict],
    ) -> float:
        """Data loss risk with stacking decay. action_weight: DELETE=1.0, state-destructive=0.6."""
        score = 0.0
        for i, _ in enumerate(deletions):
            decay = self.config.data_loss_decay ** i
            score += self.config.data_loss_base * decay * 1.0  # action_weight DELETE=1.0
        for i, _ in enumerate(state_destructive_updates, start=len(deletions)):
            decay = self.config.data_loss_decay ** i
            score += self.config.data_loss_base * decay * self.config.state_destructive_multiplier
        return score

    def calculate_security_dimension(self, exposures: List[Dict]) -> float:
        """Security exposure risk with stacking decay."""
        score = 0.0
        for i, exp in enumerate(exposures):
            decay = self.config.security_exposure_decay ** i
            base = self.config.security_exposure_base
            port_penalty = 0
            if exp.get("port") is not None and exp["port"] in self.config.sensitive_ports:
                port_penalty = self.config.security_sensitive_port_penalty
            score += (base + port_penalty) * decay
        return score

    def calculate_infrastructure_dimension(self, shared_resources: List[Dict]) -> float:
        """Infrastructure risk: per-resource action mult (DELETE 2.0, UPDATE 1.5, CREATE 1.0)."""
        score = 0.0
        for r in shared_resources:
            base = self.config.infrastructure_shared_base
            if r.get("is_critical", False):
                base *= self.config.infrastructure_critical_mult
            action = (r.get("action") or "UPDATE").upper()
            if action == "DELETE":
                mult = self.config.delete_multiplier
            elif action == "UPDATE":
                mult = self.config.update_multiplier
            else:
                mult = self.config.create_multiplier
            score += base * mult
        return score

    def calculate_cost_dimension(
        self,
        high_cost_creations: int,
        instance_scalings: int,
    ) -> float:
        """Cost risk with stacking decay."""
        score = 0.0
        for i in range(high_cost_creations):
            decay = self.config.cost_decay ** i
            score += self.config.cost_creation_weight * decay
        for i in range(instance_scalings):
            decay = self.config.cost_decay ** (high_cost_creations + i)
            score += self.config.cost_scaling_weight * decay
        return score

    def calculate_interaction_multiplier(self, dimensions: Dict[str, float]) -> float:
        """Interaction multiplier (1.0 + sum of bonuses)."""
        bonus = 0.0
        if (
            dimensions.get("data", 0) >= self.config.data_security_threshold[0]
            and dimensions.get("security", 0) >= self.config.data_security_threshold[1]
        ):
            bonus += self.config.data_security_bonus
        if (
            dimensions.get("infrastructure", 0) >= self.config.infra_security_threshold[0]
            and dimensions.get("security", 0) >= self.config.infra_security_threshold[1]
        ):
            bonus += self.config.infra_security_bonus
        if (
            dimensions.get("data", 0) >= self.config.data_infra_threshold[0]
            and dimensions.get("infrastructure", 0) >= self.config.data_infra_threshold[1]
        ):
            bonus += self.config.data_infra_bonus
        if (
            dimensions.get("cost", 0) >= self.config.cost_infra_threshold[0]
            and dimensions.get("infrastructure", 0) >= self.config.cost_infra_threshold[1]
        ):
            bonus += self.config.cost_infra_bonus
        elevated_count = sum(
            1 for s in dimensions.values() if s >= self.config.multi_dimension_threshold
        )
        if elevated_count >= 3:
            bonus += self.config.three_dimension_bonus
        elif elevated_count == 2:
            bonus += self.config.two_dimension_bonus
        return 1.0 + bonus

    def calculate_blast_radius(self, affected_count: int, primary_dimension: str) -> float:
        """B × ω_context."""
        if affected_count == 0:
            return 0.0
        b = self.config.blast_radius_base_multiplier * math.log2(affected_count + 1)
        weights = {
            "infrastructure": self.config.blast_radius_weight_infrastructure,
            "security": self.config.blast_radius_weight_security,
            "data": self.config.blast_radius_weight_data,
            "cost": self.config.blast_radius_weight_cost,
        }
        w = weights.get(primary_dimension, 0.5)
        return b * w

    def score(
        self,
        deletions: List[Dict],
        state_destructive_updates: List[Dict],
        exposures: List[Dict],
        shared_resources: List[Dict],
        high_cost_creations: int,
        instance_scalings: int,
        affected_count: int,
    ) -> Dict[str, Any]:
        """Full orchestration: dimensions, interaction, blast, level, action."""
        dimensions = {
            "data": self.calculate_data_loss_dimension(deletions, state_destructive_updates),
            "security": self.calculate_security_dimension(exposures),
            "infrastructure": self.calculate_infrastructure_dimension(shared_resources),
            "cost": self.calculate_cost_dimension(high_cost_creations, instance_scalings),
        }
        primary_dimension = max(dimensions, key=dimensions.get)
        primary_score = dimensions[primary_dimension]
        interaction_mult = self.calculate_interaction_multiplier(dimensions)
        blast_contribution = self.calculate_blast_radius(affected_count, primary_dimension)
        final_score = (primary_score * interaction_mult) + blast_contribution

        if final_score >= self.config.critical_catastrophic_threshold:
            level = "CRITICAL-CATASTROPHIC"
            action = "HARD_BLOCK"
            approval = "VP_ENGINEERING + INCIDENT_REVIEW"
        elif final_score >= self.config.critical_threshold:
            level = "CRITICAL"
            action = "SOFT_BLOCK"
            approval = "VP_ENGINEERING or DIRECTOR"
        elif final_score >= self.config.high_severe_threshold:
            level = "HIGH-SEVERE"
            action = "REQUIRE_APPROVAL"
            approval = "SENIOR_ENGINEER + ARCHITECT"
        elif final_score >= self.config.high_threshold:
            level = "HIGH"
            action = "REQUIRE_APPROVAL"
            approval = "SENIOR_ENGINEER or TECH_LEAD"
        elif final_score >= self.config.medium_threshold:
            level = "MEDIUM"
            action = "REQUIRE_PEER_REVIEW"
            approval = "ANY_ENGINEER"
        else:
            level = "LOW"
            action = "AUTO_APPROVE"
            approval = "NONE"

        return {
            "score": round(final_score, 2),
            "level": level,
            "action": action,
            "approval_required": approval,
            "primary_dimension": primary_dimension,
            "dimensions": {k: round(v, 2) for k, v in dimensions.items()},
            "breakdown": {
                "primary_score": round(primary_score, 2),
                "interaction_multiplier": round(interaction_mult, 3),
                "blast_radius_contribution": round(blast_contribution, 2),
                "affected_resources": affected_count,
            },
        }


def _build_risk_config(config: Dict[str, Any]) -> RiskConfig:
    """Build RiskConfig from config dict (risk_scoring section or legacy)."""
    rs = config.get("risk_scoring", {})
    blast = config.get("blast_radius", {})
    shared = config.get("shared_resources", {})
    cost_cfg = config.get("cost_alerts", {})

    data_loss = rs.get("data_loss", {})
    security = rs.get("security", {})
    infra = rs.get("infrastructure", {})
    cost_sec = rs.get("cost", {})
    interactions = rs.get("interactions", {})
    blast_cfg = rs.get("blast_radius", {})
    thresholds = rs.get("thresholds", {})

    return RiskConfig(
        data_loss_base=float(data_loss.get("base_weight", 50)),
        data_loss_decay=float(data_loss.get("decay_factor", 0.85)),
        state_destructive_multiplier=float(data_loss.get("state_destructive_multiplier", 0.6)),
        security_exposure_base=float(security.get("base_weight", 40)),
        security_exposure_decay=float(security.get("decay_factor", 0.9)),
        security_sensitive_port_penalty=float(security.get("sensitive_port_penalty", 20)),
        sensitive_ports=security.get("sensitive_ports") or DEFAULT_SENSITIVE_PORTS,
        infrastructure_shared_base=float(infra.get("shared_resource_base", blast.get("shared_resource_weight", 30))),
        infrastructure_critical_mult=float(infra.get("critical_multiplier", blast.get("critical_infrastructure_multiplier", 1.3))),
        critical_types=infra.get("critical_types") or shared.get("critical_types") or DEFAULT_CRITICAL_TYPES,
        cost_creation_weight=float(cost_sec.get("creation_weight", 15)),
        cost_scaling_weight=float(cost_sec.get("scaling_weight", 10)),
        cost_decay=float(cost_sec.get("decay_factor", 0.9)),
        delete_multiplier=float(blast.get("delete_action_multiplier", 2.0)),
        update_multiplier=float(blast.get("update_action_multiplier", 1.5)),
        create_multiplier=float(blast.get("create_action_multiplier", 1.0)),
        data_security_threshold=tuple(interactions.get("data_security", {}).get("thresholds", [40, 40])),
        data_security_bonus=float(interactions.get("data_security", {}).get("bonus", 0.35)),
        infra_security_threshold=tuple(interactions.get("infrastructure_security", {}).get("thresholds", [60, 40])),
        infra_security_bonus=float(interactions.get("infrastructure_security", {}).get("bonus", 0.30)),
        data_infra_threshold=tuple(interactions.get("data_infrastructure", {}).get("thresholds", [40, 60])),
        data_infra_bonus=float(interactions.get("data_infrastructure", {}).get("bonus", 0.25)),
        cost_infra_threshold=tuple(interactions.get("cost_infrastructure", {}).get("thresholds", [30, 60])),
        cost_infra_bonus=float(interactions.get("cost_infrastructure", {}).get("bonus", 0.20)),
        multi_dimension_threshold=float(interactions.get("multi_dimension", {}).get("threshold", 35)),
        three_dimension_bonus=float(interactions.get("multi_dimension", {}).get("three_plus_bonus", 0.40)),
        two_dimension_bonus=float(interactions.get("multi_dimension", {}).get("two_bonus", 0.15)),
        blast_radius_base_multiplier=float(blast_cfg.get("base_multiplier", 10)),
        blast_radius_weight_infrastructure=float(blast_cfg.get("weights", {}).get("infrastructure", 1.0)),
        blast_radius_weight_security=float(blast_cfg.get("weights", {}).get("security", 0.4)),
        blast_radius_weight_data=float(blast_cfg.get("weights", {}).get("data", 0.2)),
        blast_radius_weight_cost=float(blast_cfg.get("weights", {}).get("cost", 0.5)),
        critical_catastrophic_threshold=float(thresholds.get("critical_catastrophic", 200)),
        critical_threshold=float(thresholds.get("critical", 150)),
        high_severe_threshold=float(thresholds.get("high_severe", 100)),
        high_threshold=float(thresholds.get("high", 70)),
        medium_threshold=float(thresholds.get("medium", 40)),
        sensitive_delete_types=shared.get("sensitive_delete_types") or DEFAULT_SENSITIVE_DELETE_TYPES,
    )


def calculate_risk_score(
    graph: DependencyGraph,
    config: Dict[str, Any],
    security_exposures: Optional[List] = None,
    cost_alerts: Optional[List] = None,
    state_destructive_updates: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Calculate risk score using production-grade multi-dimensional formula.

    Adapter: builds scorer inputs from graph, exposures, cost_alerts, state_destructive.
    """
    security_exposures = security_exposures or []
    cost_alerts = cost_alerts or []
    state_destructive_updates = state_destructive_updates or []

    changed_resources = graph.get_changed_resources()
    if not changed_resources:
        return {
            "blast_radius_score": 0.0,
            "risk_level": "LOW",
            "risk_level_detailed": "LOW",
            "risk_action": "AUTO_APPROVE",
            "approval_required": "NONE",
            "contributing_factors": [],
            "affected_count": 0,
            "deletion_count": 0,
            "affected_components": [],
            "risk_attributes": RiskAttributes(
                blast_radius=BlastRadiusMetrics(
                    affected_resources=0, affected_components=0, changed_resources=0
                ),
                risk_breakdown=None,
            ),
        }

    blast_radius = calculate_blast_radius(graph, changed_resources)
    shared_list = detect_shared_resources(graph, config)
    changed_shared = [r for r in changed_resources if r in shared_list]
    risk_config = _build_risk_config(config)
    critical_types = risk_config.critical_types
    sensitive_delete_types = risk_config.sensitive_delete_types

    deletions = [
        {"type": r.type, "id": r.id if not r.module else f"{r.module}.{r.id}"}
        for r in changed_resources
        if r.action == ResourceAction.DELETE and r.type in sensitive_delete_types
    ]

    exposures_for_scorer = []
    for exp in security_exposures:
        d = {"port": getattr(exp, "port", None)}
        exposures_for_scorer.append(d)

    shared_resources_for_scorer = []
    for r in changed_shared:
        node_id = graph.get_node_id(r)
        shared_resources_for_scorer.append({
            "type": r.type,
            "action": r.action.value if hasattr(r.action, "value") else str(r.action),
            "is_critical": r.type in critical_types,
            "dependents": len(graph.get_downstream_resources(node_id)),
        })

    def _alert_type(a) -> str:
        at = getattr(a, "alert_type", None)
        if at:
            return at
        return "INSTANCE_SCALING" if "scaling" in getattr(a, "reason", "").lower() else "HIGH_COST_CREATION"

    high_cost_creations = len([a for a in cost_alerts if _alert_type(a) == "HIGH_COST_CREATION"])
    instance_scalings = len([a for a in cost_alerts if _alert_type(a) == "INSTANCE_SCALING"])

    affected_count = blast_radius["affected_count"]

    scorer = ProductionRiskScorer(risk_config)
    result = scorer.score(
        deletions=deletions,
        state_destructive_updates=state_destructive_updates,
        exposures=exposures_for_scorer,
        shared_resources=shared_resources_for_scorer,
        high_cost_creations=high_cost_creations,
        instance_scalings=instance_scalings,
        affected_count=affected_count,
    )

    from ..contracts.core_output import get_legacy_risk_level
    legacy_level = get_legacy_risk_level(result["level"])

    shared_dependencies: List[SharedDependency] = []
    for r in changed_shared:
        node_id = graph.get_node_id(r)
        dep_count = len(graph.get_downstream_resources(node_id))
        resource_id = r.id if not r.module else f"{r.module}.{r.id}"
        risk_reason = generate_risk_reason(
            resource_type=r.type,
            dependents=dep_count,
            is_shared=True,
            is_critical=r.type in critical_types,
        )
        shared_dependencies.append(SharedDependency(
            resource_id=resource_id,
            resource_type=r.type,
            dependents=dep_count,
            is_critical=r.type in critical_types,
            multiplier_applied=risk_config.infrastructure_critical_mult if r.type in critical_types else None,
            risk_reason=risk_reason,
        ))

    critical_infrastructure: List[CriticalInfrastructure] = []
    changed_critical = [
        r for r in changed_resources
        if r.type in critical_types and r not in changed_shared
    ]
    for r in changed_critical:
        resource_id = r.id if not r.module else f"{r.module}.{r.id}"
        critical_infrastructure.append(CriticalInfrastructure(
            resource_id=resource_id,
            resource_type=r.type,
            risk_reason=generate_critical_risk_reason(r.type),
        ))

    sensitive_deletions: List[SensitiveDeletion] = []
    for r in changed_resources:
        if r.action == ResourceAction.DELETE and r.type in sensitive_delete_types:
            resource_id = r.id if not r.module else f"{r.module}.{r.id}"
            sensitive_deletions.append(SensitiveDeletion(resource_id=resource_id, resource_type=r.type))

    action_types = list({r.action.value for r in changed_resources if r.action != ResourceAction.NO_OP})
    if not action_types:
        action_types = ["CREATE"]

    factors = []
    for d in result["dimensions"].values():
        if d > 0:
            factors.append(f"Dimension score: {d}")
    if affected_count > 0:
        factors.append(f"{affected_count} resources affected")
    for sd in sensitive_deletions:
        factors.append(f"Sensitive deletion: {sd.resource_id} ({sd.resource_type})")
    for exp in security_exposures:
        factors.append(f"Security exposure: {exp.details}")
    for ca in cost_alerts:
        factors.append(f"Cost alert: {ca.reason}")

    breakdown = result["breakdown"]
    risk_breakdown = RiskBreakdown(
        primary_dimension=result["primary_dimension"],
        primary_score=breakdown["primary_score"],
        interaction_multiplier=breakdown["interaction_multiplier"],
        blast_radius_contribution=breakdown["blast_radius_contribution"],
        dimensions=result["dimensions"],
    )

    risk_attributes = RiskAttributes(
        blast_radius=BlastRadiusMetrics(
            affected_resources=affected_count,
            affected_components=len(blast_radius["affected_components"]),
            changed_resources=len(changed_resources),
        ),
        shared_dependencies=shared_dependencies,
        critical_infrastructure=critical_infrastructure,
        sensitive_deletions=sensitive_deletions,
        security_exposures=security_exposures,
        cost_alerts=cost_alerts,
        action_types=action_types,
        action_multiplier=None,
        risk_breakdown=risk_breakdown,
    )

    deletion_count = sum(1 for r in changed_resources if r.action == ResourceAction.DELETE)

    logger.info(f"Risk score calculated: {result['score']} ({result['level']})")

    return {
        "blast_radius_score": result["score"],
        "risk_level": legacy_level.value,
        "risk_level_detailed": result["level"],
        "risk_action": result["action"],
        "approval_required": result["approval_required"],
        "contributing_factors": factors,
        "affected_count": affected_count,
        "deletion_count": deletion_count,
        "affected_components": blast_radius["affected_components"],
        "risk_attributes": risk_attributes,
    }
