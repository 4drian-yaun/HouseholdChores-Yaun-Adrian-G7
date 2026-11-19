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
    donor = max(grouped, key=lambda key: len(grouped[key]))
    if len(grouped[donor]) < 2:
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


def week_overview(household, membership, week=None):
    week = week or current_week_start()
    assignments = list(
        Assignment.objects.filter(chore__household=household, week_start_date=week)
        .select_related("chore", "member")
        .order_by("chore__name")
    )
    for assignment in assignments:
        assignment.can_complete = completion_block_reason(membership, assignment) is None
    total = len(assignments)
    done = sum(1 for a in assignments if a.status == Assignment.Status.COMPLETED)
    return {
        "assignments": assignments,
        "total": total,
        "done": done,
        "pending": sum(1 for a in assignments if a.status == Assignment.Status.PENDING),
        "percent": round(done * 100 / total) if total else 0,
        "week_start": week,
        "week_end": week + timedelta(days=6),
    }


def past_weeks(household):
    return list(
        Assignment.objects.filter(
            chore__household=household, week_start_date__lt=current_week_start()
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

    chores = list(
        closed.values("chore_id", "chore__name", "chore__is_active")
        .annotate(missed=Count("id", filter=missed_filter), total=Count("id"))
        .filter(missed__gt=0)
        .order_by("-missed", "chore__name")[:5]
    )
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

    return {
        "has_data": total > 0,
        "done": done,
        "missed": missed,
        "total": total,
        "done_pct": percent(done, total),
        "missed_pct": 100 - percent(done, total) if total else 0,
        "members": members,
        "chores": chores,
        "weeks": weeks,
    }
