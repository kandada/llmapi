from typing import Optional, List
from sqlalchemy.orm import Session
import json

from models.package import Package, PackageStatus
from utils.time import get_timestamp


class PackageService:
    def __init__(self, db: Session):
        self.db = db

    def get_package_by_id(self, package_id: int) -> Optional[Package]:
        return self.db.query(Package).filter(Package.id == package_id).first()

    def get_all_packages(self, status: int = PackageStatus.ENABLED) -> List[Package]:
        query = self.db.query(Package)
        if status is not None:
            query = query.filter(Package.status == status)
        return query.order_by(Package.sort_order.asc()).all()

    def get_enabled_packages(self) -> List[Package]:
        return self.get_all_packages(status=PackageStatus.ENABLED)

    def create_package(self, package_data: dict) -> Package:
        now = get_timestamp()
        prices = package_data.get("prices", "{}")
        if isinstance(prices, dict):
            prices = json.dumps(prices)

        package = Package(
            name=package_data.get("name", ""),
            description=package_data.get("description", ""),
            quota=package_data.get("quota", 0),
            prices=prices,
            status=package_data.get("status", PackageStatus.ENABLED),
            payment_providers=package_data.get("payment_providers", "stripe"),
            sort_order=package_data.get("sort_order", 0),
            created_time=now,
            updated_time=now,
        )
        self.db.add(package)
        self.db.commit()
        self.db.refresh(package)
        return package

    def update_package(self, package_id: int, update_data: dict) -> Optional[Package]:
        package = self.get_package_by_id(package_id)
        if not package:
            return None

        if "prices" in update_data:
            if isinstance(update_data["prices"], dict):
                update_data["prices"] = json.dumps(update_data["prices"])

        update_data["updated_time"] = get_timestamp()

        for key, value in update_data.items():
            if value is not None and hasattr(package, key):
                setattr(package, key, value)

        self.db.commit()
        self.db.refresh(package)
        return package

    def delete_package(self, package_id: int) -> bool:
        package = self.get_package_by_id(package_id)
        if not package:
            return False

        self.db.delete(package)
        self.db.commit()
        return True

    def get_price(self, package: Package, currency: str = "USD") -> float:
        try:
            prices = json.loads(package.prices)
            if currency not in prices:
                raise ValueError(f"Currency '{currency}' not found in package prices")
            return float(prices.get(currency, 0))
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid package price data: {e}")