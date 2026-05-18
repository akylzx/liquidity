"""Account endpoints: list accounts, get balances, get account details."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.services.forecast_engine import get_latest_balances

router = APIRouter()


@router.get("")
async def list_accounts(session: AsyncSession = Depends(get_db)):
    """List all accounts with their latest balance and status."""
    result = await session.execute(select(Account).where(Account.is_active == True))
    accounts = result.scalars().all()

    balances = await get_latest_balances(session)

    items = []
    for acct in accounts:
        aid = str(acct.id)
        bal_info = balances.get(aid, {})
        balance = bal_info.get("balance", 0)
        min_bal = float(acct.min_balance)
        max_bal = float(acct.max_balance) if acct.max_balance else None

        # Traffic light status
        if balance < min_bal:
            status = "red"
        elif balance < min_bal * 1.2:
            status = "yellow"
        else:
            status = "green"

        items.append({
            "id": aid,
            "bank_name": acct.bank_name,
            "bank_country": acct.bank_country,
            "currency": acct.currency,
            "account_type": acct.account_type,
            "balance": balance,
            "available": bal_info.get("available", balance),
            "in_flight_in": bal_info.get("in_flight_in", 0),
            "in_flight_out": bal_info.get("in_flight_out", 0),
            "min_balance": min_bal,
            "max_balance": max_bal,
            "status": status,
            "as_of": bal_info.get("as_of"),
        })

    # Summary stats
    total_balance = sum(i["balance"] for i in items)
    total_in_flight = sum(i["in_flight_in"] for i in items)

    return {
        "accounts": items,
        "summary": {
            "total_balance": round(total_balance, 2),
            "total_in_flight_in": round(total_in_flight, 2),
            "account_count": len(items),
            "red_count": sum(1 for i in items if i["status"] == "red"),
            "yellow_count": sum(1 for i in items if i["status"] == "yellow"),
            "green_count": sum(1 for i in items if i["status"] == "green"),
        },
    }


@router.get("/{account_id}")
async def get_account(account_id: UUID, session: AsyncSession = Depends(get_db)):
    """Get detailed account info."""
    result = await session.execute(select(Account).where(Account.id == account_id))
    acct = result.scalar_one_or_none()
    if not acct:
        return {"error": "Account not found"}

    balances = await get_latest_balances(session)
    bal_info = balances.get(str(account_id), {})

    return {
        "id": str(acct.id),
        "bank_name": acct.bank_name,
        "bank_country": acct.bank_country,
        "currency": acct.currency,
        "account_type": acct.account_type,
        "min_balance": float(acct.min_balance),
        "max_balance": float(acct.max_balance) if acct.max_balance else None,
        "overdraft_limit": float(acct.overdraft_limit),
        **bal_info,
    }


@router.get("/{account_id}/history")
async def get_balance_history(
    account_id: UUID,
    days: int = 30,
    session: AsyncSession = Depends(get_db),
):
    """Get daily balance history for an account."""
    query = text("""
        SELECT
            date_trunc('day', time) as day,
            AVG(balance) as avg_balance,
            MIN(balance) as min_balance,
            MAX(balance) as max_balance,
            AVG(in_flight_in) as avg_in_flight_in,
            AVG(in_flight_out) as avg_in_flight_out
        FROM balance_snapshots
        WHERE account_id = CAST(:account_id AS uuid)
          AND time >= NOW() - make_interval(days => :days)
        GROUP BY day
        ORDER BY day
    """)
    result = await session.execute(query, {
        "account_id": str(account_id),
        "days": days,
    })
    rows = result.fetchall()

    return {
        "account_id": str(account_id),
        "history": [
            {
                "date": row.day.isoformat(),
                "balance": round(float(row.avg_balance), 2),
                "min_balance": round(float(row.min_balance), 2),
                "max_balance": round(float(row.max_balance), 2),
                "in_flight_in": round(float(row.avg_in_flight_in), 2),
                "in_flight_out": round(float(row.avg_in_flight_out), 2),
            }
            for row in rows
        ],
    }
