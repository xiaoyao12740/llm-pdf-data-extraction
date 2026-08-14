from src.normalization.normalizer import fields_to_record, normalize_value


def test_rate_and_region_normalization():
    assert normalize_value("positive_rate", "6.92%") == 0.0692
    assert normalize_value("region", " north region ") == "North"


def test_fields_to_record_preserves_missing():
    assert fields_to_record([{"field_name": "sample_count", "raw_value": "1,200"}]) == {"sample_count": 1200}
