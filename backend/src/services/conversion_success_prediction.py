"""
Conversion Success Prediction with ML Models

This service provides machine learning-based prediction of conversion success
for Java to Bedrock modding concept transformations.
"""

import logging
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, mean_squared_error
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func

from ..db.crud import get_async_session
from ..db.knowledge_graph_crud import (
    KnowledgeNodeCRUD, KnowledgeRelationshipCRUD, ConversionPatternCRUD
)
from ..models import (
    KnowledgeNode, KnowledgeRelationship, ConversionPattern
)

logger = logging.getLogger(__name__)


class PredictionType(Enum):
    """Types of conversion success predictions."""
    OVERALL_SUCCESS = "overall_success"
    FEATURE_COMPLETENESS = "feature_completeness"
    PERFORMANCE_IMPACT = "performance_impact"
    COMPATIBILITY_SCORE = "compatibility_score"
    RISK_ASSESSMENT = "risk_assessment"
    CONVERSION_TIME = "conversion_time"
    RESOURCE_USAGE = "resource_usage"


@dataclass
class ConversionFeatures:
    """Features for conversion success prediction."""
    java_concept: str
    bedrock_concept: str
    pattern_type: str
    minecraft_version: str
    node_type: str
    platform: str
    description_length: int
    expert_validated: bool
    community_rating: float
    usage_count: int
    relationship_count: int
    success_history: List[float]
    feature_count: int
    complexity_score: float
    version_compatibility: float
    cross_platform_difficulty: float


@dataclass
class PredictionResult:
    """Result of conversion success prediction."""
    prediction_type: PredictionType
    predicted_value: float
    confidence: float
    feature_importance: Dict[str, float]
    risk_factors: List[str]
    success_factors: List[str]
    recommendations: List[str]
    prediction_metadata: Dict[str, Any]


class ConversionSuccessPredictionService:
    """ML-based conversion success prediction service."""
    
    def __init__(self):
        self.is_trained = False
        self.models = {
            "overall_success": RandomForestClassifier(n_estimators=100, random_state=42),
            "feature_completeness": GradientBoostingRegressor(n_estimators=100, random_state=42),
            "performance_impact": GradientBoostingRegressor(n_estimators=100, random_state=42),
            "compatibility_score": GradientBoostingRegressor(n_estimators=100, random_state=42),
            "risk_assessment": RandomForestClassifier(n_estimators=100, random_state=42),
            "conversion_time": GradientBoostingRegressor(n_estimators=100, random_state=42),
            "resource_usage": GradientBoostingRegressor(n_estimators=100, random_state=42)
        }
        self.preprocessors = {
            "feature_scaler": StandardScaler(),
            "label_encoders": {}
        }
        self.feature_names = []
        self.training_data = []
        self.model_metrics = {}
        self.prediction_history = []
        
    async def train_models(
        self,
        db: AsyncSession,
        force_retrain: bool = False
    ) -> Dict[str, Any]:
        """
        Train ML models using historical conversion data.
        
        Args:
            db: Database session
            force_retrain: Force retraining even if models are already trained
        
        Returns:
            Training results with model metrics
        """
        try:
            if self.is_trained and not force_retrain:
                return {
                    "success": True,
                    "message": "Models already trained",
                    "metrics": self.model_metrics
                }
            
            # Step 1: Collect training data
            training_data = await self._collect_training_data(db)
            
            if len(training_data) < 100:
                return {
                    "success": False,
                    "error": "Insufficient training data (minimum 100 samples required)",
                    "available_samples": len(training_data)
                }
            
            # Step 2: Prepare features and targets
            features, targets = await self._prepare_training_data(training_data)
            
            if len(features) < 50:
                return {
                    "success": False,
                    "error": "Insufficient feature data (minimum 50 feature samples required)",
                    "available_features": len(features)
                }
            
            # Step 3: Train each model
            training_results = {}
            
            for prediction_type in PredictionType:
                if prediction_type.value in targets:
                    result = await self._train_model(
                        prediction_type, features, targets[prediction_type.value]
                    )
                    training_results[prediction_type.value] = result
            
            # Step 4: Store training data and feature names
            self.training_data = training_data
            self.feature_names = list(features[0].keys()) if features else []
            
            # Convert to numpy arrays for models
            X = np.array([list(f.values()) for f in features])
            X_scaled = self.preprocessors["feature_scaler"].fit_transform(X)
            
            # Train final models with all data
            for prediction_type in PredictionType:
                if prediction_type.value in targets:
                    y = targets[prediction_type.value]
                    if prediction_type in [PredictionType.OVERALL_SUCCESS, PredictionType.RISK_ASSESSMENT]:
                        self.models[prediction_type.value].fit(X_scaled, y)
                    else:
                        self.models[prediction_type.value].fit(X_scaled, y)
            
            self.is_trained = True
            
            # Calculate overall metrics
            overall_metrics = {
                "training_samples": len(training_data),
                "feature_count": len(self.feature_names),
                "models_trained": len(training_results),
                "training_timestamp": datetime.utcnow().isoformat()
            }
            
            # Store model metrics
            self.model_metrics = {**training_results, **overall_metrics}
            
            return {
                "success": True,
                "message": "ML models trained successfully",
                "metrics": self.model_metrics,
                "training_samples": len(training_data),
                "feature_count": len(self.feature_names)
            }
            
        except Exception as e:
            logger.error(f"Error training conversion prediction models: {e}")
            return {
                "success": False,
                "error": f"Model training failed: {str(e)}"
            }
    
    async def predict_conversion_success(
        self,
        java_concept: str,
        bedrock_concept: str = None,
        pattern_type: str = "unknown",
        minecraft_version: str = "latest",
        context_data: Dict[str, Any] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Predict conversion success for Java concept.
        
        Args:
            java_concept: Java concept to convert
            bedrock_concept: Target Bedrock concept (optional)
            pattern_type: Conversion pattern type
            minecraft_version: Minecraft version
            context_data: Additional context
            db: Database session
        
        Returns:
            Comprehensive prediction results with confidence scores
        """
        try:
            if not self.is_trained:
                return {
                    "success": False,
                    "error": "ML models not trained. Call train_models() first."
                }
            
            # Step 1: Extract conversion features
            features = await self._extract_conversion_features(
                java_concept, bedrock_concept, pattern_type, minecraft_version, db
            )
            
            if not features:
                return {
                    "success": False,
                    "error": "Unable to extract conversion features",
                    "java_concept": java_concept
                }
            
            # Step 2: Prepare features for prediction
            feature_vector = await self._prepare_feature_vector(features)
            
            # Step 3: Make predictions for all types
            predictions = {}
            
            for prediction_type in PredictionType:
                prediction = await self._make_prediction(
                    prediction_type, feature_vector, features
                )
                predictions[prediction_type.value] = prediction
            
            # Step 4: Analyze overall conversion viability
            viability_analysis = await self._analyze_conversion_viability(
                java_concept, bedrock_concept, predictions
            )
            
            # Step 5: Generate conversion recommendations
            recommendations = await self._generate_conversion_recommendations(
                features, predictions, viability_analysis
            )
            
            # Step 6: Identify potential issues and mitigations
            issues_mitigations = await self._identify_issues_mitigations(
                features, predictions
            )
            
            # Step 7: Store prediction for learning
            await self._store_prediction(
                java_concept, bedrock_concept, predictions, context_data
            )
            
            return {
                "success": True,
                "java_concept": java_concept,
                "bedrock_concept": bedrock_concept,
                "pattern_type": pattern_type,
                "minecraft_version": minecraft_version,
                "predictions": predictions,
                "viability_analysis": viability_analysis,
                "recommendations": recommendations,
                "issues_mitigations": issues_mitigations,
                "prediction_metadata": {
                    "model_version": "1.0",
                    "prediction_timestamp": datetime.utcnow().isoformat(),
                    "feature_count": len(self.feature_names),
                    "confidence_threshold": 0.7
                }
            }
            
        except Exception as e:
            logger.error(f"Error predicting conversion success: {e}")
            return {
                "success": False,
                "error": f"Prediction failed: {str(e)}",
                "java_concept": java_concept
            }
    
    async def batch_predict_success(
        self,
        conversions: List[Dict[str, Any]],
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Predict success for multiple conversions.
        
        Args:
            conversions: List of conversion requests with java_concept, bedrock_concept, etc.
            db: Database session
        
        Returns:
            Batch prediction results with comparative analysis
        """
        try:
            if not self.is_trained:
                return {
                    "success": False,
                    "error": "ML models not trained. Call train_models() first."
                }
            
            batch_results = {}
            
            # Process each conversion
            for i, conversion in enumerate(conversions):
                java_concept = conversion.get("java_concept")
                bedrock_concept = conversion.get("bedrock_concept")
                pattern_type = conversion.get("pattern_type", "unknown")
                minecraft_version = conversion.get("minecraft_version", "latest")
                context_data = conversion.get("context_data", {})
                
                result = await self.predict_conversion_success(
                    java_concept, bedrock_concept, pattern_type, 
                    minecraft_version, context_data, db
                )
                
                batch_results[f"conversion_{i+1}"] = {
                    "input": conversion,
                    "prediction": result,
                    "success_probability": result.get("predictions", {}).get("overall_success", {}).get("predicted_value", 0.0)
                }
            
            # Analyze batch results
            batch_analysis = await self._analyze_batch_predictions(batch_results)
            
            # Rank conversions by success probability
            ranked_conversions = await self._rank_conversions_by_success(batch_results)
            
            # Identify batch patterns
            batch_patterns = await self._identify_batch_patterns(batch_results)
            
            return {
                "success": True,
                "total_conversions": len(conversions),
                "successful_predictions": len(batch_results),
                "batch_results": batch_results,
                "batch_analysis": batch_analysis,
                "ranked_conversions": ranked_conversions,
                "batch_patterns": batch_patterns,
                "batch_metadata": {
                    "prediction_timestamp": datetime.utcnow().isoformat(),
                    "average_success_probability": np.mean([
                        result["success_probability"] for result in batch_results.values()
                    ]) if batch_results else 0.0
                }
            }
            
        except Exception as e:
            logger.error(f"Error in batch success prediction: {e}")
            return {
                "success": False,
                "error": f"Batch prediction failed: {str(e)}",
                "total_conversions": len(conversions)
            }
    
    async def update_models_with_feedback(
        self,
        conversion_id: str,
        actual_result: Dict[str, Any],
        feedback_data: Dict[str, Any] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Update ML models with actual conversion results.
        
        Args:
            conversion_id: ID of the conversion
            actual_result: Actual conversion outcome
            feedback_data: Additional feedback
            db: Database session
        
        Returns:
            Update results with model improvement metrics
        """
        try:
            # Find stored prediction
            stored_prediction = None
            for prediction in self.prediction_history:
                if prediction.get("conversion_id") == conversion_id:
                    stored_prediction = prediction
                    break
            
            if not stored_prediction:
                return {
                    "success": False,
                    "error": "No stored prediction found for conversion"
                }
            
            # Calculate prediction accuracy
            predictions = stored_prediction.get("predictions", {})
            accuracy_scores = {}
            
            for pred_type, pred_result in predictions.items():
                predicted_value = pred_result.get("predicted_value", 0.0)
                actual_value = actual_result.get(pred_type, 0.0)
                
                if pred_type in ["overall_success", "risk_assessment"]:
                    # Classification accuracy
                    accuracy = 1.0 if abs(predicted_value - actual_value) < 0.1 else 0.0
                else:
                    # Regression accuracy (normalized error)
                    error = abs(predicted_value - actual_value)
                    accuracy = max(0.0, 1.0 - error)
                
                accuracy_scores[pred_type] = accuracy
            
            # Update model metrics
            model_improvements = await self._update_model_metrics(accuracy_scores)
            
            # Create training example for future retraining
            training_example = await self._create_training_example(
                stored_prediction, actual_result, feedback_data
            )
            
            # Add to training data
            if training_example:
                self.training_data.append(training_example)
            
            # Update prediction record
            update_record = {
                "conversion_id": conversion_id,
                "update_timestamp": datetime.utcnow().isoformat(),
                "actual_result": actual_result,
                "feedback_data": feedback_data,
                "accuracy_scores": accuracy_scores,
                "model_improvements": model_improvements
            }
            
            return {
                "success": True,
                "accuracy_scores": accuracy_scores,
                "model_improvements": model_improvements,
                "training_example_created": training_example is not None,
                "update_record": update_record,
                "recommendation": await self._get_model_update_recommendation(accuracy_scores)
            }
            
        except Exception as e:
            logger.error(f"Error updating models with feedback: {e}")
            return {
                "success": False,
                "error": f"Model update failed: {str(e)}"
            }
    
    async def get_prediction_insights(
        self,
        days: int = 30,
        prediction_type: Optional[PredictionType] = None
    ) -> Dict[str, Any]:
        """
        Get insights about prediction performance.
        
        Args:
            days: Number of days to analyze
            prediction_type: Filter by prediction type
        
        Returns:
            Performance insights and trends
        """
        try:
            if not self.is_trained:
                return {
                    "success": False,
                    "error": "ML models not trained"
                }
            
            # Get recent predictions
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            recent_predictions = [
                pred for pred in self.prediction_history
                if datetime.fromisoformat(pred["timestamp"]) > cutoff_date
            ]
            
            if prediction_type:
                recent_predictions = [
                    pred for pred in recent_predictions
                    if prediction_type.value in pred.get("predictions", {})
                ]
            
            # Analyze prediction accuracy
            accuracy_analysis = await self._analyze_prediction_accuracy(recent_predictions)
            
            # Analyze feature importance trends
            feature_trends = await self._analyze_feature_importance_trends(recent_predictions)
            
            # Identify prediction patterns
            prediction_patterns = await self._identify_prediction_patterns(recent_predictions)
            
            return {
                "success": True,
                "analysis_period_days": days,
                "prediction_type_filter": prediction_type.value if prediction_type else None,
                "total_predictions": len(recent_predictions),
                "accuracy_analysis": accuracy_analysis,
                "feature_trends": feature_trends,
                "prediction_patterns": prediction_patterns,
                "insights_metadata": {
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "model_trained": self.is_trained,
                    "training_samples": len(self.training_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting prediction insights: {e}")
            return {
                "success": False,
                "error": f"Insights analysis failed: {str(e)}"
            }
    
    # Private Helper Methods
    
    async def _collect_training_data(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Collect training data from successful and failed conversions."""
        try:
            training_data = []
            
            # Get conversion patterns with success metrics
            patterns = await ConversionPatternCRUD.get_by_version(
                db, "latest", validation_status="validated", limit=1000
            )
            
            for pattern in patterns:
                # Extract features from pattern
                training_sample = {
                    "java_concept": pattern.java_concept,
                    "bedrock_concept": pattern.bedrock_concept,
                    "pattern_type": pattern.pattern_type,
                    "minecraft_version": pattern.minecraft_version,
                    "overall_success": 1 if pattern.success_rate > 0.7 else 0,
                    "feature_completeness": pattern.success_rate or 0.5,
                    "performance_impact": 0.8 if pattern.success_rate > 0.8 else 0.5,
                    "compatibility_score": 0.9 if pattern.minecraft_version == "latest" else 0.7,
                    "risk_assessment": 0 if pattern.success_rate > 0.8 else 1,
                    "conversion_time": 1.0 if pattern.pattern_type == "direct_conversion" else 2.5,
                    "resource_usage": 0.5 if pattern.success_rate > 0.7 else 0.8,
                    "expert_validated": pattern.expert_validated,
                    "usage_count": pattern.usage_count or 0,
                    "confidence_score": pattern.confidence_score or 0.5,
                    "features": json.loads(pattern.conversion_features or "{}"),
                    "metadata": {
                        "source": "conversion_patterns",
                        "validation_results": json.loads(pattern.validation_results or "{}")
                    }
                }
                training_data.append(training_sample)
            
            # Get knowledge nodes and relationships for additional training data
            nodes = await KnowledgeNodeCRUD.get_by_type(
                db, "java_concept", "latest", limit=500
            )
            
            for node in nodes:
                # Find relationships for this node
                relationships = await KnowledgeRelationshipCRUD.get_by_source(
                    db, str(node.id), "converts_to"
                )
                
                for rel in relationships:
                    training_sample = {
                        "java_concept": node.name,
                        "bedrock_concept": rel.target_node_name or "",
                        "pattern_type": "direct_conversion",
                        "minecraft_version": node.minecraft_version,
                        "overall_success": 1 if rel.confidence_score > 0.7 else 0,
                        "feature_completeness": rel.confidence_score or 0.5,
                        "performance_impact": 0.7,
                        "compatibility_score": 0.8 if node.minecraft_version == "latest" else 0.6,
                        "risk_assessment": 0 if rel.confidence_score > 0.8 else 1,
                        "conversion_time": 1.0,
                        "resource_usage": 0.6,
                        "expert_validated": node.expert_validated and rel.expert_validated,
                        "usage_count": 0,
                        "confidence_score": rel.confidence_score or 0.5,
                        "features": json.loads(node.properties or "{}"),
                        "metadata": {
                            "source": "knowledge_graph",
                            "node_id": str(node.id),
                            "relationship_id": str(rel.id)
                        }
                    }
                    training_data.append(training_sample)
            
            logger.info(f"Collected {len(training_data)} training samples")
            return training_data
            
        except Exception as e:
            logger.error(f"Error collecting training data: {e}")
            return []
    
    async def _prepare_training_data(
        self, 
        training_data: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]]]:
        """Prepare features and targets for training."""
        try:
            features = []
            targets = {
                "overall_success": [],
                "feature_completeness": [],
                "performance_impact": [],
                "compatibility_score": [],
                "risk_assessment": [],
                "conversion_time": [],
                "resource_usage": []
            }
            
            for sample in training_data:
                # Extract numerical features
                feature_dict = {
                    "expert_validated": int(sample.get("expert_validated", False)),
                    "usage_count": min(sample.get("usage_count", 0) / 100.0, 1.0),
                    "confidence_score": sample.get("confidence_score", 0.5),
                    "feature_count": len(sample.get("features", {})),
                    "pattern_type_encoded": self._encode_pattern_type(sample.get("pattern_type", "")),
                    "version_compatibility": 0.9 if sample.get("minecraft_version") == "latest" else 0.7
                }
                
                features.append(feature_dict)
                
                # Extract targets
                for target_key in targets:
                    if target_key in sample:
                        targets[target_key].append(sample[target_key])
            
            return features, targets
            
        except Exception as e:
            logger.error(f"Error preparing training data: {e}")
            return [], {}
    
    def _encode_pattern_type(self, pattern_type: str) -> float:
        """Encode pattern type as numerical value."""
        pattern_encoding = {
            "direct_conversion": 1.0,
            "entity_conversion": 0.8,
            "block_conversion": 0.7,
            "item_conversion": 0.6,
            "behavior_conversion": 0.5,
            "command_conversion": 0.4,
            "unknown": 0.3
        }
        return pattern_encoding.get(pattern_type, 0.3)
    
    async def _train_model(
        self, 
        prediction_type: PredictionType, 
        features: List[Dict[str, Any]], 
        targets: List[float]
    ) -> Dict[str, Any]:
        """Train a specific prediction model."""
        try:
            if len(features) < 10 or len(targets) < 10:
                return {"error": "Insufficient data for training"}
            
            # Convert to numpy arrays
            X = np.array([list(f.values()) for f in features])
            y = np.array(targets)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.preprocessors["feature_scaler"].fit_transform(X_train)
            X_test_scaled = self.preprocessors["feature_scaler"].transform(X_test)
            
            # Train model
            model = self.models[prediction_type.value]
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test_scaled)
            
            if prediction_type in [PredictionType.OVERALL_SUCCESS, PredictionType.RISK_ASSESSMENT]:
                # Classification metrics
                accuracy = accuracy_score(y_test, y_pred)
                precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
                recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
                f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
                
                metrics = {
                    "accuracy": accuracy,
                    "precision": precision,
                    "recall": recall,
                    "f1_score": f1
                }
            else:
                # Regression metrics
                mse = mean_squared_error(y_test, y_pred)
                rmse = np.sqrt(mse)
                
                metrics = {
                    "mse": mse,
                    "rmse": rmse,
                    "mae": np.mean(np.abs(y_test - y_pred))
                }
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
            metrics["cv_mean"] = cv_scores.mean()
            metrics["cv_std"] = cv_scores.std()
            
            return {
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "feature_count": X_train.shape[1],
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"Error training model {prediction_type}: {e}")
            return {"error": str(e)}
    
    async def _extract_conversion_features(
        self,
        java_concept: str,
        bedrock_concept: Optional[str],
        pattern_type: str,
        minecraft_version: str,
        db: AsyncSession
    ) -> Optional[ConversionFeatures]:
        """Extract features for conversion prediction."""
        try:
            # Search for Java concept
            java_nodes = await KnowledgeNodeCRUD.search(db, java_concept, limit=10)
            java_node = None
            
            for node in java_nodes:
                if node.platform in ["java", "both"]:
                    java_node = node
                    break
            
            if not java_node:
                # Create basic features from concept name
                return ConversionFeatures(
                    java_concept=java_concept,
                    bedrock_concept=bedrock_concept or "",
                    pattern_type=pattern_type,
                    minecraft_version=minecraft_version,
                    node_type="unknown",
                    platform="java",
                    description_length=len(java_concept),
                    expert_validated=False,
                    community_rating=0.0,
                    usage_count=0,
                    relationship_count=0,
                    success_history=[],
                    feature_count=0,
                    complexity_score=0.5,
                    version_compatibility=0.7,
                    cross_platform_difficulty=0.5
                )
            
            # Get relationships
            relationships = await KnowledgeRelationshipCRUD.get_by_source(
                db, str(java_node.id)
            )
            
            # Calculate features
            features = ConversionFeatures(
                java_concept=java_concept,
                bedrock_concept=bedrock_concept or "",
                pattern_type=pattern_type,
                minecraft_version=minecraft_version,
                node_type=java_node.node_type or "unknown",
                platform=java_node.platform,
                description_length=len(java_node.description or ""),
                expert_validated=java_node.expert_validated or False,
                community_rating=java_node.community_rating or 0.0,
                usage_count=0,  # Would be populated from usage logs
                relationship_count=len(relationships),
                success_history=[],  # Would be populated from historical data
                feature_count=len(json.loads(java_node.properties or "{}")),
                complexity_score=self._calculate_complexity(java_node),
                version_compatibility=0.9 if minecraft_version == "latest" else 0.7,
                cross_platform_difficulty=self._calculate_cross_platform_difficulty(
                    java_node, bedrock_concept
                )
            )
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting conversion features: {e}")
            return None
    
    def _calculate_complexity(self, node: KnowledgeNode) -> float:
        """Calculate complexity score for a node."""
        try:
            complexity = 0.0
            
            # Base complexity from properties
            properties = json.loads(node.properties or "{}")
            complexity += len(properties) * 0.1
            
            # Complexity from description length
            desc_len = len(node.description or "")
            complexity += min(desc_len / 1000.0, 1.0) * 0.3
            
            # Node type complexity
            type_complexity = {
                "entity": 0.8,
                "block": 0.7,
                "item": 0.6,
                "behavior": 0.9,
                "command": 0.5,
                "unknown": 0.5
            }
            complexity += type_complexity.get(node.node_type, 0.5) * 0.2
            
            return min(complexity, 1.0)
            
        except Exception:
            return 0.5
    
    def _calculate_cross_platform_difficulty(
        self, 
        java_node: KnowledgeNode, 
        bedrock_concept: Optional[str]
    ) -> float:
        """Calculate cross-platform conversion difficulty."""
        try:
            difficulty = 0.5  # Base difficulty
            
            # Platform-specific factors
            if java_node.platform == "both":
                difficulty -= 0.2
            elif java_node.platform == "java":
                difficulty += 0.1
            
            # Node type difficulty
            type_difficulty = {
                "entity": 0.8,
                "block": 0.6,
                "item": 0.4,
                "behavior": 0.9,
                "command": 0.7,
                "unknown": 0.5
            }
            difficulty += type_difficulty.get(java_node.node_type, 0.5) * 0.2
            
            return max(0.0, min(1.0, difficulty))
            
        except Exception:
            return 0.5
    
    async def _prepare_feature_vector(self, features: ConversionFeatures) -> np.ndarray:
        """Prepare feature vector for ML model."""
        try:
            feature_vector = np.array([
                features.expert_validated,
                min(features.usage_count / 100.0, 1.0),
                features.community_rating,
                features.feature_count / 10.0,  # Normalize
                self._encode_pattern_type(features.pattern_type),
                features.version_compatibility,
                features.complexity_score,
                features.cross_platform_difficulty,
                features.relationship_count / 10.0,  # Normalize
                1.0 if features.minecraft_version == "latest" else 0.7
            ])
            
            # Scale features
            feature_vector = self.preprocessors["feature_scaler"].transform([feature_vector])
            
            return feature_vector[0]
            
        except Exception as e:
            logger.error(f"Error preparing feature vector: {e}")
            return np.zeros(10)
    
    async def _make_prediction(
        self, 
        prediction_type: PredictionType, 
        feature_vector: np.ndarray, 
        features: ConversionFeatures
    ) -> PredictionResult:
        """Make prediction for a specific type."""
        try:
            model = self.models[prediction_type.value]
            prediction = model.predict([feature_vector])[0]
            
            # Get feature importance
            feature_importance = self._get_feature_importance(model, prediction_type)
            
            # Calculate prediction confidence
            confidence = self._calculate_prediction_confidence(model, feature_vector, prediction_type)
            
            # Generate risk and success factors
            risk_factors = self._identify_risk_factors(features, prediction_type, prediction)
            success_factors = self._identify_success_factors(features, prediction_type, prediction)
            
            # Generate recommendations
            recommendations = self._generate_type_recommendations(
                prediction_type, prediction, features
            )
            
            return PredictionResult(
                prediction_type=prediction_type,
                predicted_value=float(prediction),
                confidence=confidence,
                feature_importance=feature_importance,
                risk_factors=risk_factors,
                success_factors=success_factors,
                recommendations=recommendations,
                prediction_metadata={
                    "model_type": type(model).__name__,
                    "feature_count": len(feature_vector),
                    "prediction_time": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error making prediction for {prediction_type}: {e}")
            return PredictionResult(
                prediction_type=prediction_type,
                predicted_value=0.5,
                confidence=0.0,
                feature_importance={},
                risk_factors=[f"Prediction error: {str(e)}"],
                success_factors=[],
                recommendations=["Retry prediction"],
                prediction_metadata={"error": str(e)}
            )
    
    def _get_feature_importance(
        self, 
        model, 
        prediction_type: PredictionType
    ) -> Dict[str, float]:
        """Get feature importance from model."""
        try:
            if hasattr(model, 'feature_importances_'):
                # Tree-based models
                importance = model.feature_importances_
            elif hasattr(model, 'coef_'):
                # Linear models
                importance = np.abs(model.coef_)
            else:
                return {}
            
            feature_names = [
                "expert_validated",
                "usage_count_normalized",
                "community_rating",
                "feature_count_normalized",
                "pattern_type_encoded",
                "version_compatibility",
                "complexity_score",
                "cross_platform_difficulty",
                "relationship_count_normalized",
                "is_latest_version"
            ]
            
            return {
                feature_names[i]: float(importance[i])
                for i in range(min(len(feature_names), len(importance)))
            }
            
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return {}
    
    def _calculate_prediction_confidence(
        self, 
        model, 
        feature_vector: np.ndarray, 
        prediction_type: PredictionType
    ) -> float:
        """Calculate confidence in prediction."""
        try:
            if hasattr(model, 'predict_proba'):
                # Classification models
                probabilities = model.predict_proba([feature_vector])
                confidence = max(probabilities[0])
            else:
                # Regression models - use prediction variance or distance from training data
                confidence = 0.7  # Default confidence for regression
            
            return confidence
            
        except Exception:
            return 0.5
    
    def _identify_risk_factors(
        self, 
        features: ConversionFeatures, 
        prediction_type: PredictionType, 
        prediction: float
    ) -> List[str]:
        """Identify risk factors for prediction."""
        risk_factors = []
        
        if not features.expert_validated:
            risk_factors.append("No expert validation - higher uncertainty")
        
        if features.community_rating < 0.5:
            risk_factors.append("Low community rating - potential issues")
        
        if features.usage_count < 5:
            risk_factors.append("Limited usage data - untested conversion")
        
        if features.complexity_score > 0.8:
            risk_factors.append("High complexity - difficult conversion")
        
        if features.cross_platform_difficulty > 0.7:
            risk_factors.append("High cross-platform difficulty")
        
        if prediction_type == PredictionType.OVERALL_SUCCESS and prediction < 0.5:
            risk_factors.append("Low predicted success probability")
        
        if prediction_type == PredictionType.RISK_ASSESSMENT and prediction > 0.6:
            risk_factors.append("High risk assessment")
        
        return risk_factors
    
    def _identify_success_factors(
        self, 
        features: ConversionFeatures, 
        prediction_type: PredictionType, 
        prediction: float
    ) -> List[str]:
        """Identify success factors for prediction."""
        success_factors = []
        
        if features.expert_validated:
            success_factors.append("Expert validated - high reliability")
        
        if features.community_rating > 0.8:
            success_factors.append("High community rating - proven concept")
        
        if features.usage_count > 50:
            success_factors.append("High usage - well-tested conversion")
        
        if features.version_compatibility > 0.8:
            success_factors.append("Good version compatibility")
        
        if features.cross_platform_difficulty < 0.3:
            success_factors.append("Low conversion difficulty")
        
        if prediction_type == PredictionType.OVERALL_SUCCESS and prediction > 0.8:
            success_factors.append("High predicted success probability")
        
        if prediction_type == PredictionType.FEATURE_COMPLETENESS and prediction > 0.8:
            success_factors.append("High feature completeness expected")
        
        return success_factors
    
    def _generate_type_recommendations(
        self, 
        prediction_type: PredictionType, 
        prediction: float, 
        features: ConversionFeatures
    ) -> List[str]:
        """Generate recommendations for specific prediction type."""
        recommendations = []
        
        if prediction_type == PredictionType.OVERALL_SUCCESS:
            if prediction > 0.8:
                recommendations.append("High success probability - proceed with confidence")
            elif prediction > 0.6:
                recommendations.append("Moderate success probability - test thoroughly")
            else:
                recommendations.append("Low success probability - consider alternatives")
        
        elif prediction_type == PredictionType.FEATURE_COMPLETENESS:
            if prediction < 0.7:
                recommendations.append("Expected feature gaps - plan for manual completion")
        
        elif prediction_type == PredictionType.PERFORMANCE_IMPACT:
            if prediction > 0.8:
                recommendations.append("High performance impact - optimize critical paths")
            elif prediction < 0.3:
                recommendations.append("Low performance impact - safe for performance")
        
        elif prediction_type == PredictionType.CONVERSION_TIME:
            if prediction > 2.0:
                recommendations.append("Long conversion time - consider breaking into steps")
        
        elif prediction_type == PredictionType.RESOURCE_USAGE:
            if prediction > 0.8:
                recommendations.append("High resource usage - monitor system resources")
        
        return recommendations
    
    async def _analyze_conversion_viability(
        self,
        java_concept: str,
        bedrock_concept: Optional[str],
        predictions: Dict[str, PredictionResult]
    ) -> Dict[str, Any]:
        """Analyze overall conversion viability."""
        try:
            overall_success = predictions.get("overall_success", PredictionResult(
                PredictionType.OVERALL_SUCCESS, 0.0, 0.0, {}, [], [], [], {}
            ))
            
            risk_assessment = predictions.get("risk_assessment", PredictionResult(
                PredictionType.RISK_ASSESSMENT, 0.0, 0.0, {}, [], [], [], {}
            ))
            
            feature_completeness = predictions.get("feature_completeness", PredictionResult(
                PredictionType.FEATURE_COMPLETENESS, 0.0, 0.0, {}, [], [], [], {}
            ))
            
            # Calculate viability score
            viability_score = (
                overall_success.predicted_value * 0.4 +
                (1.0 - risk_assessment.predicted_value) * 0.3 +
                feature_completeness.predicted_value * 0.3
            )
            
            # Determine viability level
            if viability_score > 0.8:
                viability_level = "high"
            elif viability_score > 0.6:
                viability_level = "medium"
            elif viability_score > 0.4:
                viability_level = "low"
            else:
                viability_level = "very_low"
            
            # Generate viability assessment
            assessment = {
                "viability_score": viability_score,
                "viability_level": viability_level,
                "success_probability": overall_success.predicted_value,
                "risk_level": risk_assessment.predicted_value,
                "feature_coverage": feature_completeness.predicted_value,
                "recommended_action": self._get_recommended_action(viability_level),
                "confidence": np.mean([
                    overall_success.confidence,
                    risk_assessment.confidence,
                    feature_completeness.confidence
                ])
            }
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error analyzing conversion viability: {e}")
            return {
                "viability_score": 0.5,
                "viability_level": "unknown",
                "error": str(e)
            }
    
    def _get_recommended_action(self, viability_level: str) -> str:
        """Get recommended action based on viability level."""
        actions = {
            "high": "Proceed with conversion - high chance of success",
            "medium": "Proceed with caution - thorough testing recommended",
            "low": "Consider alternatives or seek expert consultation",
            "very_low": "Not recommended - significant risk of failure",
            "unknown": "Insufficient data for recommendation"
        }
        return actions.get(viability_level, "Unknown viability level")
    
    async def _generate_conversion_recommendations(
        self,
        features: ConversionFeatures,
        predictions: Dict[str, PredictionResult],
        viability_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate comprehensive conversion recommendations."""
        try:
            recommendations = []
            
            # Viability-based recommendations
            viability_level = viability_analysis.get("viability_level", "unknown")
            if viability_level == "high":
                recommendations.append("High viability - proceed with standard conversion process")
            elif viability_level == "medium":
                recommendations.append("Medium viability - implement additional testing")
            elif viability_level in ["low", "very_low"]:
                recommendations.append("Low viability - seek expert review first")
            
            # Feature-based recommendations
            if not features.expert_validated:
                recommendations.append("Request expert validation to improve reliability")
            
            if features.community_rating < 0.5:
                recommendations.append("Encourage community testing and feedback")
            
            if features.complexity_score > 0.8:
                recommendations.append("Break complex conversion into smaller steps")
            
            # Prediction-based recommendations
            overall_success = predictions.get("overall_success")
            if overall_success and overall_success.predicted_value < 0.6:
                recommendations.append("Consider alternative conversion approaches")
            
            performance_impact = predictions.get("performance_impact")
            if performance_impact and performance_impact.predicted_value > 0.8:
                recommendations.append("Implement performance monitoring and optimization")
            
            conversion_time = predictions.get("conversion_time")
            if conversion_time and conversion_time.predicted_value > 2.0:
                recommendations.append("Plan for extended conversion time")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating conversion recommendations: {e}")
            return ["Error generating recommendations"]
    
    async def _identify_issues_mitigations(
        self,
        features: ConversionFeatures,
        predictions: Dict[str, PredictionResult]
    ) -> Dict[str, List[str]]:
        """Identify potential issues and mitigations."""
        try:
            issues = []
            mitigations = []
            
            # Feature-based issues
            if features.complexity_score > 0.8:
                issues.append("High complexity may lead to conversion errors")
                mitigations.append("Implement step-by-step conversion with validation")
            
            if features.cross_platform_difficulty > 0.7:
                issues.append("Difficult cross-platform conversion")
                mitigations.append("Research platform-specific alternatives")
            
            # Prediction-based issues
            overall_success = predictions.get("overall_success")
            if overall_success and overall_success.predicted_value < 0.5:
                issues.append("Low success probability predicted")
                mitigations.append("Consider alternative conversion strategies")
            
            risk_assessment = predictions.get("risk_assessment")
            if risk_assessment and risk_assessment.predicted_value > 0.6:
                issues.append("High risk assessment")
                mitigations.append("Implement additional validation and testing")
            
            feature_completeness = predictions.get("feature_completeness")
            if feature_completeness and feature_completeness.predicted_value < 0.7:
                issues.append("Expected feature gaps")
                mitigations.append("Plan for manual feature completion")
            
            return {
                "issues": issues,
                "mitigations": mitigations
            }
            
        except Exception as e:
            logger.error(f"Error identifying issues and mitigations: {e}")
            return {
                "issues": [f"Error: {str(e)}"],
                "mitigations": []
            }
    
    async def _store_prediction(
        self,
        java_concept: str,
        bedrock_concept: Optional[str],
        predictions: Dict[str, PredictionResult],
        context_data: Optional[Dict[str, Any]]
    ):
        """Store prediction for learning."""
        try:
            prediction_record = {
                "conversion_id": f"{java_concept}_{bedrock_concept or 'unknown'}_{datetime.utcnow().timestamp()}",
                "timestamp": datetime.utcnow().isoformat(),
                "java_concept": java_concept,
                "bedrock_concept": bedrock_concept,
                "predictions": {
                    pred_type.value: {
                        "predicted_value": pred.predicted_value,
                        "confidence": pred.confidence,
                        "feature_importance": pred.feature_importance
                    }
                    for pred_type, pred in predictions.items()
                },
                "context_data": context_data or {}
            }
            
            self.prediction_history.append(prediction_record)
            
            # Limit history size
            if len(self.prediction_history) > 10000:
                self.prediction_history = self.prediction_history[-5000:]
                
        except Exception as e:
            logger.error(f"Error storing prediction: {e}")
    
    async def _analyze_batch_predictions(
        self, 
        batch_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze batch prediction results."""
        try:
            success_probabilities = []
            risk_assessments = []
            feature_completeness = []
            
            for result in batch_results.values():
                prediction = result.get("prediction", {})
                predictions = prediction.get("predictions", {})
                
                if "overall_success" in predictions:
                    success_probabilities.append(
                        predictions["overall_success"].get("predicted_value", 0.0)
                    )
                
                if "risk_assessment" in predictions:
                    risk_assessments.append(
                        predictions["risk_assessment"].get("predicted_value", 0.0)
                    )
                
                if "feature_completeness" in predictions:
                    feature_completeness.append(
                        predictions["feature_completeness"].get("predicted_value", 0.0)
                    )
            
            analysis = {
                "total_conversions": len(batch_results),
                "average_success_probability": np.mean(success_probabilities) if success_probabilities else 0.0,
                "average_risk_assessment": np.mean(risk_assessments) if risk_assessments else 0.0,
                "average_feature_completeness": np.mean(feature_completeness) if feature_completeness else 0.0,
                "high_success_count": sum(1 for p in success_probabilities if p > 0.8),
                "medium_success_count": sum(1 for p in success_probabilities if 0.5 < p <= 0.8),
                "low_success_count": sum(1 for p in success_probabilities if p <= 0.5)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing batch predictions: {e}")
            return {}
    
    async def _rank_conversions_by_success(
        self, 
        batch_results: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank conversions by success probability."""
        try:
            rankings = []
            
            for conv_id, result in batch_results.items():
                success_prob = result.get("success_probability", 0.0)
                input_data = result.get("input", {})
                
                rankings.append({
                    "conversion_id": conv_id,
                    "java_concept": input_data.get("java_concept"),
                    "bedrock_concept": input_data.get("bedrock_concept"),
                    "success_probability": success_prob,
                    "rank": 0  # Will be filled after sorting
                })
            
            # Sort by success probability (descending)
            rankings.sort(key=lambda x: x["success_probability"], reverse=True)
            
            # Assign ranks
            for i, ranking in enumerate(rankings):
                ranking["rank"] = i + 1
            
            return rankings
            
        except Exception as e:
            logger.error(f"Error ranking conversions: {e}")
            return []
    
    async def _identify_batch_patterns(
        self, 
        batch_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Identify patterns across batch predictions."""
        try:
            pattern_types = []
            success_probabilities = []
            
            for result in batch_results.values():
                input_data = result.get("input", {})
                prediction = result.get("prediction", {})
                
                pattern_types.append(input_data.get("pattern_type", "unknown"))
                success_probabilities.append(result.get("success_probability", 0.0))
            
            # Analyze pattern type distribution
            pattern_counts = {}
            for pattern_type in pattern_types:
                pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
            
            # Calculate average success by pattern type
            pattern_success = {}
            for i, pattern_type in enumerate(pattern_types):
                if pattern_type not in pattern_success:
                    pattern_success[pattern_type] = []
                pattern_success[pattern_type].append(success_probabilities[i])
            
            pattern_averages = {
                pattern_type: np.mean(probabilities)
                for pattern_type, probabilities in pattern_success.items()
            }
            
            return {
                "pattern_type_distribution": pattern_counts,
                "average_success_by_pattern": pattern_averages,
                "most_common_pattern": max(pattern_counts.items(), key=lambda x: x[1])[0] if pattern_counts else None,
                "best_performing_pattern": max(pattern_averages.items(), key=lambda x: x[1])[0] if pattern_averages else None
            }
            
        except Exception as e:
            logger.error(f"Error identifying batch patterns: {e}")
            return {}
    
    async def _update_model_metrics(self, accuracy_scores: Dict[str, float]) -> Dict[str, Any]:
        """Update model performance metrics with feedback."""
        try:
            improvements = {}
            
            for pred_type, accuracy in accuracy_scores.items():
                if pred_type in self.model_metrics:
                    current_metrics = self.model_metrics[pred_type].get("metrics", {})
                    
                    # Update accuracy (simplified)
                    if "accuracy" in current_metrics:
                        new_accuracy = (current_metrics["accuracy"] + accuracy) / 2
                        self.model_metrics[pred_type]["metrics"]["accuracy"] = new_accuracy
                        improvements[pred_type] = new_accuracy - current_metrics["accuracy"]
                    elif "mse" in current_metrics:
                        # For regression models, convert accuracy to error
                        error = 1.0 - accuracy
                        new_mse = (current_metrics["mse"] + error) / 2
                        self.model_metrics[pred_type]["metrics"]["mse"] = new_mse
                        improvements[pred_type] = current_metrics["mse"] - new_mse
            
            return improvements
            
        except Exception as e:
            logger.error(f"Error updating model metrics: {e}")
            return {}
    
    async def _create_training_example(
        self,
        stored_prediction: Dict[str, Any],
        actual_result: Dict[str, Any],
        feedback_data: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Create training example from prediction and actual result."""
        try:
            # Extract features from stored prediction
            java_concept = stored_prediction.get("java_concept")
            bedrock_concept = stored_prediction.get("bedrock_concept")
            context_data = stored_prediction.get("context_data", {})
            
            # Create training example
            training_example = {
                "java_concept": java_concept,
                "bedrock_concept": bedrock_concept,
                "pattern_type": context_data.get("pattern_type", "unknown"),
                "minecraft_version": context_data.get("minecraft_version", "latest"),
                "overall_success": actual_result.get("overall_success", 0),
                "feature_completeness": actual_result.get("feature_completeness", 0.5),
                "performance_impact": actual_result.get("performance_impact", 0.5),
                "compatibility_score": actual_result.get("compatibility_score", 0.7),
                "risk_assessment": actual_result.get("risk_assessment", 0.5),
                "conversion_time": actual_result.get("conversion_time", 1.0),
                "resource_usage": actual_result.get("resource_usage", 0.5),
                "feedback_data": feedback_data or {},
                "metadata": {
                    "source": "feedback",
                    "creation_timestamp": datetime.utcnow().isoformat()
                }
            }
            
            return training_example
            
        except Exception as e:
            logger.error(f"Error creating training example: {e}")
            return None
    
    async def _get_model_update_recommendation(self, accuracy_scores: Dict[str, float]) -> str:
        """Get recommendation for model updates."""
        try:
            avg_accuracy = np.mean(list(accuracy_scores.values())) if accuracy_scores else 0.0
            
            if avg_accuracy > 0.8:
                return "Models performing well - continue current approach"
            elif avg_accuracy > 0.6:
                return "Models performing moderately - consider retraining with more data"
            else:
                return "Models need improvement - review training data and feature engineering"
                
        except Exception:
            return "Unable to generate recommendation"


# Singleton instance
conversion_success_prediction_service = ConversionSuccessPredictionService()
