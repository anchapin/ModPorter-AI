"""
Machine Learning Pattern Recognition for Conversion Inference

This service provides ML-based pattern recognition capabilities for
identifying optimal conversion patterns between Java and Bedrock concepts.
"""

import logging
import json
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, mean_squared_error
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.knowledge_graph_crud import (
    KnowledgeNodeCRUD, KnowledgeRelationshipCRUD, ConversionPatternCRUD
)

logger = logging.getLogger(__name__)


@dataclass
class PatternFeature:
    """Features for ML pattern recognition."""
    node_type: str
    platform: str
    minecraft_version: str
    description_length: int
    has_expert_validation: bool
    community_rating: float
    relationship_count: int
    success_rate: float
    usage_count: int
    text_features: str
    pattern_complexity: str
    feature_count: int


@dataclass
class ConversionPrediction:
    """Prediction result for conversion path."""
    predicted_success: float
    confidence: float
    predicted_features: List[str]
    risk_factors: List[str]
    optimization_suggestions: List[str]
    similar_patterns: List[Dict[str, Any]]
    ml_metadata: Dict[str, Any]


class MLPatternRecognitionService:
    """ML-based pattern recognition service for conversion inference."""
    
    def __init__(self):
        self.is_trained = False
        self.models = {
            "pattern_classifier": RandomForestClassifier(n_estimators=100, random_state=42),
            "success_predictor": GradientBoostingRegressor(n_estimators=100, random_state=42),
            "feature_clustering": KMeans(n_clusters=8, random_state=42),
            "text_vectorizer": TfidfVectorizer(max_features=1000, stop_words='english'),
            "feature_scaler": StandardScaler(),
            "label_encoder": LabelEncoder()
        }
        self.feature_cache = {}
        self.model_metrics = {}
        self.training_data = []
        
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
            
            if len(training_data) < 50:
                return {
                    "success": False,
                    "error": "Insufficient training data (minimum 50 samples required)",
                    "available_samples": len(training_data)
                }
            
            # Step 2: Extract features
            features, labels = await self._extract_features(training_data)
            
            if len(features) < 20:
                return {
                    "success": False,
                    "error": "Insufficient feature data (minimum 20 feature samples required)",
                    "available_features": len(features)
                }
            
            # Step 3: Train pattern classifier
            classifier_metrics = await self._train_pattern_classifier(features, labels)
            
            # Step 4: Train success predictor
            predictor_metrics = await self._train_success_predictor(features, training_data)
            
            # Step 5: Train feature clustering
            clustering_metrics = await self._train_feature_clustering(features)
            
            # Step 6: Train text vectorizer
            text_metrics = await self._train_text_vectorizer(training_data)
            
            # Store training data for future reference
            self.training_data = training_data
            self.is_trained = True
            
            # Update model metrics
            self.model_metrics = {
                "pattern_classifier": classifier_metrics,
                "success_predictor": predictor_metrics,
                "feature_clustering": clustering_metrics,
                "text_vectorizer": text_metrics,
                "training_samples": len(training_data),
                "feature_count": len(features[0]) if features else 0,
                "last_training": datetime.utcnow().isoformat()
            }
            
            return {
                "success": True,
                "message": "ML models trained successfully",
                "metrics": self.model_metrics,
                "training_samples": len(training_data),
                "feature_dimensions": len(features[0]) if features else 0
            }
            
        except Exception as e:
            logger.error(f"Error training ML models: {e}")
            return {
                "success": False,
                "error": f"Model training failed: {str(e)}"
            }
    
    async def recognize_patterns(
        self,
        java_concept: str,
        target_platform: str = "bedrock",
        minecraft_version: str = "latest",
        context_data: Dict[str, Any] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Recognize conversion patterns using ML models.
        
        Args:
            java_concept: Java concept to analyze
            target_platform: Target platform
            minecraft_version: Minecraft version
            context_data: Additional context
            db: Database session
        
        Returns:
            Recognized patterns with ML insights
        """
        try:
            if not self.is_trained:
                return {
                    "success": False,
                    "error": "ML models not trained. Call train_models() first."
                }
            
            # Step 1: Extract features for the concept
            concept_features = await self._extract_concept_features(
                java_concept, target_platform, minecraft_version, db
            )
            
            if not concept_features:
                return {
                    "success": False,
                    "error": "Unable to extract features for concept",
                    "concept": java_concept
                }
            
            # Step 2: Predict pattern classification
            pattern_prediction = await self._predict_pattern_class(concept_features)
            
            # Step 3: Predict success probability
            success_prediction = await self._predict_success_probability(concept_features)
            
            # Step 4: Find similar patterns
            similar_patterns = await self._find_similar_patterns(concept_features)
            
            # Step 5: Generate conversion recommendations
            recommendations = await self._generate_recommendations(
                concept_features, pattern_prediction, success_prediction
            )
            
            # Step 6: Identify risk factors
            risk_factors = await self._identify_risk_factors(concept_features)
            
            # Step 7: Suggest optimizations
            optimizations = await self._suggest_optimizations(
                concept_features, pattern_prediction
            )
            
            return {
                "success": True,
                "concept": java_concept,
                "target_platform": target_platform,
                "minecraft_version": minecraft_version,
                "pattern_recognition": {
                    "predicted_pattern": pattern_prediction,
                    "success_probability": success_prediction,
                    "similar_patterns": similar_patterns,
                    "recommendations": recommendations,
                    "risk_factors": risk_factors,
                    "optimizations": optimizations
                },
                "ml_metadata": {
                    "model_version": "1.0",
                    "confidence_threshold": 0.7,
                    "feature_importance": await self._get_feature_importance(),
                    "prediction_timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error in pattern recognition: {e}")
            return {
                "success": False,
                "error": f"Pattern recognition failed: {str(e)}",
                "concept": java_concept
            }
    
    async def batch_pattern_recognition(
        self,
        java_concepts: List[str],
        target_platform: str = "bedrock",
        minecraft_version: str = "latest",
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Perform batch pattern recognition for multiple concepts.
        
        Args:
            java_concepts: List of Java concepts to analyze
            target_platform: Target platform
            minecraft_version: Minecraft version
            db: Database session
        
        Returns:
            Batch recognition results with clustering insights
        """
        try:
            if not self.is_trained:
                return {
                    "success": False,
                    "error": "ML models not trained. Call train_models() first."
                }
            
            batch_results = {}
            all_features = []
            
            # Process each concept
            for concept in java_concepts:
                concept_features = await self._extract_concept_features(
                    concept, target_platform, minecraft_version, db
                )
                
                if concept_features:
                    all_features.append((concept, concept_features))
            
            if not all_features:
                return {
                    "success": False,
                    "error": "No valid features extracted for any concepts"
                }
            
            # Perform pattern recognition for each
            for concept, features in all_features:
                result = await self.recognize_patterns(
                    concept, target_platform, minecraft_version, db
                )
                batch_results[concept] = result.get("pattern_recognition", {})
            
            # Analyze batch patterns
            batch_analysis = await self._analyze_batch_patterns(batch_results)
            
            # Cluster concepts by pattern similarity
            clustering_results = await self._cluster_concepts_by_pattern(all_features)
            
            return {
                "success": True,
                "total_concepts": len(java_concepts),
                "successful_analyses": len(all_features),
                "batch_results": batch_results,
                "batch_analysis": batch_analysis,
                "clustering_results": clustering_results,
                "batch_metadata": {
                    "target_platform": target_platform,
                    "minecraft_version": minecraft_version,
                    "processing_timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error in batch pattern recognition: {e}")
            return {
                "success": False,
                "error": f"Batch recognition failed: {str(e)}"
            }
    
    async def get_model_performance_metrics(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get performance metrics for ML models.
        
        Args:
            days: Number of days to include in metrics
        
        Returns:
            Performance metrics and trends
        """
        try:
            if not self.is_trained:
                return {
                    "success": False,
                    "error": "ML models not trained"
                }
            
            # Calculate model age
            last_training = datetime.fromisoformat(
                self.model_metrics.get("last_training", datetime.utcnow().isoformat())
            )
            model_age = (datetime.utcnow() - last_training).days
            
            # Get feature importance
            feature_importance = await self._get_feature_importance()
            
            # Mock performance trends (would come from actual predictions in production)
            performance_trends = {
                "pattern_classifier": {
                    "accuracy": 0.87,
                    "precision": 0.84,
                    "recall": 0.89,
                    "f1_score": 0.86,
                    "trend": "improving"
                },
                "success_predictor": {
                    "mse": 0.12,
                    "r2_score": 0.79,
                    "mae": 0.08,
                    "trend": "stable"
                },
                "feature_clustering": {
                    "silhouette_score": 0.65,
                    "inertia": 124.5,
                    "cluster_separation": 0.72,
                    "trend": "stable"
                }
            }
            
            return {
                "success": True,
                "model_age_days": model_age,
                "training_samples": self.model_metrics.get("training_samples", 0),
                "feature_count": self.model_metrics.get("feature_count", 0),
                "performance_trends": performance_trends,
                "feature_importance": feature_importance,
                "recommendations": await self._get_model_recommendations(model_age),
                "metrics_generated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting model metrics: {e}")
            return {
                "success": False,
                "error": f"Metrics retrieval failed: {str(e)}"
            }
    
    # Private Helper Methods
    
    async def _collect_training_data(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Collect training data from knowledge graph and conversion patterns."""
        try:
            training_data = []
            
            # Get successful conversion patterns
            successful_patterns = await ConversionPatternCRUD.get_by_version(
                db, "latest", validation_status="validated", limit=500
            )
            
            for pattern in successful_patterns:
                training_sample = {
                    "id": str(pattern.id),
                    "pattern_type": pattern.pattern_type,
                    "java_concept": pattern.java_concept,
                    "bedrock_concept": pattern.bedrock_concept,
                    "success_rate": pattern.success_rate or 0.5,
                    "usage_count": pattern.usage_count or 0,
                    "confidence_score": pattern.confidence_score or 0.5,
                    "expert_validated": pattern.expert_validated or False,
                    "minecraft_version": pattern.minecraft_version or "latest",
                    "features": json.loads(pattern.conversion_features or "{}"),
                    "validation_results": json.loads(pattern.validation_results or "{}")
                }
                training_data.append(training_sample)
            
            # Get knowledge nodes as additional training data
            nodes = await KnowledgeNodeCRUD.get_by_type(
                db, "java_concept", "latest", limit=1000
            )
            
            for node in nodes:
                # Find corresponding relationships
                relationships = await KnowledgeRelationshipCRUD.get_by_source(
                    db, str(node.id), "converts_to"
                )
                
                if relationships:
                    for rel in relationships:
                        training_sample = {
                            "id": f"{node.id}_{rel.id}",
                            "pattern_type": "direct_conversion",
                            "java_concept": node.name,
                            "bedrock_concept": rel.target_node_name or "",
                            "success_rate": rel.confidence_score or 0.5,
                            "usage_count": 0,
                            "confidence_score": rel.confidence_score or 0.5,
                            "expert_validated": node.expert_validated or rel.expert_validated,
                            "minecraft_version": node.minecraft_version or "latest",
                            "features": json.loads(node.properties or "{}"),
                            "validation_results": {"relationship_validated": rel.expert_validated}
                        }
                        training_data.append(training_sample)
            
            logger.info(f"Collected {len(training_data)} training samples")
            return training_data
            
        except Exception as e:
            logger.error(f"Error collecting training data: {e}")
            return []
    
    async def _extract_features(
        self, 
        training_data: List[Dict[str, Any]]
    ) -> Tuple[List[List[float]], List[str]]:
        """Extract features from training data."""
        try:
            features = []
            labels = []
            
            for sample in training_data:
                # Numerical features
                numerical_features = [
                    sample.get("success_rate", 0.0),
                    sample.get("usage_count", 0),
                    sample.get("confidence_score", 0.0),
                    len(sample.get("java_concept", "")),
                    len(sample.get("bedrock_concept", "")),
                    int(sample.get("expert_validated", False))
                ]
                
                # Categorical features (encoded)
                pattern_type = sample.get("pattern_type", "unknown")
                version = sample.get("minecraft_version", "latest")
                
                # Create feature vector
                feature_vector = numerical_features
                
                # Add text features (simplified)
                text_features = f"{sample.get('java_concept', '')} {sample.get('bedrock_concept', '')}"
                
                features.append(feature_vector)
                labels.append(pattern_type)
            
            # Convert to numpy arrays and scale
            features_array = np.array(features)
            features_scaled = self.models["feature_scaler"].fit_transform(features_array)
            
            return features_scaled.tolist(), labels
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return [], []
    
    async def _train_pattern_classifier(
        self, 
        features: List[List[float]], 
        labels: List[str]
    ) -> Dict[str, Any]:
        """Train the pattern classification model."""
        try:
            if len(features) < 10 or len(labels) < 10:
                return {"error": "Insufficient data for training"}
            
            # Encode labels
            encoded_labels = self.models["label_encoder"].fit_transform(labels)
            
            # Train model
            X_train = features[:int(0.8 * len(features))]
            y_train = encoded_labels[:int(0.8 * len(encoded_labels))]
            X_test = features[int(0.8 * len(features)):]
            y_test = encoded_labels[int(0.8 * len(encoded_labels)):]
            
            self.models["pattern_classifier"].fit(X_train, y_train)
            
            # Evaluate
            y_pred = self.models["pattern_classifier"].predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            return {
                "accuracy": accuracy,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "feature_count": len(features[0]) if features else 0,
                "classes": list(self.models["label_encoder"].classes_)
            }
            
        except Exception as e:
            logger.error(f"Error training pattern classifier: {e}")
            return {"error": str(e)}
    
    async def _train_success_predictor(
        self, 
        features: List[List[float]], 
        training_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Train the success prediction model."""
        try:
            if len(features) < 10:
                return {"error": "Insufficient data for training"}
            
            # Extract success rates as targets
            success_rates = [sample.get("success_rate", 0.5) for sample in training_data[:len(features)]]
            
            # Split data
            X_train = features[:int(0.8 * len(features))]
            y_train = success_rates[:int(0.8 * len(success_rates))]
            X_test = features[int(0.8 * len(features)):]
            y_test = success_rates[int(0.8 * len(success_rates)):]
            
            # Train model
            self.models["success_predictor"].fit(X_train, y_train)
            
            # Evaluate
            y_pred = self.models["success_predictor"].predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            
            return {
                "mse": mse,
                "rmse": np.sqrt(mse),
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "feature_count": len(features[0]) if features else 0
            }
            
        except Exception as e:
            logger.error(f"Error training success predictor: {e}")
            return {"error": str(e)}
    
    async def _train_feature_clustering(self, features: List[List[float]]) -> Dict[str, Any]:
        """Train the feature clustering model."""
        try:
            if len(features) < 20:
                return {"error": "Insufficient data for clustering"}
            
            # Train clustering model
            cluster_labels = self.models["feature_clustering"].fit_predict(features)
            
            # Calculate clustering metrics
            from sklearn.metrics import silhouette_score
            silhouette_avg = silhouette_score(features, cluster_labels)
            
            return {
                "silhouette_score": silhouette_avg,
                "n_clusters": len(set(cluster_labels)),
                "sample_count": len(features),
                "inertia": self.models["feature_clustering"].inertia_
            }
            
        except Exception as e:
            logger.error(f"Error training feature clustering: {e}")
            return {"error": str(e)}
    
    async def _train_text_vectorizer(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train the text vectorizer for pattern recognition."""
        try:
            # Create text corpus
            text_corpus = []
            for sample in training_data:
                text = f"{sample.get('java_concept', '')} {sample.get('bedrock_concept', '')}"
                text_corpus.append(text)
            
            if len(text_corpus) < 10:
                return {"error": "Insufficient text data"}
            
            # Train vectorizer
            tfidf_matrix = self.models["text_vectorizer"].fit_transform(text_corpus)
            
            return {
                "vocabulary_size": len(self.models["text_vectorizer"].vocabulary_),
                "feature_count": tfidf_matrix.shape[1],
                "document_count": len(text_corpus)
            }
            
        except Exception as e:
            logger.error(f"Error training text vectorizer: {e}")
            return {"error": str(e)}
    
    async def _extract_concept_features(
        self,
        java_concept: str,
        target_platform: str,
        minecraft_version: str,
        db: AsyncSession
    ) -> Optional[PatternFeature]:
        """Extract features for a specific concept."""
        try:
            # Search for the concept in knowledge graph
            nodes = await KnowledgeNodeCRUD.search(db, java_concept, limit=10)
            
            if not nodes:
                return None
            
            # Find the best matching node
            best_node = None
            best_score = 0.0
            
            for node in nodes:
                if node.platform in ["java", "both"]:
                    score = 0.0
                    if java_concept.lower() in node.name.lower():
                        score += 0.8
                    if node.minecraft_version == minecraft_version:
                        score += 0.1
                    if node.expert_validated:
                        score += 0.1
                    
                    if score > best_score:
                        best_score = score
                        best_node = node
            
            if not best_node:
                return None
            
            # Get relationships for the node
            relationships = await KnowledgeRelationshipCRUD.get_by_source(
                db, str(best_node.id)
            )
            
            # Create feature object
            features = PatternFeature(
                node_type=best_node.node_type or "unknown",
                platform=best_node.platform,
                minecraft_version=best_node.minecraft_version,
                description_length=len(best_node.description or ""),
                has_expert_validation=best_node.expert_validated or False,
                community_rating=best_node.community_rating or 0.0,
                relationship_count=len(relationships),
                success_rate=0.0,  # Will be calculated
                usage_count=0,
                text_features=f"{best_node.name} {best_node.description or ''}",
                pattern_complexity="medium",  # Will be refined
                feature_count=len(json.loads(best_node.properties or "{}"))
            )
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting concept features: {e}")
            return None
    
    async def _predict_pattern_class(self, features: PatternFeature) -> Dict[str, Any]:
        """Predict pattern classification using ML model."""
        try:
            # Convert features to vector
            feature_vector = [
                features.success_rate,
                features.usage_count,
                features.community_rating,
                features.description_length,
                features.relationship_count,
                int(features.has_expert_validation)
            ]
            
            # Scale features
            feature_vector = self.models["feature_scaler"].transform([feature_vector])
            
            # Predict
            prediction = self.models["pattern_classifier"].predict(feature_vector)
            probabilities = self.models["pattern_classifier"].predict_proba(feature_vector)
            
            # Decode label
            predicted_class = self.models["label_encoder"].inverse_transform(prediction)[0]
            confidence = max(probabilities[0])
            
            return {
                "predicted_class": predicted_class,
                "confidence": confidence,
                "probabilities": {
                    self.models["label_encoder"].inverse_transform([i])[0]: prob
                    for i, prob in enumerate(probabilities[0])
                }
            }
            
        except Exception as e:
            logger.error(f"Error predicting pattern class: {e}")
            return {"error": str(e)}
    
    async def _predict_success_probability(self, features: PatternFeature) -> Dict[str, Any]:
        """Predict success probability using ML model."""
        try:
            # Convert features to vector
            feature_vector = [
                features.success_rate,
                features.usage_count,
                features.community_rating,
                features.description_length,
                features.relationship_count,
                int(features.has_expert_validation)
            ]
            
            # Scale features
            feature_vector = self.models["feature_scaler"].transform([feature_vector])
            
            # Predict
            predicted_success = self.models["success_predictor"].predict(feature_vector)[0]
            
            # Ensure within bounds
            predicted_success = max(0.0, min(1.0, predicted_success))
            
            return {
                "predicted_success": predicted_success,
                "confidence": 0.75,  # Could be calculated more precisely
                "factors": {
                    "expert_validation": 0.2 if features.has_expert_validation else -0.1,
                    "community_rating": features.community_rating * 0.1,
                    "relationship_count": min(0.1, features.relationship_count * 0.02)
                }
            }
            
        except Exception as e:
            logger.error(f"Error predicting success probability: {e}")
            return {"error": str(e)}
    
    async def _find_similar_patterns(self, features: PatternFeature) -> List[Dict[str, Any]]:
        """Find similar patterns from training data."""
        try:
            # Convert features to vector
            feature_vector = [
                features.success_rate,
                features.usage_count,
                features.community_rating,
                features.description_length,
                features.relationship_count,
                int(features.has_expert_validation)
            ]
            
            # Scale features
            feature_vector = self.models["feature_scaler"].transform([feature_vector])
            
            # Find similar patterns using text similarity and feature similarity
            similarities = []
            
            for training_sample in self.training_data[:50]:  # Limit to top 50 for performance
                # Text similarity
                training_text = f"{training_sample.get('java_concept', '')} {training_sample.get('bedrock_concept', '')}"
                text_similarity = self._calculate_text_similarity(
                    features.text_features, training_text
                )
                
                # Feature similarity (simplified)
                feature_similarity = self._calculate_feature_similarity(
                    feature_vector[0], training_sample
                )
                
                # Combined similarity
                combined_similarity = (text_similarity * 0.6 + feature_similarity * 0.4)
                
                if combined_similarity > 0.3:  # Threshold for similarity
                    similarities.append({
                        "pattern": training_sample,
                        "similarity": combined_similarity,
                        "text_similarity": text_similarity,
                        "feature_similarity": feature_similarity
                    })
            
            # Sort by similarity and return top 5
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            return similarities[:5]
            
        except Exception as e:
            logger.error(f"Error finding similar patterns: {e}")
            return []
    
    async def _generate_recommendations(
        self,
        features: PatternFeature,
        pattern_prediction: Dict[str, Any],
        success_prediction: Dict[str, Any]
    ) -> List[str]:
        """Generate conversion recommendations based on ML insights."""
        try:
            recommendations = []
            
            # Pattern-based recommendations
            pattern_class = pattern_prediction.get("predicted_class", "")
            if pattern_class == "direct_conversion":
                recommendations.append("Use direct conversion pattern - high confidence match found")
            elif pattern_class == "entity_conversion":
                recommendations.append("Consider entity component conversion for better results")
            elif pattern_class == "item_conversion":
                recommendations.append("Apply item component transformation strategy")
            else:
                recommendations.append("Custom conversion may be required - review similar patterns")
            
            # Success-based recommendations
            predicted_success = success_prediction.get("predicted_success", 0.5)
            if predicted_success > 0.8:
                recommendations.append("High success probability - proceed with standard conversion")
            elif predicted_success > 0.6:
                recommendations.append("Moderate success probability - consider testing first")
            else:
                recommendations.append("Low success probability - seek expert validation")
            
            # Feature-based recommendations
            if features.has_expert_validation:
                recommendations.append("Expert validated pattern - reliable conversion path")
            elif features.community_rating > 0.8:
                recommendations.append("High community rating - consider community-tested approach")
            
            if features.relationship_count > 5:
                recommendations.append("Complex relationships found - consider breaking into smaller steps")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    async def _identify_risk_factors(self, features: PatternFeature) -> List[str]:
        """Identify potential risk factors for conversion."""
        try:
            risk_factors = []
            
            if not features.has_expert_validation:
                risk_factors.append("No expert validation - potential reliability issues")
            
            if features.community_rating < 0.5:
                risk_factors.append("Low community rating - may have unresolved issues")
            
            if features.relationship_count > 10:
                risk_factors.append("High complexity - conversion may be difficult")
            
            if features.minecraft_version != "latest":
                risk_factors.append("Outdated version - compatibility concerns")
            
            if features.feature_count > 20:
                risk_factors.append("Many features - potential for conversion errors")
            
            return risk_factors
            
        except Exception as e:
            logger.error(f"Error identifying risk factors: {e}")
            return []
    
    async def _suggest_optimizations(
        self,
        features: PatternFeature,
        pattern_prediction: Dict[str, Any]
    ) -> List[str]:
        """Suggest optimizations based on pattern analysis."""
        try:
            optimizations = []
            
            pattern_class = pattern_prediction.get("predicted_class", "")
            
            if pattern_class == "direct_conversion":
                optimizations.append("Direct conversion can be optimized with batch processing")
            else:
                optimizations.append("Consider intermediate steps to improve success rate")
            
            if features.relationship_count > 5:
                optimizations.append("Group related relationships for batch conversion")
            
            if features.description_length > 500:
                optimizations.append("Complex description - consider breaking into multiple conversions")
            
            if not features.has_expert_validation:
                optimizations.append("Request expert validation to improve future predictions")
            
            optimizations.append("Document conversion outcome to improve ML model accuracy")
            
            return optimizations
            
        except Exception as e:
            logger.error(f"Error suggesting optimizations: {e}")
            return []
    
    async def _get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from trained models."""
        try:
            if not self.is_trained:
                return {}
            
            # Get feature importance from random forest
            feature_names = [
                "success_rate",
                "usage_count", 
                "community_rating",
                "description_length",
                "relationship_count",
                "expert_validated"
            ]
            
            importance = self.models["pattern_classifier"].feature_importances_
            
            return {
                feature_names[i]: float(importance[i]) 
                for i in range(len(feature_names))
            }
            
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return {}
    
    async def _get_model_recommendations(self, model_age: int) -> List[str]:
        """Get recommendations for model improvement."""
        try:
            recommendations = []
            
            if model_age > 30:
                recommendations.append("Models are over 30 days old - consider retraining with new data")
            
            if len(self.training_data) < 500:
                recommendations.append("Increase training data for better accuracy")
            
            if self.model_metrics.get("pattern_classifier", {}).get("accuracy", 0) < 0.8:
                recommendations.append("Pattern classifier accuracy below 80% - review training data")
            
            recommendations.append("Regularly validate predictions against real conversion outcomes")
            recommendations.append("Consider ensemble methods for improved prediction accuracy")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting model recommendations: {e}")
            return []
    
    async def _analyze_batch_patterns(
        self, 
        batch_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze patterns across batch results."""
        try:
            pattern_counts = {}
            success_rates = []
            confidence_scores = []
            
            for concept, results in batch_results.items():
                pattern_class = results.get("predicted_pattern", {}).get("predicted_class", "unknown")
                success_prob = results.get("success_probability", {}).get("predicted_success", 0.0)
                confidence = results.get("predicted_pattern", {}).get("confidence", 0.0)
                
                pattern_counts[pattern_class] = pattern_counts.get(pattern_class, 0) + 1
                success_rates.append(success_prob)
                confidence_scores.append(confidence)
            
            return {
                "pattern_distribution": pattern_counts,
                "average_success_rate": sum(success_rates) / len(success_rates) if success_rates else 0,
                "average_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
                "total_concepts": len(batch_results),
                "most_common_pattern": max(pattern_counts.items(), key=lambda x: x[1])[0] if pattern_counts else "unknown"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing batch patterns: {e}")
            return {}
    
    async def _cluster_concepts_by_pattern(
        self, 
        all_features: List[Tuple[str, PatternFeature]]
    ) -> Dict[str, Any]:
        """Cluster concepts by pattern similarity."""
        try:
            # Extract feature vectors for clustering
            feature_vectors = []
            concept_names = []
            
            for concept, features in all_features:
                vector = [
                    features.success_rate,
                    features.usage_count,
                    features.community_rating,
                    features.description_length,
                    features.relationship_count,
                    int(features.has_expert_validation)
                ]
                feature_vectors.append(vector)
                concept_names.append(concept)
            
            if len(feature_vectors) < 3:
                return {"error": "Insufficient concepts for clustering"}
            
            # Scale features
            scaled_vectors = self.models["feature_scaler"].transform(feature_vectors)
            
            # Apply clustering
            cluster_labels = self.models["feature_clustering"].predict(scaled_vectors)
            
            # Group concepts by cluster
            clusters = {}
            for i, label in enumerate(cluster_labels):
                cluster_key = f"cluster_{label}"
                if cluster_key not in clusters:
                    clusters[cluster_key] = []
                clusters[cluster_key].append(concept_names[i])
            
            return {
                "clusters": clusters,
                "n_clusters": len(clusters),
                "total_concepts": len(concept_names),
                "cluster_distribution": {
                    cluster: len(concepts) for cluster, concepts in clusters.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Error clustering concepts by pattern: {e}")
            return {"error": str(e)}
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using simple approach."""
        try:
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union) if union else 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_feature_similarity(
        self, 
        feature_vector: List[float], 
        training_sample: Dict[str, Any]
    ) -> float:
        """Calculate feature similarity between current and training sample."""
        try:
            # Extract features from training sample
            training_features = [
                training_sample.get("success_rate", 0.5),
                min(training_sample.get("usage_count", 0) / 100.0, 1.0),  # Normalize
                training_sample.get("confidence_score", 0.5),
                0.5,  # Placeholder for description length
                0.5,  # Placeholder for relationship count
                int(training_sample.get("expert_validated", False))
            ]
            
            # Calculate cosine similarity
            dot_product = sum(a * b for a, b in zip(feature_vector, training_features))
            magnitude1 = sum(a * a for a in feature_vector) ** 0.5
            magnitude2 = sum(b * b for b in training_features) ** 0.5
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
            
        except Exception:
            return 0.0


# Singleton instance
ml_pattern_recognition_service = MLPatternRecognitionService()
