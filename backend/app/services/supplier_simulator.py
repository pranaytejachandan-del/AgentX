import logging
from decimal import Decimal
from typing import Tuple

logger = logging.getLogger("agentx.supplier_simulator")


class SupplierSimulator:
    """
    Synthetic Supplier Simulator with deterministic economic boundaries.
    Enforces supplier_min_allowable_price floor and gradual price reductions per turn.
    """

    @staticmethod
    def evaluate_buyer_offer(
        base_price: Decimal,
        min_allowable_price: Decimal,
        current_supplier_offer: Decimal,
        buyer_offer: Decimal,
        turn_number: int,
        max_turns: int = 4
    ) -> Tuple[str, Decimal, str]:
        """
        Evaluate buyer's offer and return (action, new_supplier_offer, message).
        Actions: 'ACCEPT' or 'COUNTER_OFFER'.
        """
        # Sanity check floor
        if min_allowable_price > base_price:
            logger.warning(f"Invalid supplier min ({min_allowable_price}) > base ({base_price}). Clamping min to base.")
            min_allowable_price = base_price

        # Rule 1: If buyer offer meets or exceeds current supplier price, accept immediately
        if buyer_offer >= current_supplier_offer and buyer_offer >= min_allowable_price:
            msg = f"We accept your offer of ₹{buyer_offer:,.2f} per unit."
            return "ACCEPT", buyer_offer, msg

        # Calculate gradual price reduction step
        price_spread = base_price - min_allowable_price
        step = price_spread / Decimal(str(max_turns))
        
        # Calculate new counter offer for this turn
        new_supplier_offer = current_supplier_offer - step
        if new_supplier_offer < min_allowable_price:
            new_supplier_offer = min_allowable_price

        new_supplier_offer = Decimal(str(round(new_supplier_offer, 2)))

        # Rule 2: If buyer offer is >= new supplier counter offer AND >= min_allowable_price, accept buyer offer
        if buyer_offer >= new_supplier_offer and buyer_offer >= min_allowable_price:
            msg = f"We accept your counter-offer of ₹{buyer_offer:,.2f} per unit."
            return "ACCEPT", buyer_offer, msg

        # Rule 3: Otherwise, counter-offer with new_supplier_offer
        msg = f"For this volume, we can reduce our price to ₹{new_supplier_offer:,.2f} per unit."
        return "COUNTER_OFFER", new_supplier_offer, msg
