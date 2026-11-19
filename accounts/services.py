from django.db import transaction

from chores.models import Assignment
from chores.services import reassign_pending
from households.models import Household, HouseholdMember
from households.services import compact_orders
from households.utils import get_membership


@transaction.atomic
def delete_user_account(user):
    # 1. Unlink any previously deactivated member profiles for this user
    HouseholdMember.objects.filter(user=user, is_active=False).update(user=None)

    # 2. Check active membership in a household
    membership = get_membership(user)
    if membership is not None:
        household = membership.household
        other_members = household.members.filter(is_active=True).exclude(pk=membership.pk)

        # Check if any other active member has a linked user account
        other_user_member = other_members.filter(user__isnull=False).first()

        if not other_members.exists() or not other_user_member:
            # Cannot keep household without an account holder:
            # Delete assignments first to satisfy on_delete=PROTECT on Assignment.member
            Assignment.objects.filter(chore__household=household).delete()
            household.delete()
        else:
            # Another member with an account exists! Transfer created_by if this user was creator
            if household.created_by_id == user.pk:
                household.created_by = other_user_member.user
                household.save(update_fields=["created_by"])

            # If this user was the only active admin, promote another member with an account
            if membership.role == HouseholdMember.Role.ADMIN:
                admins = other_members.filter(role=HouseholdMember.Role.ADMIN)
                if not admins.exists():
                    other_user_member.role = HouseholdMember.Role.ADMIN
                    other_user_member.save(update_fields=["role"])

            # Reassign pending chores to remaining active members
            reassign_pending(membership)

            # Deactivate this membership and detach user
            membership.is_active = False
            membership.rotation_order = None
            membership.user = None
            membership.save(update_fields=["is_active", "rotation_order", "user"])
            compact_orders(household)

    # 3. Check if user is created_by for any remaining household
    other_households = Household.objects.filter(created_by=user)
    for h in other_households:
        h_member = h.members.filter(is_active=True, user__isnull=False).exclude(user=user).first()
        if h_member:
            h.created_by = h_member.user
            h.save(update_fields=["created_by"])
        else:
            Assignment.objects.filter(chore__household=h).delete()
            h.delete()

    # 4. Permanently delete the user account
    user.delete()
