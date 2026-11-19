from .models import HouseholdMember


def get_membership(user):
    if not user.is_authenticated:
        return None
    return (
        HouseholdMember.objects.filter(user=user, is_active=True)
        .select_related("household")
        .first()
    )
