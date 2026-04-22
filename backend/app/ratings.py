from collections import defaultdict
from math import exp

from sqlalchemy.orm import Session

from .models import CategoryWeight, Comparison, GoalkeeperWeight, Player, Skill


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = exp(-value)
        return 1 / (1 + z)
    z = exp(value)
    return z / (1 + z)


def _normalize_skill_scores(raw_scores: dict[int, float]) -> dict[int, float]:
    if not raw_scores:
        return {}

    minimum = min(raw_scores.values())
    maximum = max(raw_scores.values())
    if abs(maximum - minimum) < 1e-9:
        return {player_id: 50.0 for player_id in raw_scores}

    return {
        player_id: 100 * (score - minimum) / (maximum - minimum)
        for player_id, score in raw_scores.items()
    }


def _compute_skill_ratings(
    player_ids: list[int],
    comparisons: list[Comparison],
    regularization: float = 0.015,
    iterations: int = 220,
    learning_rate: float = 0.9,
) -> tuple[dict[int, float], dict[int, int]]:
    if not player_ids:
        return {}, {}

    ratings = {player_id: 0.0 for player_id in player_ids}
    counts = {player_id: 0 for player_id in player_ids}
    if not comparisons:
        return {player_id: 50.0 for player_id in player_ids}, counts

    matches: list[tuple[int, int, float]] = []
    for comparison in comparisons:
        player_a_id = comparison.player_a_id
        player_b_id = comparison.player_b_id
        if player_a_id not in ratings or player_b_id not in ratings:
            continue
        if comparison.comparison_value == 0:
            outcome = 0.5
        elif comparison.winner_player_id == player_a_id:
            outcome = 1.0
        elif comparison.winner_player_id == player_b_id:
            outcome = 0.0
        else:
            outcome = 1.0 if comparison.comparison_value > 0 else 0.0
        matches.append((player_a_id, player_b_id, outcome))
        counts[player_a_id] += 1
        counts[player_b_id] += 1

    if not matches:
        return {player_id: 50.0 for player_id in player_ids}, counts

    player_count = len(player_ids)
    for _ in range(iterations):
        gradients = {player_id: -regularization * ratings[player_id] for player_id in player_ids}
        for player_a_id, player_b_id, outcome in matches:
            probability = _sigmoid(ratings[player_a_id] - ratings[player_b_id])
            delta = outcome - probability
            gradients[player_a_id] += delta
            gradients[player_b_id] -= delta

        step = learning_rate / max(len(matches), player_count)
        for player_id in player_ids:
            ratings[player_id] += step * gradients[player_id]

        mean_rating = sum(ratings.values()) / player_count
        for player_id in player_ids:
            ratings[player_id] -= mean_rating

    return _normalize_skill_scores(ratings), counts


def compute_player_ratings(session: Session, include_inactive: bool = False) -> list[dict[str, object]]:
    player_query = session.query(Player)
    if not include_inactive:
        player_query = player_query.filter_by(is_active=True)
    players = player_query.order_by(Player.id).all()
    player_ids = [player.id for player in players]
    player_map = {player.id: player for player in players}
    if not players:
        return []

    skills = session.query(Skill).filter_by(is_active=True).order_by(Skill.priority.desc(), Skill.id).all()
    category_weights = {
        row.category_key: row.weight
        for row in session.query(CategoryWeight).all()
    }
    goalkeeper_weights = {
        row.skill_key: row.weight
        for row in session.query(GoalkeeperWeight).all()
    }

    all_comparisons = (
        session.query(Comparison)
        .filter(
            Comparison.player_a_id.in_(player_ids),
            Comparison.player_b_id.in_(player_ids),
            Comparison.winner_player_id.in_(player_ids),
        )
        .all()
    )
    comparisons_by_skill: dict[int, list[Comparison]] = defaultdict(list)
    for comparison in all_comparisons:
        comparisons_by_skill[comparison.skill_id].append(comparison)

    skill_results: dict[str, dict[int, float]] = {}
    skill_counts: dict[str, dict[int, int]] = {}

    for skill in skills:
        eligible_player_ids = [
            player.id
            for player in players
            if skill.applies_to_role_group != "goalkeeper_only"
            or player.role_type in {"goalkeeper", "hybrid"}
        ]
        ratings, counts = _compute_skill_ratings(
            eligible_player_ids,
            comparisons_by_skill.get(skill.id, []),
        )
        skill_results[skill.key] = ratings
        skill_counts[skill.key] = counts

    player_payloads: list[dict[str, object]] = []
    for player in players:
        category_bucket: dict[str, list[tuple[float, float]]] = defaultdict(list)
        goalkeeping_bucket: list[tuple[float, float]] = []
        player_skill_payload: dict[str, dict[str, float | int | None]] = {}

        for skill in skills:
            rating = skill_results.get(skill.key, {}).get(player.id)
            comparisons_count = skill_counts.get(skill.key, {}).get(player.id, 0)
            player_skill_payload[skill.key] = {
                "rating": rating,
                "comparisons_count": comparisons_count,
            }
            if rating is None:
                continue
            if skill.category_key == "goalkeeping":
                goalkeeping_bucket.append((rating, goalkeeper_weights.get(skill.key, 0)))
            else:
                category_bucket[skill.category_key].append((rating, 1.0))

        category_ratings: dict[str, float] = {}
        for category_key, entries in category_bucket.items():
            total_weight = sum(weight for _, weight in entries) or 1.0
            category_ratings[category_key] = sum(value * weight for value, weight in entries) / total_weight

        overall_numerator = 0.0
        overall_denominator = 0.0
        for category_key, value in category_ratings.items():
            category_weight = category_weights.get(category_key, 0)
            if category_weight <= 0:
                continue
            overall_numerator += value * category_weight
            overall_denominator += category_weight
        overall_rating = overall_numerator / overall_denominator if overall_denominator else 50.0

        goalkeeper_rating = None
        if goalkeeping_bucket:
            goalkeeper_weight_total = sum(weight for _, weight in goalkeeping_bucket) or 1.0
            goalkeeper_rating = sum(
                value * weight for value, weight in goalkeeping_bucket
            ) / goalkeeper_weight_total

        comparison_total = sum(
            payload["comparisons_count"] or 0
            for payload in player_skill_payload.values()
        )
        maturity = min(100.0, comparison_total * 100 / max(1, len(skills) * 8))

        player_payloads.append(
            {
                "player": {
                    "id": player.id,
                    "display_name": player.display_name,
                    "name_fa": player.name_fa,
                    "name_en": player.name_en,
                    "role_type": player.role_type,
                    "appearance_score": player.appearance_score,
                    "image_url": player.image_url,
                    "is_active": player.is_active,
                    "linked_user_id": player.linked_user_id,
                },
                "overall_rating": round(overall_rating, 1),
                "goalkeeper_rating": round(goalkeeper_rating, 1) if goalkeeper_rating is not None else None,
                "category_ratings": {
                    key: round(value, 1) for key, value in sorted(category_ratings.items())
                },
                "skill_ratings": player_skill_payload,
                "comparison_total": comparison_total,
                "maturity": round(maturity, 1),
            }
        )

    player_payloads.sort(
        key=lambda item: (
            item["overall_rating"],
            item["goalkeeper_rating"] or -1,
            item["player"]["appearance_score"],
        ),
        reverse=True,
    )
    return player_payloads
