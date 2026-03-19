#!/usr/bin/env python3
"""
Diagnostic test for _train_predictor_once function.
Validates data loading, class distribution, feature engineering, and model training.
"""
import sys
sys.path.insert(0, '/Users/prakh/OneDrive/Desktop/gc_dev/gcdata')

import pandas as pd
import numpy as np
from backend.routes.funnel import (
    _load_predictor_training_dataframe,
    _train_predictor_once,
    _categorize_publish_time,
    PredictorTrainingError
)

def test_data_loading():
    print("\n" + "="*60)
    print("TEST 1: Data Loading")
    print("="*60)
    try:
        df = _load_predictor_training_dataframe()
        print(f"✓ Data loaded successfully")
        print(f"  - Total rows: {len(df)}")
        print(f"  - Columns: {df.columns.tolist()}")
        print(f"  - Shape: {df.shape}")
        
        # Check for required columns
        required_cols = ["Published_URL", "Publish_Date", "Create_Date", "Uploaded_Duration", "Created_Duration"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            print(f"✗ Missing columns: {missing}")
            return False
        print(f"✓ All required columns present")
        return True
    except Exception as e:
        print(f"✗ Error loading data: {e}")
        return False

def test_class_distribution():
    print("\n" + "="*60)
    print("TEST 2: Class Distribution After Categorization")
    print("="*60)
    try:
        df = _load_predictor_training_dataframe()
        
        df["Is_Published"] = df["Published_URL"].notna()
        df["Days_to_Publish"] = (df["Publish_Date"] - df["Create_Date"]).dt.total_seconds() / (24 * 3600)
        df["Publish_Timeframe"] = df.apply(
            lambda row: _categorize_publish_time(bool(row["Is_Published"]), row.get("Days_to_Publish")),
            axis=1,
        )
        
        class_dist = df["Publish_Timeframe"].value_counts().sort_index()
        print("✓ Class distribution:")
        for cls, count in class_dist.items():
            pct = (count / len(df)) * 100
            print(f"  - {cls}: {count} rows ({pct:.2f}%)")
        
        expected_classes = {"0_Never", "1_Within_1_Day", "2_Within_2_Days", "3_Within_3_Days", "4_More_than_3_Days"}
        actual_classes = set(class_dist.index)
        missing = expected_classes - actual_classes
        if missing:
            print(f"✗ Missing classes: {missing}")
            return False
        print(f"✓ All 5 classes present in full dataset")
        return True
    except Exception as e:
        print(f"✗ Error in class distribution: {e}")
        return False

def test_feature_engineering():
    print("\n" + "="*60)
    print("TEST 3: Feature Engineering")
    print("="*60)
    try:
        df = _load_predictor_training_dataframe()
        
        df["Is_Published"] = df["Published_URL"].notna()
        df["Days_to_Publish"] = (df["Publish_Date"] - df["Create_Date"]).dt.total_seconds() / (24 * 3600)
        df["Publish_Timeframe"] = df.apply(
            lambda row: _categorize_publish_time(bool(row["Is_Published"]), row.get("Days_to_Publish")),
            axis=1,
        )
        
        max_up_dur = float(df["Uploaded_Duration"].max())
        max_cr_dur = float(df["Created_Duration"].max())
        print(f"✓ Max Uploaded Duration: {max_up_dur:.2f}")
        print(f"✓ Max Created Duration: {max_cr_dur:.2f}")
        
        df["up_dur_norm"] = df["Uploaded_Duration"] / max_up_dur
        df["cr_dur_norm"] = df["Created_Duration"] / max_cr_dur
        
        for power in [2, 3, 7, 9, 11]:
            df[f"Up_Duration_P{power}"] = df["up_dur_norm"] ** power
            df[f"Cr_Duration_P{power}"] = df["cr_dur_norm"] ** power
        
        print(f"✓ Created power features for powers: [2, 3, 7, 9, 11]")
        
        drop_cols = [
            "Publish_Timeframe", "Is_Published", "Publish_Date",
            "Days_to_Publish", "Create_Date", "Upload_Date",
            "Published_Platform", "up_dur_norm", "cr_dur_norm", "Post_ID",
            "Upload_to_Create_Days",
        ]
        feature_df = df.drop(columns=[column for column in drop_cols if column in df.columns])
        X = pd.get_dummies(feature_df, drop_first=True)
        y = df["Publish_Timeframe"]
        
        print(f"✓ Feature matrix shape: {X.shape}")
        print(f"✓ Features (first 10): {X.columns[:10].tolist()}")
        print(f"✓ Target shape: {y.shape}")
        print(f"✓ Target unique values: {y.nunique()}")
        
        return True
    except Exception as e:
        print(f"✗ Error in feature engineering: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_train_test_split():
    print("\n" + "="*60)
    print("TEST 4: Train-Test Split with Stratification")
    print("="*60)
    try:
        from sklearn.model_selection import train_test_split
        
        df = _load_predictor_training_dataframe()
        
        df["Is_Published"] = df["Published_URL"].notna()
        df["Days_to_Publish"] = (df["Publish_Date"] - df["Create_Date"]).dt.total_seconds() / (24 * 3600)
        df["Publish_Timeframe"] = df.apply(
            lambda row: _categorize_publish_time(bool(row["Is_Published"]), row.get("Days_to_Publish")),
            axis=1,
        )
        
        max_up_dur = float(df["Uploaded_Duration"].max())
        max_cr_dur = float(df["Created_Duration"].max())
        
        df["up_dur_norm"] = df["Uploaded_Duration"] / max_up_dur
        df["cr_dur_norm"] = df["Created_Duration"] / max_cr_dur
        
        for power in [2, 3, 7, 9, 11]:
            df[f"Up_Duration_P{power}"] = df["up_dur_norm"] ** power
            df[f"Cr_Duration_P{power}"] = df["cr_dur_norm"] ** power
        
        drop_cols = [
            "Publish_Timeframe", "Is_Published", "Publish_Date",
            "Days_to_Publish", "Create_Date", "Upload_Date",
            "Published_Platform", "up_dur_norm", "cr_dur_norm", "Post_ID",
            "Upload_to_Create_Days",
        ]
        feature_df = df.drop(columns=[column for column in drop_cols if column in df.columns])
        X = pd.get_dummies(feature_df, drop_first=True)
        y = df["Publish_Timeframe"]
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"✓ Train set size: {len(X_train)} rows")
        print(f"✓ Test set size: {len(X_test)} rows")
        
        # Check class distribution in training set
        train_class_dist = y_train.value_counts().sort_index()
        print(f"\n✓ Class distribution in training set:")
        for cls, count in train_class_dist.items():
            pct = (count / len(y_train)) * 100
            print(f"  - {cls}: {count} rows ({pct:.2f}%)")
        
        expected_classes = {"0_Never", "1_Within_1_Day", "2_Within_2_Days", "3_Within_3_Days", "4_More_than_3_Days"}
        train_classes = set(train_class_dist.index)
        missing = expected_classes - train_classes
        if missing:
            print(f"✗ Missing classes in training set: {missing}")
            return False
        print(f"\n✓ All 5 classes present in training set")
        return True
    except Exception as e:
        print(f"✗ Error in train-test split: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model_training():
    print("\n" + "="*60)
    print("TEST 5: Model Training")
    print("="*60)
    try:
        artifacts = _train_predictor_once()
        
        print(f"✓ Model trained and cached")
        print(f"  - Model type: {type(artifacts.rf_model).__name__}")
        print(f"  - Feature columns: {len(artifacts.feature_columns)}")
        print(f"  - Max upload duration: {artifacts.max_up_dur:.2f}")
        print(f"  - Max created duration: {artifacts.max_cr_dur:.2f}")
        print(f"  - Training rows: {artifacts.training_rows}")
        print(f"  - Train rows (80%): {artifacts.train_rows}")
        
        # Check model classes
        print(f"\n✓ Model classes: {list(artifacts.rf_model.classes_)}")
        
        expected_classes = {"0_Never", "1_Within_1_Day", "2_Within_2_Days", "3_Within_3_Days", "4_More_than_3_Days"}
        model_classes = set(artifacts.rf_model.classes_)
        missing = expected_classes - model_classes
        if missing:
            print(f"✗ Missing classes in model: {missing}")
            return False
        print(f"✓ Model has all 5 classes")
        
        # Test prediction on a sample
        import pandas as pd
        sample_df = pd.DataFrame({
            "Client_Name": ["TestClient"],
            "Assigned_Channel": ["TestChannel"],
            "Input_Type": ["video"],
            "Language": ["en"],
            "Uploaded_Duration": [5000.0],
            "Output_Type": ["TestOutput"],
            "Created_Duration": [2500.0],
        })
        
        sample_df["up_dur_norm"] = sample_df["Uploaded_Duration"] / artifacts.max_up_dur
        sample_df["cr_dur_norm"] = sample_df["Created_Duration"] / artifacts.max_cr_dur
        for power in [2, 3, 7, 9, 11]:
            sample_df[f"Up_Duration_P{power}"] = sample_df["up_dur_norm"] ** power
            sample_df[f"Cr_Duration_P{power}"] = sample_df["cr_dur_norm"] ** power
        sample_df = sample_df.drop(columns=["up_dur_norm", "cr_dur_norm"])
        
        sample_X = pd.get_dummies(sample_df).reindex(columns=artifacts.feature_columns, fill_value=0)
        
        pred = artifacts.rf_model.predict(sample_X)[0]
        probs = artifacts.rf_model.predict_proba(sample_X)[0]
        
        print(f"\n✓ Test prediction on sample:")
        print(f"  - Predicted class: {pred}")
        print(f"  - Prediction probabilities:")
        for cls, prob in zip(artifacts.rf_model.classes_, probs):
            print(f"    - {cls}: {prob*100:.2f}%")
        
        return True
    except Exception as e:
        print(f"✗ Error in model training: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*60)
    print("PREDICTOR DIAGNOSTIC TEST SUITE")
    print("="*60)
    
    tests = [
        ("Data Loading", test_data_loading),
        ("Class Distribution", test_class_distribution),
        ("Feature Engineering", test_feature_engineering),
        ("Train-Test Split", test_train_test_split),
        ("Model Training", test_model_training),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ UNEXPECTED ERROR in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL TESTS PASSED - Predictor is working correctly!")
    else:
        print("✗ SOME TESTS FAILED - Check errors above")
    print("="*60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
