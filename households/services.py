from django.db import transaction
from django.db.models import Max

from accounts.models import CustomUser
from chores.services import on_member_joined, reassign_pending

from .models import Household, HouseholdMember


class MemberError(Exception):
    pass


def role_for(user):
    if user is not None and user.role == CustomUser.Role.ADMIN:
        return HouseholdMember.Role.ADMIN
    return HouseholdMember.Role.MEMBER


def next_order(household):
    top = household.members.filter(is_active=True).aggregate(top=Max("rotation_order"))["top"]
    return (top or 0) + 1


def compact_orders(household):
    members = household.members.filter(is_active=True).order_by("rotation_order")
    for index, member in enumerate(members, start=1):
        if member.rotation_order != index:
            HouseholdMember.objects.filter(pk=member.pk).update(rotation_order=index)


@transaction.atomic
def create_household(user, name):
    household = Household.objects.create(name=name, created_by=user)
    HouseholdMember.objects.create(
        household=household,
        user=user,
        display_name=user.full_name,
        role=HouseholdMember.Role.ADMIN,
        rotation_order=1,
    )
    return household


@transaction.atomic
def add_member(household, display_name, user):
    Household.objects.select_for_update().get(pk=household.pk)
    member = HouseholdMember.objects.create(
        household=household,
        user=user,
        display_name=display_name,
        role=role_for(user),
        rotation_order=next_order(household),
    )
    moved = on_member_joined(member)
    return member, moved


@transaction.atomic
def update_member(member, display_name, user):
    member.display_name = display_name
    if member.role != HouseholdMember.Role.ADMIN:
        member.user = user
        member.role = role_for(user)
    member.save()
    return member


@transaction.atomic
def move_member(member, direction):
    members = list(member.household.members.filter(is_active=True).order_by("rotation_order"))
    index = [m.id for m in members].index(member.id)
    target = index - 1 if direction == "up" else index + 1
    if target < 0 or target >= len(members):
        return False
    other = members[target]
    first, second = member.rotation_order, other.rotation_order
    HouseholdMember.objects.filter(pk=member.pk).update(rotation_order=None)
    HouseholdMember.objects.filter(pk=other.pk).update(rotation_order=first)
    HouseholdMember.objects.filter(pk=member.pk).update(rotation_order=second)
    return True


@transaction.atomic
def remove_member(member, actor):
    Household.objects.select_for_update().get(pk=member.household_id)
    if member.pk == actor.pk:
        raise MemberError("You cannot remove yourself from the household.")
    if member.role == HouseholdMember.Role.ADMIN:
        admins = member.household.members.filter(
            is_active=True, role=HouseholdMember.Role.ADMIN
        ).count()
        if admins <= 1:
            raise MemberError("A household must keep at least one active Household Admin.")
    reassigned = reassign_pending(member)
    member.is_active = False
    member.rotation_order = None
    member.save(update_fields=["is_active", "rotation_order"])
    compact_orders(member.household)
    return reassigned
