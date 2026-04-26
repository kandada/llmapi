from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from models import option as option_model
from models.option import Option
import json


class OptionService:
    def __init__(self, db: Session):
        self.db = db
        self._cache: Dict[str, Any] = {}

    def get_all_options(self) -> Dict[str, Any]:
        options = self.db.query(Option).all()
        result = {}
        for opt in options:
            result[opt.key] = opt.value
            self._cache[opt.key] = opt.value
        return result

    def get_option(self, key: str) -> Optional[str]:
        if key in self._cache:
            return self._cache[key]

        opt = self.db.query(Option).filter(Option.key == key).first()
        if opt:
            self._cache[key] = opt.value
            return opt.value
        return None

    def set_option(self, key: str, value: str) -> bool:
        opt = self.db.query(Option).filter(Option.key == key).first()
        if opt:
            opt.value = value
        else:
            opt = Option(key=key, value=value)
            self.db.add(opt)
        self.db.commit()
        self._cache[key] = value
        return True

    def delete_option(self, key: str) -> bool:
        opt = self.db.query(Option).filter(Option.key == key).first()
        if opt:
            self.db.delete(opt)
            self.db.commit()
            self._cache.pop(key, None)
            return True
        return False

    def get_model_ratio(self) -> Dict[str, float]:
        ratio_str = self.get_option("ModelRatio")
        if ratio_str:
            try:
                return json.loads(ratio_str)
            except:
                pass
        return {}

    def get_group_ratio(self) -> Dict[str, float]:
        ratio_str = self.get_option("GroupRatio")
        if ratio_str:
            try:
                return json.loads(ratio_str)
            except:
                pass
        return {"default": 1.0}

    def get_completion_ratio(self) -> Dict[str, float]:
        ratio_str = self.get_option("CompletionRatio")
        if ratio_str:
            try:
                return json.loads(ratio_str)
            except:
                pass
        return {}

    def set_model_ratio(self, ratio: Dict[str, float]):
        self.set_option("ModelRatio", json.dumps(ratio))

    def set_group_ratio(self, ratio: Dict[str, float]):
        self.set_option("GroupRatio", json.dumps(ratio))

    def set_completion_ratio(self, ratio: Dict[str, float]):
        self.set_option("CompletionRatio", json.dumps(ratio))
