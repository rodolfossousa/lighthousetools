import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

from data_processor import (
    normalize_attribute_key,
    clean_and_standardize_data,
    validate_data,
    get_template_enrollment_data,
    get_item_enrollment_data,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _v1_df(rows):
    """Minimal V1-format DataFrame (Portuguese headers, pipe notation)."""
    base = {'Template': None, 'Equipamento': None, 'attribute_name': None,
            'Value': None, 'Categories': None}
    return pd.DataFrame([{**base, **r} for r in rows])


def _v2_df(rows):
    """Minimal V2-format DataFrame (English headers, separate subattribute column)."""
    base = {'template': None, 'asset_name': None, 'attribute_name': None,
            'subattribute_name': None, 'type': None, 'reference': None,
            'value': None, 'unit_of_measurement': None, 'decimal_places': None,
            'categories': None}
    return pd.DataFrame([{**base, **r} for r in rows])


def _pipeline_df(rows):
    """DataFrame in the shape returned by ingest_pipeline (post-ETL schema)."""
    base = {
        'template_name': None, 'asset_name': None, 'parent_asset_name': None,
        'attribute_name': None, 'subattribute_name': '', 'attribute_level': 'attribute',
        'reference': None, 'value': None, 'unit_of_measurement': '',
        'decimal_places': 2, 'categories': None, 'data_type': 'Time Series Float',
    }
    return pd.DataFrame([{**base, **r} for r in rows])


# ---------------------------------------------------------------------------
# normalize_attribute_key
# ---------------------------------------------------------------------------

class TestNormalizeAttributeKey:
    def test_lowercase(self):
        assert normalize_attribute_key("Temperature") == "temperature"

    def test_extra_spaces_collapsed(self):
        assert normalize_attribute_key("  Speed  RPM  ") == "speed rpm"

    def test_pipe_no_spaces(self):
        assert normalize_attribute_key("Parent|Child") == "parent | child"

    def test_pipe_with_spaces(self):
        assert normalize_attribute_key("  Parent  |  Child  ") == "parent | child"

    def test_non_string_passthrough(self):
        assert normalize_attribute_key(None) is None
        assert normalize_attribute_key(42) == 42


# ---------------------------------------------------------------------------
# clean_and_standardize_data — V1
# ---------------------------------------------------------------------------

class TestCleanAndStandardizeV1:
    def test_detects_v1_by_absence_of_v2_columns(self):
        df = _v1_df([{'Template': 'T1', 'attribute_name': 'Attr1'}])
        result = clean_and_standardize_data(df)
        assert 'template_name' in result.columns
        assert 'asset_name' in result.columns

    def test_pipe_notation_split_into_separate_columns(self):
        df = _v1_df([{'Template': 'T1', 'Equipamento': 'E1',
                       'attribute_name': 'Vibration|RMS'}])
        result = clean_and_standardize_data(df)
        assert result.iloc[0]['attribute_name'] == 'Vibration'
        assert result.iloc[0]['subattribute_name'] == 'RMS'
        assert result.iloc[0]['attribute_level'] == 'subattribute'

    def test_no_pipe_is_attribute_level(self):
        df = _v1_df([{'Template': 'T1', 'Equipamento': 'E1',
                       'attribute_name': 'Temperature'}])
        result = clean_and_standardize_data(df)
        assert result.iloc[0]['attribute_name'] == 'Temperature'
        assert result.iloc[0]['subattribute_name'] == ''
        assert result.iloc[0]['attribute_level'] == 'attribute'

    def test_pipe_with_extra_spaces(self):
        df = _v1_df([{'Template': 'T1', 'attribute_name': '  Parent  |  Child  '}])
        result = clean_and_standardize_data(df)
        assert result.iloc[0]['attribute_name'] == 'Parent'
        assert result.iloc[0]['subattribute_name'] == 'Child'


# ---------------------------------------------------------------------------
# clean_and_standardize_data — V2
# ---------------------------------------------------------------------------

class TestCleanAndStandardizeV2:
    def test_detects_v2_by_asset_name_and_template_columns(self):
        df = _v2_df([{'template': 'T1', 'asset_name': 'E1', 'attribute_name': 'Attr1'}])
        result = clean_and_standardize_data(df)
        assert 'template_name' in result.columns
        assert 'data_type' in result.columns

    def test_subattribute_name_filled_sets_subattribute_level(self):
        df = _v2_df([{'template': 'T1', 'asset_name': 'E1',
                       'attribute_name': 'Vibration', 'subattribute_name': 'RMS'}])
        result = clean_and_standardize_data(df)
        assert result.iloc[0]['attribute_level'] == 'subattribute'

    def test_empty_subattribute_name_sets_attribute_level(self):
        df = _v2_df([{'template': 'T1', 'asset_name': 'E1',
                       'attribute_name': 'Temperature', 'subattribute_name': None}])
        result = clean_and_standardize_data(df)
        assert result.iloc[0]['attribute_level'] == 'attribute'


# ---------------------------------------------------------------------------
# validate_data
# ---------------------------------------------------------------------------

class TestValidateData:
    def test_rows_without_template_name_removed(self):
        df = pd.DataFrame([
            {'template_name': 'T1', 'asset_name': 'E1'},
            {'template_name': None, 'asset_name': 'E2'},
        ])
        result = validate_data(df)
        assert len(result) == 1
        assert result.iloc[0]['template_name'] == 'T1'


# ---------------------------------------------------------------------------
# get_template_enrollment_data — deduplication
# Regression tests for the subattribute deduplication bug:
#   clean_and_standardize_data splits "Parent|Child" so attribute_name becomes
#   only the parent name. Without subattribute_name in the dedup key, all
#   subattributes of the same parent collapse into one row.
# ---------------------------------------------------------------------------

class TestDedupPreservesSubattributes:
    @patch('data_processor.ingest_pipeline')
    def test_multiple_subattributes_of_same_parent_all_preserved(self, mock_pipeline):
        mock_pipeline.return_value = _pipeline_df([
            {'template_name': 'T1', 'attribute_name': 'Vibration', 'subattribute_name': 'RMS',   'attribute_level': 'subattribute'},
            {'template_name': 'T1', 'attribute_name': 'Vibration', 'subattribute_name': 'Peak',  'attribute_level': 'subattribute'},
            {'template_name': 'T1', 'attribute_name': 'Vibration', 'subattribute_name': 'Hi',    'attribute_level': 'subattribute'},
            {'template_name': 'T1', 'attribute_name': 'Vibration', 'subattribute_name': 'Hi Hi', 'attribute_level': 'subattribute'},
            {'template_name': 'T1', 'attribute_name': 'Temperature', 'subattribute_name': '',    'attribute_level': 'attribute'},
        ])
        result = get_template_enrollment_data()
        assert len(result) == 5, (
            f"Expected 5 rows but got {len(result)}. "
            "Subattributes of the same parent are being incorrectly dropped."
        )

    @patch('data_processor.ingest_pipeline')
    def test_true_duplicates_are_removed(self, mock_pipeline):
        mock_pipeline.return_value = _pipeline_df([
            {'template_name': 'T1', 'attribute_name': 'Vibration', 'subattribute_name': 'RMS', 'attribute_level': 'subattribute'},
            {'template_name': 'T1', 'attribute_name': 'Vibration', 'subattribute_name': 'RMS', 'attribute_level': 'subattribute'},  # true duplicate
            {'template_name': 'T1', 'attribute_name': 'Temperature', 'subattribute_name': '', 'attribute_level': 'attribute'},
            {'template_name': 'T1', 'attribute_name': 'Temperature', 'subattribute_name': '', 'attribute_level': 'attribute'},  # true duplicate
        ])
        result = get_template_enrollment_data()
        assert len(result) == 2

    @patch('data_processor.ingest_pipeline')
    def test_same_subattribute_name_under_different_parents_both_kept(self, mock_pipeline):
        mock_pipeline.return_value = _pipeline_df([
            {'template_name': 'T1', 'attribute_name': 'Vibration',   'subattribute_name': 'Hi', 'attribute_level': 'subattribute'},
            {'template_name': 'T1', 'attribute_name': 'Temperature', 'subattribute_name': 'Hi', 'attribute_level': 'subattribute'},
        ])
        result = get_template_enrollment_data()
        assert len(result) == 2

    @patch('data_processor.ingest_pipeline')
    def test_same_attribute_across_different_templates_both_kept(self, mock_pipeline):
        mock_pipeline.return_value = _pipeline_df([
            {'template_name': 'T1', 'attribute_name': 'Temperature', 'subattribute_name': '', 'attribute_level': 'attribute'},
            {'template_name': 'T2', 'attribute_name': 'Temperature', 'subattribute_name': '', 'attribute_level': 'attribute'},
        ])
        result = get_template_enrollment_data()
        assert len(result) == 2

    @patch('data_processor.ingest_pipeline')
    def test_case_insensitive_dedup_removes_case_variants(self, mock_pipeline):
        mock_pipeline.return_value = _pipeline_df([
            {'template_name': 'T1', 'attribute_name': 'Temperature', 'subattribute_name': '', 'attribute_level': 'attribute'},
            {'template_name': 'T1', 'attribute_name': 'TEMPERATURE', 'subattribute_name': '', 'attribute_level': 'attribute'},
        ])
        result = get_template_enrollment_data()
        assert len(result) == 1


# ---------------------------------------------------------------------------
# get_item_enrollment_data
# ---------------------------------------------------------------------------

class TestGetItemEnrollmentData:
    @patch('data_processor.ingest_pipeline')
    def test_rows_without_asset_name_excluded(self, mock_pipeline):
        mock_pipeline.return_value = _pipeline_df([
            {'template_name': 'T1', 'asset_name': 'E1', 'attribute_name': 'Temp',
             'subattribute_name': '', 'attribute_level': 'attribute'},
            {'template_name': 'T1', 'asset_name': None, 'attribute_name': 'Temp',
             'subattribute_name': '', 'attribute_level': 'attribute'},
        ])
        df, attrs, subattrs = get_item_enrollment_data()
        assert len(df) == 1

    @patch('data_processor.ingest_pipeline')
    def test_attributes_and_subattributes_split_correctly(self, mock_pipeline):
        mock_pipeline.return_value = _pipeline_df([
            {'template_name': 'T1', 'asset_name': 'E1', 'attribute_name': 'Temp',
             'subattribute_name': '', 'attribute_level': 'attribute'},
            {'template_name': 'T1', 'asset_name': 'E1', 'attribute_name': 'Vibration',
             'subattribute_name': 'RMS', 'attribute_level': 'subattribute', 'value': '1.5'},
        ])
        df, attrs, subattrs = get_item_enrollment_data()
        assert len(attrs) == 1
        assert len(subattrs) == 1

    @patch('data_processor.ingest_pipeline')
    def test_subattribute_value_converted_to_numeric(self, mock_pipeline):
        mock_pipeline.return_value = _pipeline_df([
            {'template_name': 'T1', 'asset_name': 'E1', 'attribute_name': 'Vibration',
             'subattribute_name': 'Hi', 'attribute_level': 'subattribute', 'value': '2.5'},
        ])
        _, _, subattrs = get_item_enrollment_data()
        assert subattrs.iloc[0]['value'] == 2.5

    @patch('data_processor.ingest_pipeline')
    def test_reference_with_comma_takes_first_value(self, mock_pipeline):
        mock_pipeline.return_value = _pipeline_df([
            {'template_name': 'T1', 'asset_name': 'E1', 'attribute_name': 'Temp',
             'subattribute_name': '', 'attribute_level': 'attribute',
             'reference': 'TAG001, TAG002'},
        ])
        df, attrs, _ = get_item_enrollment_data()
        assert attrs.iloc[0]['reference'] == 'TAG001'
