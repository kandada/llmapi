from sqlalchemy.orm import Session
from typing import List

from database import get_session
from services.package_service import PackageService
from middleware.auth import AuthContext, require_admin


class PackageController:
    def __init__(self, db: Session):
        self.db = db
        self.package_service = PackageService(db)

    def get_public_packages(self) -> dict:
        packages = self.package_service.get_enabled_packages()
        return {
            "packages": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "package_type": p.package_type,
                    "quota": p.quota,
                    "prices": p.prices,
                    "duration_days": p.duration_days,
                    "payment_providers": p.payment_providers,
                }
                for p in packages
            ]
        }

    def get_package_detail(self, package_id: int) -> dict:
        package = self.package_service.get_package_by_id(package_id)
        if not package:
            return None
        return {
            "id": package.id,
            "name": package.name,
            "description": package.description,
            "package_type": package.package_type,
            "quota": package.quota,
            "prices": package.prices,
            "duration_days": package.duration_days,
            "max_tokens": package.max_tokens,
            "allowed_models": package.allowed_models,
            "payment_providers": package.payment_providers,
            "status": package.status,
        }

    def get_all_packages_admin(self) -> List[dict]:
        packages = self.package_service.get_all_packages(status=None)
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "package_type": p.package_type,
                "quota": p.quota,
                "prices": p.prices,
                "duration_days": p.duration_days,
                "status": p.status,
                "payment_providers": p.payment_providers,
                "sort_order": p.sort_order,
                "created_time": p.created_time,
            }
            for p in packages
        ]

    def create_package(self, package_data: dict) -> dict:
        package = self.package_service.create_package(package_data)
        return {"id": package.id}

    def update_package(self, package_id: int, update_data: dict) -> bool:
        result = self.package_service.update_package(package_id, update_data)
        return result is not None

    def delete_package(self, package_id: int) -> bool:
        return self.package_service.delete_package(package_id)