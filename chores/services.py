from collections import Counter
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from households.models import Household, HouseholdMember

from .models import Assignment, Chore


class CompletionError(Exception):
    pass


def week_start_of(day):
    return day - timedelta(days=day.weekday())


def current_week_start():
    return week_start_of(timezone.localdate())


def active_members(household):
    return list(household.members.filter(is_active=True).order_by("rotation_order"))


def week_load(household, week):
    rows = Assignment.objects.filter(
        chore__household=household, week_start_date=week
    ).values_list("member_id", flat=True)
    return Counter(rows)


def least_loaded(members, load):
    return min(members, key=lambda m: (load.get(m.id, 0), m.rotation_order or 0))


def next_in_rotation(previous, members, chore):
    ids = [m.id for m in members]
    if previous.id in ids:
        return members[(ids.index(previous.id) + 1) % len(members)]
    history = Counter(chore.assignments.values_list("member_id", flat=True))
    return least_loaded(members, history)


@transaction.atomic
def sync_household(household):
    Household.objects.select_for_update().get(pk=household.pk)
    this_week = current_week_start()
    Assignment.objects.filter(
        chore__household=household,
        status=Assignment.Status.PENDING,
        week_start_date__lt=this_week,
    ).update(status=Assignment.Status.MISSED)
    members = active_members(household)
    if not members:
        return
    load = week_load(household, this_week)
    for chore in household.chores.filter(is_active=True):
        last = chore.assignments.select_related("member").order_by("-week_start_date").first()
        if last is None:
            member = least_loaded(members, load)
            Assignment.objects.get_or_create(
                chore=chore, week_start_date=this_week, defaults={"member": member}
            )
            load[member.id] += 1
            continue
        week = last.week_start_date + timedelta(days=7)
        previous = last.member
        while week <= this_week:
            member = next_in_rotation(previous, members, chore)
            is_current = week == this_week
            Assignment.objects.get_or_create(
                chore=chore,
                week_start_date=week,
                defaults={
                    "member": member,
                    "status": Assignment.Status.PENDING if is_current else Assignment.Status.MISSED,
                },
            )
            if is_current:
                load[member.id] += 1
            previous = member
            week += timedelta(days=7)


@transaction.atomic
def create_chore(household, name, description):
    chore = Chore.objects.create(household=household, name=name, description=description)
    this_week = current_week_start()
    member = least_loaded(active_members(household), week_load(household, this_week))
    Assignment.objects.create(chore=chore, member=member, week_start_date=this_week)
    return chore


@transaction.atomic
def retire_chore(chore):
    chore.is_active = False
    chore.save(update_fields=["is_active"])
    Assignment.objects.filter(
        chore=chore,
        week_start_date=current_week_start(),
        status=Assignment.Status.PENDING,
    ).delete()


@transaction.atomic
def on_member_joined(member):
    this_week = current_week_start()
    if Assignment.objects.filter(member=member, week_start_date=this_week).exists():
        return None
    load = week_load(member.household, this_week)
    pending = (
        Assignment.objects.filter(
            chore__household=member.household,
            chore__is_active=True,
            week_start_date=this_week,
            status=Assignment.Status.PENDING,
        )
        .select_related("chore")
        .order_by("chore__name")
    )
    grouped = {}
    for assignment in pending:
        grouped.setdefault(assignment.member_id, []).append(assignment)
    if not grouped:
        return None
    donor = max(grouped, key=lambda key: (load.get(key, 0), len(grouped[key])))
    if load.get(donor, 0) < 2:
        return None
    moved = grouped[donor][-1]
    moved.member = member
    moved.save(update_fields=["member"])
    return moved


@transaction.atomic
def reassign_pending(member):
    this_week = current_week_start()
    others = [m for m in active_members(member.household) if m.id != member.id]
    if not others:
        return 0
    load = week_load(member.household, this_week)
    pending = list(
        Assignment.objects.filter(
            member=member, week_start_date=this_week, status=Assignment.Status.PENDING
        )
    )
    for assignment in pending:
        target = least_loaded(others, load)
        assignment.member = target
        assignment.save(update_fields=["member"])
        load[target.id] += 1
    return len(pending)


def completion_block_reason(membership, assignment):
    if assignment.chore.household_id != membership.household_id:
        return "That chore does not belong to your household."
    if assignment.status == Assignment.Status.COMPLETED:
        return "That chore is already completed."
    if (
        assignment.status == Assignment.Status.MISSED
        or assignment.week_start_date != current_week_start()
    ):
        return "That chore belongs to a past week and can no longer be changed."
    if assignment.member_id == membership.id:
        return None
    if membership.role == HouseholdMember.Role.ADMIN and assignment.member.user_id is None:
        return None
    return "You can only complete chores assigned to you."


@transaction.atomic
def complete_assignment(membership, assignment):
    assignment = (
        Assignment.objects.select_for_update(of=("self",))
        .select_related("chore", "member")
        .get(pk=assignment.pk)
    )
    reason = completion_block_reason(membership, assignment)
    if reason:
        raise CompletionError(reason)
    assignment.status = Assignment.Status.COMPLETED
    assignment.completed_at = timezone.now()
    assignment.save(update_fields=["status", "completed_at"])
    return assignment


def week_overview(household, membership, week=None, member_id=None):
    week = week or current_week_start()
    qs = (
        Assignment.objects.filter(
            chore__household=household,
            week_start_date=week,
            member__is_active=True,
        )
        .select_related("chore", "member")
        .order_by("chore__name")
    )
    if member_id:
        qs = qs.filter(member_id=member_id)
    assignments = list(qs)
    for assignment in assignments:
        assignment.can_complete = completion_block_reason(membership, assignment) is None
        assignment.is_mine = assignment.member_id == membership.id
    total = len(assignments)
    done = sum(1 for a in assignments if a.status == Assignment.Status.COMPLETED)
    missed = sum(1 for a in assignments if a.status == Assignment.Status.MISSED)
    pending = sum(1 for a in assignments if a.status == Assignment.Status.PENDING)
    today = timezone.localdate()
    week_end = week + timedelta(days=6)
    days_left = max((week_end - today).days, 0)
    return {
        "assignments": assignments,
        "total": total,
        "done": done,
        "missed": missed,
        "pending": pending,
        "percent": round(done * 100 / total) if total else 0,
        "week_start": week,
        "week_end": week_end,
        "days_left": days_left,
    }


def past_weeks(household):
    return list(
        Assignment.objects.filter(
            chore__household=household,
            week_start_date__lt=current_week_start(),
            member__is_active=True,
        )
        .values_list("week_start_date", flat=True)
        .distinct()
        .order_by("-week_start_date")
    )


def percent(part, whole):
    return round(part * 100 / whole) if whole else 0


def analytics(household):
    closed = Assignment.objects.filter(
        chore__household=household,
        member__is_active=True,
        status__in=[Assignment.Status.COMPLETED, Assignment.Status.MISSED],
    )
    done_filter = Q(status=Assignment.Status.COMPLETED)
    missed_filter = Q(status=Assignment.Status.MISSED)
    totals = closed.aggregate(
        done=Count("id", filter=done_filter), missed=Count("id", filter=missed_filter)
    )
    done, missed = totals["done"], totals["missed"]
    total = done + missed

    members = list(
        closed.values("member_id", "member__display_name", "member__is_active")
        .annotate(done=Count("id", filter=done_filter), missed=Count("id", filter=missed_filter))
        .order_by("-done", "member__display_name")
    )
    top_done = max([m["done"] for m in members], default=0)
    for row in members:
        row["total"] = row["done"] + row["missed"]
        row["rate"] = percent(row["done"], row["total"])
        row["width"] = percent(row["done"], top_done)
        row["share"] = percent(row["done"], done) if done else 0
        row["missed_rate"] = 100 - row["rate"] if row["total"] else 0

    all_chores = list(
        closed.values("chore_id", "chore__name", "chore__is_active")
        .annotate(
            done=Count("id", filter=done_filter),
            missed=Count("id", filter=missed_filter),
            total=Count("id"),
        )
        .order_by("-missed", "chore__name")
    )
    for row in all_chores:
        row["done_rate"] = percent(row["done"], row["total"])
        row["missed_rate"] = percent(row["missed"], row["total"])

    chores = [dict(c) for c in all_chores if c["missed"] > 0][:5]
    top_missed = max([c["missed"] for c in chores], default=0)
    for row in chores:
        row["rate"] = percent(row["missed"], row["total"])
        row["width"] = percent(row["missed"], top_missed)

    weeks = list(
        closed.values("week_start_date")
        .annotate(done=Count("id", filter=done_filter), missed=Count("id", filter=missed_filter))
        .order_by("-week_start_date")[:8]
    )[::-1]
    for row in weeks:
        row["total"] = row["done"] + row["missed"]
        row["rate"] = percent(row["done"], row["total"])

    # Compute SVG smooth Bezier area & line chart coordinates (viewBox 520 x 170)
    pad_l, pad_r, pad_t, pad_b = 34.0, 20.0, 18.0, 26.0
    chart_w = 520.0 - pad_l - pad_r
    chart_h = 170.0 - pad_t - pad_b
    n_weeks = len(weeks)
    pts = []
    for idx, row in enumerate(weeks):
        if n_weeks == 1:
            x = pad_l + chart_w / 2
        else:
            x = pad_l + (chart_w * idx / (n_weeks - 1))
        y = pad_t + chart_h * (1 - row["rate"] / 100.0)
        row["svg_x"] = round(x, 1)
        row["svg_y"] = round(y, 1)
        pts.append((row["svg_x"], row["svg_y"]))

    baseline_y = round(pad_t + chart_h, 1)
    trend_line_path = ""
    trend_area_path = ""
    if len(pts) == 1:
        px, py = pts[0]
        trend_line_path = f"M {pad_l} {py} L {520.0 - pad_r} {py}"
        trend_area_path = f"M {pad_l} {baseline_y} L {pad_l} {py} L {520.0 - pad_r} {py} L {520.0 - pad_r} {baseline_y} Z"
    elif len(pts) >= 2:
        segs = [f"M {pts[0][0]} {pts[0][1]}"]
        for i in range(1, len(pts)):
            x0, y0 = pts[i - 1]
            x1, y1 = pts[i]
            cx = round((x0 + x1) / 2, 1)
            segs.append(f"C {cx} {y0}, {cx} {y1}, {x1} {y1}")
        trend_line_path = " ".join(segs)
        trend_area_path = (
            f"{trend_line_path} L {pts[-1][0]} {baseline_y} L {pts[0][0]} {baseline_y} Z"
        )

    trend_delta = None
    if len(weeks) >= 2:
        trend_delta = weeks[-1]["rate"] - weeks[-2]["rate"]

    perfect_weeks = sum(1 for w in weeks if w["total"] > 0 and w["missed"] == 0)

    # Day-of-week completion rhythm from actual completed_at timestamps
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_full = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_counts = [0] * 7
    completed_timestamps = closed.filter(
        status=Assignment.Status.COMPLETED, completed_at__isnull=False
    ).values_list("completed_at", flat=True)
    for ts in completed_timestamps:
        day_counts[timezone.localtime(ts).weekday()] += 1
    max_day = max(day_counts, default=0)
    weekdays = [
        {
            "short": day_names[i],
            "full": day_full[i],
            "count": day_counts[i],
            "height": percent(day_counts[i], max_day) if max_day else 0,
            "is_peak": max_day > 0 and day_counts[i] == max_day,
        }
        for i in range(7)
    ]
    peak_day = next((d["full"] for d in weekdays if d["is_peak"]), None)

    done_pct = percent(done, total)
    missed_pct = 100 - done_pct if total else 0
    week_count = closed.values("week_start_date").distinct().count()
    avg_per_week = round(total / week_count, 1) if week_count else 0
    top_members = [m["member__display_name"] for m in members if top_done > 0 and m["done"] == top_done]
    if done_pct >= 85:
        health_label, health_tone = "Excellent", "ok"
    elif done_pct >= 60:
        health_label, health_tone = "On track", "sun"
    else:
        health_label, health_tone = "Needs focus", "warn"

    donut_circ = 414.69
    donut_done_offset = round(donut_circ * (1 - done_pct / 100), 2)

    return {
        "has_data": total > 0,
        "done": done,
        "missed": missed,
        "total": total,
        "done_pct": done_pct,
        "missed_pct": missed_pct,
        "week_count": week_count,
        "avg_per_week": avg_per_week,
        "perfect_weeks": perfect_weeks,
        "trend_delta": trend_delta,
        "trend_line_path": trend_line_path,
        "trend_area_path": trend_area_path,
        "weekdays": weekdays,
        "peak_day": peak_day,
        "has_timestamps": max_day > 0,
        "top_members": top_members,
        "health_label": health_label,
        "health_tone": health_tone,
        "donut_circ": donut_circ,
        "donut_done_offset": donut_done_offset,
        "members": members,
        "chores": chores,
        "all_chores": all_chores,
        "weeks": weeks,
    }
