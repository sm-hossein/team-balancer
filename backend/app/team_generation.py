from collections import defaultdict
from copy import deepcopy
from itertools import combinations
import random

from sqlalchemy.orm import Session

from .models import CategoryWeight, Player
from .ratings import compute_player_ratings


def _effective_lineups(team: list[dict[str, object]], players_per_team: int) -> list[list[dict[str, object]]]:
    if not team:
        return [[]]

    fixed_goalkeepers = [item for item in team if item.get("is_fixed_goalkeeper")]
    fixed_goalkeeper = fixed_goalkeepers[0] if fixed_goalkeepers else None
    outfield_players = [item for item in team if item is not fixed_goalkeeper]

    if fixed_goalkeeper is not None:
        active_outfield_count = max(players_per_team - 1, 0)
    else:
        active_outfield_count = players_per_team

    if active_outfield_count <= 0:
        return [[fixed_goalkeeper]] if fixed_goalkeeper is not None else [[]]

    if len(outfield_players) <= active_outfield_count:
        lineup = list(outfield_players)
        if fixed_goalkeeper is not None:
            lineup.insert(0, fixed_goalkeeper)
        return [lineup]

    lineups: list[list[dict[str, object]]] = []
    for combo in combinations(outfield_players, active_outfield_count):
        lineup = list(combo)
        if fixed_goalkeeper is not None:
            lineup.insert(0, fixed_goalkeeper)
        lineups.append(lineup)
    return lineups


def _team_metrics(team: list[dict[str, object]], players_per_team: int) -> dict[str, object]:
    if not team:
        return {
            "overall": 0.0,
            "goalkeeper": 0.0,
            "categories": {},
            "player_ids": [],
            "size": 0,
            "on_court_size": 0,
            "bench_count": 0,
        }

    lineups = _effective_lineups(team, players_per_team)
    category_totals: dict[str, float] = defaultdict(float)
    overall_total = 0.0
    goalkeeper_total = 0.0

    for lineup in lineups:
        if not lineup:
            continue
        overall_total += sum(float(item["overall_rating"]) for item in lineup) / len(lineup)
        for item in lineup:
            if item.get("is_fixed_goalkeeper"):
                goalkeeper_total += float(item["goalkeeper_rating"] or 0.0)
            for category_key, value in item["category_ratings"].items():
                if category_key == "goalkeeping":
                    continue
                category_totals[category_key] += float(value)

    lineup_count = max(len(lineups), 1)
    average_lineup_size = round(sum(len(lineup) for lineup in lineups) / lineup_count)
    bench_count = max(len(team) - average_lineup_size, 0)

    category_metrics = {
        key: round((value / lineup_count) / average_lineup_size, 1)
        for key, value in sorted(category_totals.items())
        if average_lineup_size > 0
    }

    fixed_goalkeeper = next((item for item in team if item.get("is_fixed_goalkeeper")), None)
    goalkeeper_metric = round(float(fixed_goalkeeper["goalkeeper_rating"] or 0.0), 1) if fixed_goalkeeper else 0.0

    return {
        "overall": round(overall_total / lineup_count, 1),
        "goalkeeper": goalkeeper_metric,
        "categories": category_metrics,
        "player_ids": [item["player"]["id"] for item in team],
        "size": len(team),
        "on_court_size": average_lineup_size,
        "bench_count": bench_count,
    }


def _balance_score(
    teams: list[list[dict[str, object]]],
    category_weights: dict[str, int],
    players_per_team: int,
) -> float:
    if not teams:
        return 0.0

    metrics = [_team_metrics(team, players_per_team) for team in teams]
    categories = sorted({key for metric in metrics for key in metric["categories"]})
    score = 0.0

    for category_key in categories:
        values = [metric["categories"].get(category_key, 0.0) for metric in metrics]
        mean_value = sum(values) / len(values)
        variance = sum((value - mean_value) ** 2 for value in values) / len(values)
        score += variance * category_weights.get(category_key, 10)

    goalkeeper_values = [metric["goalkeeper"] for metric in metrics]
    goalkeeper_mean = sum(goalkeeper_values) / len(goalkeeper_values)
    goalkeeper_variance = (
        sum((value - goalkeeper_mean) ** 2 for value in goalkeeper_values) / len(goalkeeper_values)
    )
    score += goalkeeper_variance * 60

    overall_values = [metric["overall"] for metric in metrics]
    overall_mean = sum(overall_values) / len(overall_values)
    overall_variance = sum((value - overall_mean) ** 2 for value in overall_values) / len(overall_values)
    score += overall_variance * 18

    size_values = [metric["size"] for metric in metrics]
    size_mean = sum(size_values) / len(size_values)
    size_variance = sum((value - size_mean) ** 2 for value in size_values) / len(size_values)
    score += size_variance * 250
    return score


def _choose_goalkeepers(
    selected_ratings: list[dict[str, object]],
    goalkeeper_ids: list[int],
    team_count: int,
) -> list[dict[str, object]]:
    rating_map = {item["player"]["id"]: item for item in selected_ratings}
    chosen = [rating_map[player_id] for player_id in goalkeeper_ids if player_id in rating_map]
    chosen.sort(
        key=lambda item: (
            item["goalkeeper_rating"] or -1,
            item["overall_rating"],
            item["player"]["appearance_score"],
        ),
        reverse=True,
    )
    return chosen[:team_count]


def _team_signature(teams: list[list[dict[str, object]]]) -> tuple[tuple[int, ...], ...]:
    normalized = [tuple(sorted(int(item["player"]["id"]) for item in team)) for team in teams]
    return tuple(sorted(normalized))


def _generate_candidate_teams(
    selected_ratings: list[dict[str, object]],
    team_count: int,
    goalkeeper_ids: list[int],
    players_per_team: int,
    category_weights: dict[str, int],
    rng: random.Random,
) -> tuple[list[list[dict[str, object]]], float]:
    teams: list[list[dict[str, object]]] = [[] for _ in range(team_count)]
    base_team_size = len(selected_ratings) // team_count
    extra_slots = len(selected_ratings) % team_count
    target_sizes = [base_team_size + (1 if index < extra_slots else 0) for index in range(team_count)]

    chosen_goalkeepers = _choose_goalkeepers(selected_ratings, goalkeeper_ids, team_count)
    assigned_ids = set()

    goalkeeper_order = list(enumerate(chosen_goalkeepers))
    rng.shuffle(goalkeeper_order)
    for index, goalkeeper in goalkeeper_order:
        goalkeeper["is_fixed_goalkeeper"] = True
        teams[index].append(goalkeeper)
        assigned_ids.add(goalkeeper["player"]["id"])

    remaining_players = [item for item in selected_ratings if item["player"]["id"] not in assigned_ids]
    for item in remaining_players:
        item["is_fixed_goalkeeper"] = False

    remaining_players.sort(
        key=lambda item: (
            item["overall_rating"] + rng.uniform(-2.0, 2.0),
            (item["goalkeeper_rating"] or 0.0) + rng.uniform(-1.0, 1.0),
            sum(item["category_ratings"].values()) + rng.uniform(-2.0, 2.0),
            item["player"]["appearance_score"] + rng.uniform(-1.0, 1.0),
        ),
        reverse=True,
    )

    for player_rating in remaining_players:
        candidate_team_scores: list[tuple[float, int]] = []
        for index in range(team_count):
            if len(teams[index]) >= target_sizes[index]:
                continue
            trial_teams = deepcopy(teams)
            trial_teams[index].append(player_rating)
            score = _balance_score(trial_teams, category_weights, players_per_team)
            candidate_team_scores.append((score, index))

        candidate_team_scores.sort(key=lambda item: item[0])
        top_band = candidate_team_scores[: min(2, len(candidate_team_scores))]
        _, chosen_index = rng.choice(top_band)
        teams[chosen_index].append(player_rating)

    improved = True
    while improved:
        improved = False
        current_score = _balance_score(teams, category_weights, players_per_team)
        swap_candidates: list[tuple[float, list[list[dict[str, object]]]]] = []
        for left_index in range(team_count):
            for right_index in range(left_index + 1, team_count):
                for left_player in list(teams[left_index]):
                    if left_player.get("is_fixed_goalkeeper"):
                        continue
                    for right_player in list(teams[right_index]):
                        if right_player.get("is_fixed_goalkeeper"):
                            continue
                        trial_teams = deepcopy(teams)
                        left_trial = trial_teams[left_index]
                        right_trial = trial_teams[right_index]
                        left_pos = next(i for i, item in enumerate(left_trial) if item["player"]["id"] == left_player["player"]["id"])
                        right_pos = next(i for i, item in enumerate(right_trial) if item["player"]["id"] == right_player["player"]["id"])
                        left_trial[left_pos], right_trial[right_pos] = right_trial[right_pos], left_trial[left_pos]
                        trial_score = _balance_score(trial_teams, category_weights, players_per_team)
                        if trial_score + 0.5 < current_score:
                            swap_candidates.append((trial_score, trial_teams))
        if swap_candidates:
            swap_candidates.sort(key=lambda item: item[0])
            best_swaps = swap_candidates[: min(3, len(swap_candidates))]
            _, teams = rng.choice(best_swaps)
            improved = True

    return teams, _balance_score(teams, category_weights, players_per_team)


def generate_balanced_teams(
    session: Session,
    selected_player_ids: list[int],
    team_count: int,
    goalkeeper_ids: list[int],
    players_per_team: int,
    previous_team_player_ids: list[list[int]] | None = None,
) -> dict[str, object]:
    if team_count < 2:
        raise ValueError("At least two teams are required.")
    if players_per_team < 1:
        raise ValueError("Players per team must be at least one.")
    if len(selected_player_ids) < team_count * players_per_team:
        raise ValueError("Not enough players selected for the requested teams and players per team.")

    players = session.query(Player).filter(Player.id.in_(selected_player_ids), Player.is_active == True).all()
    if len(players) != len(set(selected_player_ids)):
        raise ValueError("Some selected players are missing or inactive.")

    ratings = compute_player_ratings(session, include_inactive=False)
    selected_ratings = [deepcopy(item) for item in ratings if item["player"]["id"] in selected_player_ids]
    if len(selected_ratings) != len(selected_player_ids):
        raise ValueError("Some selected players do not have rating data.")

    category_weights = {row.category_key: row.weight for row in session.query(CategoryWeight).all()}
    excluded_signatures = set()
    if previous_team_player_ids:
        excluded_signatures.add(tuple(sorted(tuple(sorted(team)) for team in previous_team_player_ids)))

    best_result: tuple[list[list[dict[str, object]]], float] | None = None
    best_alternative: tuple[list[list[dict[str, object]]], float] | None = None

    for _ in range(28):
        candidate_ratings = deepcopy(selected_ratings)
        rng = random.Random()
        teams, score = _generate_candidate_teams(
            candidate_ratings,
            team_count=team_count,
            goalkeeper_ids=goalkeeper_ids,
            players_per_team=players_per_team,
            category_weights=category_weights,
            rng=rng,
        )
        signature = _team_signature(teams)
        if best_result is None or score < best_result[1]:
            best_result = (teams, score)
        if signature not in excluded_signatures:
            if best_alternative is None or score < best_alternative[1]:
                best_alternative = (teams, score)

    chosen_teams = best_alternative[0] if best_alternative is not None else best_result[0]

    return {
        "teams": [
            {
                "team_index": index + 1,
                "players": team,
                "metrics": _team_metrics(team, players_per_team),
            }
            for index, team in enumerate(chosen_teams)
        ]
    }
