"""临床标准知识库

包含WHO BMI标准、BestHealth体脂率标准、血氧标准、内脏脂肪等级标准等
"""

from typing import Dict, Optional


class ClinicalStandards:
    """
    临床标准知识库

    提供BMI、体脂率、血氧、内脏脂肪等级等指标的分类功能
    """

    BMI_STANDARDS = {
        "underweight": {"max": 18.5},
        "normal": {"min": 18.5, "max": 25.0},
        "overweight": {"min": 25.0, "max": 30.0},
        "obese": {"min": 30.0}
    }

    BODY_FAT_STANDARDS = {
        "male": {
            (6, 13): {"under": 7.0, "normal": (7.0, 15.9), "warning": (16.0, 24.9), "over": (25.0, 29.9), "obese": 30.0},
            (14, 14): {"under": 7.0, "normal": (7.0, 14.9), "warning": (15.0, 24.9), "over": (25.0, 28.9), "obese": 29.0},
            (15, 15): {"under": 8.0, "normal": (8.0, 14.9), "warning": (15.0, 23.9), "over": (24.0, 28.9), "obese": 29.0},
            (16, 16): {"under": 8.0, "normal": (8.0, 15.9), "warning": (16.0, 23.9), "over": (24.0, 27.9), "obese": 28.0},
            (17, 17): {"under": 9.0, "normal": (9.0, 15.9), "warning": (16.0, 22.9), "over": (23.0, 27.9), "obese": 28.0},
            (18, 39): {"under": 11.0, "normal": (11.0, 16.9), "warning": (17.0, 21.9), "over": (22.0, 26.9), "obese": 27.0},
            (40, 59): {"under": 12.0, "normal": (12.0, 17.9), "warning": (18.0, 22.9), "over": (23.0, 27.9), "obese": 28.0},
            (60, 99): {"under": 14.0, "normal": (14.0, 19.9), "warning": (20.0, 24.9), "over": (25.0, 29.9), "obese": 30.0}
        },
        "female": {
            (18, 39): {"under": 21.0, "normal": (21.0, 27.9), "warning": (28.0, 34.9), "over": (35.0, 39.9), "obese": 40.0},
            (40, 59): {"under": 22.0, "normal": (22.0, 28.9), "warning": (29.0, 35.9), "over": (36.0, 40.9), "obese": 41.0},
            (60, 99): {"under": 23.0, "normal": (23.0, 29.9), "warning": (30.0, 36.9), "over": (37.0, 41.9), "obese": 42.0}
        }
    }

    SPO2_STANDARDS = {
        "normal": {"min": 95, "max": 100},
        "mild_hypoxemia": {"min": 91, "max": 94},
        "moderate": {"min": 86, "max": 90},
        "severe": {"max": 85}
    }

    VISCERAL_FAT_STANDARDS = {
        "normal": {"max": 9},
        "warning": {"min": 10, "max": 14},
        "danger": {"min": 15}
    }

    def classify_bmi(self, bmi: float) -> str:
        """
        根据BMI值分类

        Args:
            bmi: BMI值

        Returns:
            分类结果: underweight/normal/overweight/obese
        """
        if bmi < self.BMI_STANDARDS["underweight"]["max"]:
            return "underweight"
        elif bmi < self.BMI_STANDARDS["overweight"]["min"]:
            return "normal"
        elif bmi < self.BMI_STANDARDS["obese"]["min"]:
            return "overweight"
        else:
            return "obese"

    def _find_age_group(self, age: int, sex: str) -> Optional[tuple]:
        """找到年龄对应的分组"""
        sex_key = sex.lower()
        if sex_key == 'm':
            sex_key = 'male'
        elif sex_key == 'f':
            sex_key = 'female'
        
        age_groups = self.BODY_FAT_STANDARDS.get(sex_key)
        if not age_groups:
            return None

        for (min_age, max_age) in age_groups:
            if min_age <= age <= max_age:
                return (min_age, max_age)

        return None

    def classify_body_fat(self, body_fat_rate: float, sex: str, age: int) -> str:
        """
        根据体脂率分类

        Args:
            body_fat_rate: 体脂率(%)
            sex: 性别(M/F)
            age: 年龄

        Returns:
            分类结果: underweight/normal/warning/overweight/obese
        """
        age_group = self._find_age_group(age, sex)
        if not age_group:
            return "normal"

        sex_key = sex.lower()
        if sex_key == 'm':
            sex_key = 'male'
        elif sex_key == 'f':
            sex_key = 'female'

        standards = self.BODY_FAT_STANDARDS[sex_key][age_group]

        if body_fat_rate < standards["under"]:
            return "underweight"
        elif body_fat_rate <= standards["normal"][1]:
            return "normal"
        elif body_fat_rate <= standards["warning"][1]:
            return "warning"
        elif body_fat_rate <= standards["over"][1]:
            return "overweight"
        else:
            return "obese"

    def classify_spo2(self, spo2: int) -> str:
        """
        根据血氧值分类

        Args:
            spo2: 血氧值(%)

        Returns:
            分类结果: normal/mild_hypoxemia/moderate/severe
        """
        if spo2 >= self.SPO2_STANDARDS["normal"]["min"]:
            return "normal"
        elif spo2 >= self.SPO2_STANDARDS["mild_hypoxemia"]["min"]:
            return "mild_hypoxemia"
        elif spo2 >= self.SPO2_STANDARDS["moderate"]["min"]:
            return "moderate"
        else:
            return "severe"

    def classify_visceral_fat(self, level: int) -> str:
        """
        根据内脏脂肪等级分类

        Args:
            level: 内脏脂肪等级(1~50)

        Returns:
            分类结果: normal/warning/danger
        """
        if level <= self.VISCERAL_FAT_STANDARDS["normal"]["max"]:
            return "normal"
        elif level <= self.VISCERAL_FAT_STANDARDS["warning"]["max"]:
            return "warning"
        else:
            return "danger"