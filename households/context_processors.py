from .models import HouseholdMember
from .utils import get_membership


def membership(request):
    if hasattr(request, "user") and request.user.is_authenticated:
        member = get_membership(request.user)
        is_admin = member is not None and member.role == HouseholdMember.Role.ADMIN
        return {
            "membership": member,
            "is_household_admin": is_admin,
        }
    return {
        "membership": None,
        "is_household_admin": False,
    }
