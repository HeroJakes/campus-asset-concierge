from campus_asset_concierge.domain.reservations import requirements_text


STEPS = {
    "waiting_for_loading": ("waiting", "Waiting to be loaded", "Item is queued for loading."),
    "pickup_missed": ("blocked", "Pickup window closed", "This item was not loaded in time."),
    "code_not_open": ("open", "Loaded & locked", "The pickup window has not opened yet."),
    "enter_code": ("open", "Ready for pickup", "Waiting for the borrower to enter their code."),
    "confirm_pickup": ("open", "Open & waiting for pickup", "The borrower must confirm collection."),
    "code_blocked": ("blocked", "Code blocked", "Too many incorrect code attempts. Staff follow-up needed."),
    "code_expired": ("blocked", "Code expired", "The item was not collected in time."),
    "collected": ("collected", "Collected", "The item is still on loan."),
}


def booking_overview(reservations: list[dict], query: str, status: str) -> dict:
    """Keep summary counts and filtered rows based on the same booking states."""
    bookings = []
    for reservation in reservations:
        tone, label, description = STEPS[reservation["step"]]
        group = "active"
        if reservation["step"] == "waiting_for_loading":
            group = "to_load"
        if reservation["loan_status"] == "returned":
            group, tone, label, description = (
                "completed", "completed", "Returned & checked", "The loan is closed."
            )
        elif reservation["loan_status"] == "overdue":
            tone, label, description = "blocked", "Overdue", "The loan needs staff follow-up."
        bookings.append(reservation | {
            "group": group, "tone": tone, "label": label,
            "description": reservation["load_blocker"] or description,
        })
    counts = {"all": len(bookings)} | {
        group: sum(booking["group"] == group for booking in bookings)
        for group in ("to_load", "active", "completed")
    }
    query = query.strip()
    matches = [
        booking for booking in bookings
        if (status == "all" or booking["group"] == status)
        and query.casefold() in " ".join([
            booking["asset_id"], booking["borrower_id"], booking["id"],
            booking["asset_id"].replace("-", " "),
            booking["borrower_id"].replace("-", " "), requirements_text(booking),
        ]).casefold()
    ]
    return {"bookings": matches, "booking_counts": counts, "booking_query": query, "booking_filter": status}
