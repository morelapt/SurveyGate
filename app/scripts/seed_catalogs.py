import asyncio

from sqlalchemy import select

from app.db.session import SessionFactory
from app.models import Device, Service

DEVICES = [
    ("mobile", "Mobile"),
    ("tv", "TV"),
    ("desktop", "Desktop"),
]

SERVICES = [
    ("netflix", "Netflix"),
    ("kinopoisk", "KinoPoisk"),
    ("youtube", "YouTube"),
]


async def main():
    async with SessionFactory() as session:
        # devices
        existing = set((await session.scalars(select(Device.code))).all())
        for code, title in DEVICES:
            if code not in existing:
                session.add(Device(code=code, title=title))

        # services
        existing = set((await session.scalars(select(Service.code))).all())
        for code, title in SERVICES:
            if code not in existing:
                session.add(Service(code=code, title=title))

        await session.commit()
        print("Seed done")


if __name__ == "__main__":
    asyncio.run(main())
