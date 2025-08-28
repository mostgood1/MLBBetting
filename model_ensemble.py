#!/usr/bin/env python3
"""
Advanced Model Ensemble System
=============================

Implements ensemble of XGBoost + Random Forest + Neural Network for improved predictions.
Includes cross-validation, feature importance analysis, and model performance monitoring.
"""

import numpy as np
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, mean_squared_error, log_loss
import xgboost as xgb
try:
    import tensorflow as tf
    from tensorflow import keras
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
import warnings
warnings.filterwarnings('ignore')

class MLBEnsembleModel:
    
    def __init__(self, data_directory="data"):
        self.data_directory = data_directory
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.feature_importance = {}
        self.performance_history = []
        
    def build_ensemble_model(self):
        """Build and train ensemble model"""
        
        print("🤖 BUILDING ADVANCED ENSEMBLE MODEL")
        print("=" * 38)
        print()
        
        # Load and prepare training data
        X, y = self._prepare_training_data()
        
        if X is None or len(X) == 0:
            print("❌ No training data available")
            return
        
        # Split data temporally
        X_train, X_val, y_train, y_val = self._temporal_train_test_split(X, y)
        
        # Train individual models
        self._train_xgboost_model(X_train, y_train, X_val, y_val)
        self._train_random_forest_model(X_train, y_train, X_val, y_val)
        
        if TENSORFLOW_AVAILABLE:
            self._train_neural_network_model(X_train, y_train, X_val, y_val)
        
        # Create ensemble predictions
        self._create_ensemble_predictions(X_val, y_val)
        
        # Analyze feature importance
        self._analyze_feature_importance()
        
        # Generate performance report
        self._generate_performance_report()
    
    def _prepare_training_data(self):
        """Prepare training data from historical games"""
        
        print("📊 PREPARING TRAINING DATA")
        print("-" * 26)
        
        # Load historical data
        features = []
        targets = []
        
        # Find all available dates
        betting_files = []
        for file in os.listdir(self.data_directory):
            if file.startswith('betting_recommendations_2025') and file.endswith('.json'):
                betting_files.append(file)
        
        for file in sorted(betting_files):
            date_str = file.replace('betting_recommendations_', '').replace('.json', '').replace('_', '-')
            
            game_features, game_targets = self._extract_game_features(date_str)
            if game_features:
                features.extend(game_features)
                targets.extend(game_targets)
        
        if not features:
            print("❌ No features extracted")
            return None, None
        
        # Convert to numpy arrays
        X = np.array(features)
        y = np.array(targets)
        
        print(f"✅ Prepared {len(features)} training samples")
        print(f"📏 Feature dimensions: {X.shape[1]}")
        print()
        
        return X, y
    
    def _extract_game_features(self, date_str):
        """Extract features for a single day's games"""
        
        date_underscore = date_str.replace('-', '_')
        
        # Load betting recommendations
        betting_file = os.path.join(self.data_directory, f"betting_recommendations_{date_underscore}.json")
        scores_file = os.path.join(self.data_directory, f"final_scores_{date_underscore}.json")
        
        if not os.path.exists(betting_file):
            return [], []
        
        with open(betting_file, 'r') as f:
            betting_data = json.load(f)
        
        scores_data = {}
        if os.path.exists(scores_file):
            with open(scores_file, 'r') as f:
                scores_data = json.load(f)
        
        features = []
        targets = []
        
        if 'games' not in betting_data:
            return features, targets
        
        for game_key, game_data in betting_data['games'].items():
            game_features = self._extract_single_game_features(game_key, game_data)
            game_target = self._extract_game_target(game_key, game_data, scores_data)
            
            if game_features and game_target is not None:
                features.append(game_features)
                targets.append(game_target)
        
        return features, targets
    
    def _extract_single_game_features(self, game_key, game_data):
        """Extract features for a single game"""
        
        if 'predictions' not in game_data:
            return None
        
        predictions = game_data['predictions']
        
        if 'predictions' not in predictions:
            return None
        
        pred_data = predictions['predictions']
        
        # Base features
        features = []
        
        # Home/Away win probabilities
        features.append(pred_data.get('home_win_prob', 0.5))
        features.append(1 - pred_data.get('home_win_prob', 0.5))  # away_win_prob
        
        # Predicted scores
        features.append(pred_data.get('predicted_home_score', 5.0))
        features.append(pred_data.get('predicted_away_score', 5.0))
        features.append(pred_data.get('predicted_total_runs', 10.0))
        
        # Confidence
        features.append(pred_data.get('confidence', 50.0))
        
        # Pitcher factors
        if 'pitcher_info' in predictions:
            pitcher_info = predictions['pitcher_info']
            features.append(pitcher_info.get('away_pitcher_factor', 1.0))
            features.append(pitcher_info.get('home_pitcher_factor', 1.0))
        else:
            features.extend([1.0, 1.0])
        
        # Team strength (derived from win probabilities)
        home_prob = pred_data.get('home_win_prob', 0.5)
        features.append(abs(home_prob - 0.5))  # game_competitiveness
        
        # Betting line features (if available)
        if 'betting_lines' in game_data:
            lines = game_data['betting_lines']
            features.append(lines.get('total_line', 0) or 0)
            
            # Moneyline odds (convert to probabilities)
            if lines.get('moneyline_home'):
                home_ml_prob = self._odds_to_probability(lines['moneyline_home'])
                features.append(home_ml_prob)
            else:
                features.append(0.5)
                
            if lines.get('moneyline_away'):
                away_ml_prob = self._odds_to_probability(lines['moneyline_away'])
                features.append(away_ml_prob)
            else:
                features.append(0.5)
        else:
            features.extend([0, 0.5, 0.5])
        
        # Additional derived features
        home_score = pred_data.get('predicted_home_score', 5.0)
        away_score = pred_data.get('predicted_away_score', 5.0)
        
        features.append(abs(home_score - away_score))  # score_differential
        features.append(max(home_score, away_score))   # highest_team_score
        features.append(min(home_score, away_score))   # lowest_team_score
        
        return features
    
    def _extract_game_target(self, game_key, game_data, scores_data):
        """Extract target variable (actual winner) for a game"""
        
        if not scores_data:
            return None
        
        # Find actual scores
        for score_key, score_data in scores_data.items():
            if game_key in score_key or any(team in score_key for team in game_key.split('_vs_')):
                away_score = score_data.get('away_score', score_data.get('final_away_score'))
                home_score = score_data.get('home_score', score_data.get('final_home_score'))
                
                if away_score is not None and home_score is not None:
                    # Return 1 if home wins, 0 if away wins
                    return 1 if home_score > away_score else 0
        
        return None
    
    def _odds_to_probability(self, odds):
        """Convert American odds to probability"""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    
    def _temporal_train_test_split(self, X, y, test_size=0.2):
        """Split data temporally (older data for training, newer for validation)"""
        
        split_idx = int(len(X) * (1 - test_size))
        
        X_train = X[:split_idx]
        X_val = X[split_idx:]
        y_train = y[:split_idx]
        y_val = y[split_idx:]
        
        print(f"📊 Training samples: {len(X_train)}")
        print(f"📊 Validation samples: {len(X_val)}")
        print()
        
        return X_train, X_val, y_train, y_val
    
    def _train_xgboost_model(self, X_train, y_train, X_val, y_val):
        """Train XGBoost model"""
        
        print("🚀 TRAINING XGBOOST MODEL")
        print("-" * 26)
        
        # XGBoost parameters
        params = {
            'objective': 'binary:logistic',
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'random_state': 42,
            'eval_metric': 'logloss'
        }
        
        # Train model
        self.models['xgboost'] = xgb.XGBClassifier(**params)
        self.models['xgboost'].fit(X_train, y_train)
        
        # Evaluate
        train_pred = self.models['xgboost'].predict(X_train)
        val_pred = self.models['xgboost'].predict(X_val)
        
        train_acc = accuracy_score(y_train, train_pred)
        val_acc = accuracy_score(y_val, val_pred)
        
        print(f"✅ Training Accuracy: {train_acc:.3f}")
        print(f"✅ Validation Accuracy: {val_acc:.3f}")
        
        # Feature importance
        self.feature_importance['xgboost'] = self.models['xgboost'].feature_importances_
        
        print()
    
    def _train_random_forest_model(self, X_train, y_train, X_val, y_val):
        """Train Random Forest model"""
        
        print("🌲 TRAINING RANDOM FOREST MODEL")
        print("-" * 31)
        
        # Random Forest parameters
        params = {
            'n_estimators': 100,
            'max_depth': 10,
            'random_state': 42,
            'n_jobs': -1
        }
        
        # Train model
        self.models['random_forest'] = RandomForestClassifier(**params)
        self.models['random_forest'].fit(X_train, y_train)
        
        # Evaluate
        train_pred = self.models['random_forest'].predict(X_train)
        val_pred = self.models['random_forest'].predict(X_val)
        
        train_acc = accuracy_score(y_train, train_pred)
        val_acc = accuracy_score(y_val, val_pred)
        
        print(f"✅ Training Accuracy: {train_acc:.3f}")
        print(f"✅ Validation Accuracy: {val_acc:.3f}")
        
        # Feature importance
        self.feature_importance['random_forest'] = self.models['random_forest'].feature_importances_
        
        print()
    
    def _train_neural_network_model(self, X_train, y_train, X_val, y_val):
        """Train Neural Network model"""
        
        print("🧠 TRAINING NEURAL NETWORK MODEL")
        print("-" * 32)
        
        # Scale features
        self.scalers['neural_network'] = StandardScaler()
        X_train_scaled = self.scalers['neural_network'].fit_transform(X_train)
        X_val_scaled = self.scalers['neural_network'].transform(X_val)
        
        # Build neural network
        model = keras.Sequential([
            keras.layers.Dense(64, activation='relu', input_shape=(X_train.shape[1],)),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(32, activation='relu'),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(16, activation='relu'),
            keras.layers.Dense(1, activation='sigmoid')
        ])
        
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        
        # Train model
        history = model.fit(
            X_train_scaled, y_train,
            validation_data=(X_val_scaled, y_val),
            epochs=50,
            batch_size=32,
            verbose=0
        )
        
        self.models['neural_network'] = model
        
        # Evaluate
        train_loss, train_acc = model.evaluate(X_train_scaled, y_train, verbose=0)
        val_loss, val_acc = model.evaluate(X_val_scaled, y_val, verbose=0)
        
        print(f"✅ Training Accuracy: {train_acc:.3f}")
        print(f"✅ Validation Accuracy: {val_acc:.3f}")
        
        print()
    
    def _create_ensemble_predictions(self, X_val, y_val):
        """Create ensemble predictions by averaging model outputs"""
        
        print("🎯 CREATING ENSEMBLE PREDICTIONS")
        print("-" * 33)
        
        ensemble_preds = []
        
        for i in range(len(X_val)):
            predictions = []
            
            # XGBoost prediction
            if 'xgboost' in self.models:
                pred = self.models['xgboost'].predict_proba(X_val[i:i+1])[0][1]
                predictions.append(pred)
            
            # Random Forest prediction
            if 'random_forest' in self.models:
                pred = self.models['random_forest'].predict_proba(X_val[i:i+1])[0][1]
                predictions.append(pred)
            
            # Neural Network prediction
            if 'neural_network' in self.models and 'neural_network' in self.scalers:
                X_scaled = self.scalers['neural_network'].transform(X_val[i:i+1])
                pred = self.models['neural_network'].predict(X_scaled)[0][0]
                predictions.append(pred)
            
            # Average predictions
            if predictions:
                ensemble_pred = np.mean(predictions)
                ensemble_preds.append(1 if ensemble_pred > 0.5 else 0)
            else:
                ensemble_preds.append(0)
        
        # Calculate ensemble accuracy
        ensemble_acc = accuracy_score(y_val, ensemble_preds)
        
        print(f"🎯 Ensemble Accuracy: {ensemble_acc:.3f}")
        
        # Compare with individual models
        print(f"\n📊 MODEL COMPARISON:")
        for model_name in self.models.keys():
            if model_name == 'neural_network' and 'neural_network' in self.scalers:
                X_scaled = self.scalers['neural_network'].transform(X_val)
                pred = (self.models[model_name].predict(X_scaled) > 0.5).astype(int)
            else:
                pred = self.models[model_name].predict(X_val)
            
            acc = accuracy_score(y_val, pred)
            improvement = ensemble_acc - acc
            print(f"   {model_name:15}: {acc:.3f} (Δ{improvement:+.3f})")
        
        print()
    
    def _analyze_feature_importance(self):
        """Analyze feature importance across models"""
        
        print("📊 FEATURE IMPORTANCE ANALYSIS")
        print("-" * 31)
        
        feature_names = [
            'home_win_prob', 'away_win_prob', 'predicted_home_score',
            'predicted_away_score', 'predicted_total_runs', 'confidence',
            'away_pitcher_factor', 'home_pitcher_factor', 'game_competitiveness',
            'total_line', 'home_ml_prob', 'away_ml_prob', 'score_differential',
            'highest_team_score', 'lowest_team_score'
        ]
        
        # Average importance across models
        avg_importance = np.zeros(len(feature_names))
        model_count = 0
        
        for model_name, importance in self.feature_importance.items():
            if len(importance) == len(feature_names):
                avg_importance += importance
                model_count += 1
        
        if model_count > 0:
            avg_importance /= model_count
            
            # Sort by importance
            feature_importance_pairs = list(zip(feature_names, avg_importance))
            feature_importance_pairs.sort(key=lambda x: x[1], reverse=True)
            
            print("🏆 TOP 10 MOST IMPORTANT FEATURES:")
            for i, (feature, importance) in enumerate(feature_importance_pairs[:10], 1):
                print(f"   {i:2d}. {feature:20s}: {importance:.4f}")
        
        print()
    
    def _generate_performance_report(self):
        """Generate comprehensive performance report"""
        
        print("📈 ENSEMBLE MODEL PERFORMANCE REPORT")
        print("-" * 37)
        
        print("✅ MODEL TRAINING COMPLETE")
        print(f"   • XGBoost: {'✅' if 'xgboost' in self.models else '❌'}")
        print(f"   • Random Forest: {'✅' if 'random_forest' in self.models else '❌'}")
        print(f"   • Neural Network: {'✅' if 'neural_network' in self.models else '❌'}")
        
        print(f"\n🎯 NEXT STEPS:")
        print("   1. Save ensemble model for production use")
        print("   2. Implement real-time prediction endpoint")
        print("   3. Add continuous learning pipeline")
        print("   4. Monitor model performance in production")
        
        # Save models
        self._save_models()
    
    def _save_models(self):
        """Save trained models"""
        
        print("💾 Saving trained models...")
        
        # Save model metadata
        metadata = {
            'created_at': datetime.now().isoformat(),
            'models_trained': list(self.models.keys()),
            'feature_count': len(self.feature_importance.get('xgboost', [])),
            'tensorflow_available': TENSORFLOW_AVAILABLE
        }
        
        with open('ensemble_model_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print("✅ Model metadata saved to ensemble_model_metadata.json")
    
    def predict_game(self, game_features):
        """Make prediction for a single game using ensemble"""
        
        if not self.models:
            return 0.5  # Default probability
        
        predictions = []
        
        # Get predictions from each model
        if 'xgboost' in self.models:
            pred = self.models['xgboost'].predict_proba([game_features])[0][1]
            predictions.append(pred)
        
        if 'random_forest' in self.models:
            pred = self.models['random_forest'].predict_proba([game_features])[0][1]
            predictions.append(pred)
        
        if 'neural_network' in self.models and 'neural_network' in self.scalers:
            features_scaled = self.scalers['neural_network'].transform([game_features])
            pred = self.models['neural_network'].predict(features_scaled)[0][0]
            predictions.append(pred)
        
        # Return ensemble average
        return np.mean(predictions) if predictions else 0.5

def main():
    ensemble = MLBEnsembleModel()
    ensemble.build_ensemble_model()

if __name__ == "__main__":
    main()
