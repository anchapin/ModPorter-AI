"""
Production ML Model Deployment System
Handles model loading, caching, versioning, and serving
"""
import asyncio
import logging
from pathlib import Path
import pickle
import joblib
import torch
import torch.nn as nn
from typing import Dict, Any, List, Optional, Union
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib
import aiofiles
import numpy as np
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

@dataclass
class ModelMetadata:
    """Model metadata for versioning and tracking"""
    name: str
    version: str
    model_type: str  # sklearn, pytorch, custom
    created_at: datetime
    file_path: str
    file_size: int
    checksum: str
    description: str
    performance_metrics: Dict[str, float]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    tags: List[str]
    is_active: bool = False

class ModelLoader(ABC):
    """Abstract base class for model loaders"""
    
    @abstractmethod
    async def load(self, file_path: str) -> Any:
        """Load model from file"""
        pass
    
    @abstractmethod
    async def save(self, model: Any, file_path: str) -> None:
        """Save model to file"""
        pass
    
    @abstractmethod
    async def predict(self, model: Any, data: Any) -> Any:
        """Make prediction with model"""
        pass

class SklearnModelLoader(ModelLoader):
    """Loader for scikit-learn models"""
    
    async def load(self, file_path: str) -> Any:
        """Load sklearn model"""
        loop = asyncio.get_event_loop()
        try:
            # Run blocking I/O in thread pool
            model = await loop.run_in_executor(None, joblib.load, file_path)
            logger.info(f"Loaded sklearn model from {file_path}")
            return model
        except Exception as e:
            logger.error(f"Failed to load sklearn model from {file_path}: {e}")
            raise
    
    async def save(self, model: Any, file_path: str) -> None:
        """Save sklearn model"""
        loop = asyncio.get_event_loop()
        try:
            # Create directory if it doesn't exist
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Run blocking I/O in thread pool
            await loop.run_in_executor(None, joblib.dump, model, file_path)
            logger.info(f"Saved sklearn model to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save sklearn model to {file_path}: {e}")
            raise
    
    async def predict(self, model: Any, data: Any) -> Any:
        """Make prediction with sklearn model"""
        loop = asyncio.get_event_loop()
        try:
            prediction = await loop.run_in_executor(None, model.predict, data)
            return prediction
        except Exception as e:
            logger.error(f"Sklearn prediction failed: {e}")
            raise

class PyTorchModelLoader(ModelLoader):
    """Loader for PyTorch models"""
    
    async def load(self, file_path: str) -> nn.Module:
        """Load PyTorch model"""
        try:
            model = torch.load(file_path, map_location='cpu')
            model.eval()  # Set to evaluation mode
            logger.info(f"Loaded PyTorch model from {file_path}")
            return model
        except Exception as e:
            logger.error(f"Failed to load PyTorch model from {file_path}: {e}")
            raise
    
    async def save(self, model: nn.Module, file_path: str) -> None:
        """Save PyTorch model"""
        try:
            # Create directory if it doesn't exist
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            torch.save(model, file_path)
            logger.info(f"Saved PyTorch model to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save PyTorch model to {file_path}: {e}")
            raise
    
    async def predict(self, model: nn.Module, data: torch.Tensor) -> torch.Tensor:
        """Make prediction with PyTorch model"""
        try:
            with torch.no_grad():
                if isinstance(data, np.ndarray):
                    data = torch.tensor(data)
                prediction = model(data)
                return prediction
        except Exception as e:
            logger.error(f"PyTorch prediction failed: {e}")
            raise

class ModelRegistry:
    """Model registry for managing model versions and metadata"""
    
    def __init__(self, registry_path: str = "models/registry.json"):
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.models: Dict[str, List[ModelMetadata]] = {}
        self.load_registry()
    
    def load_registry(self):
        """Load model registry from file"""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    data = json.load(f)
                    
                # Convert JSON back to ModelMetadata objects
                for model_name, versions in data.items():
                    self.models[model_name] = []
                    for version_data in versions:
                        # Convert string datetime back to datetime object
                        version_data['created_at'] = datetime.fromisoformat(version_data['created_at'])
                        self.models[model_name].append(ModelMetadata(**version_data))
                
                logger.info(f"Loaded registry with {len(self.models)} models")
            except Exception as e:
                logger.error(f"Failed to load model registry: {e}")
                self.models = {}
    
    def save_registry(self):
        """Save model registry to file"""
        try:
            data = {}
            for model_name, versions in self.models.items():
                data[model_name] = []
                for metadata in versions:
                    # Convert datetime to string for JSON serialization
                    metadata_dict = asdict(metadata)
                    metadata_dict['created_at'] = metadata.created_at.isoformat()
                    data[model_name].append(metadata_dict)
            
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info("Saved model registry")
        except Exception as e:
            logger.error(f"Failed to save model registry: {e}")
    
    def register_model(self, metadata: ModelMetadata) -> bool:
        """Register a new model version"""
        try:
            if metadata.name not in self.models:
                self.models[metadata.name] = []
            
            # Deactivate previous active version
            for model in self.models[metadata.name]:
                model.is_active = False
            
            # Add new model and activate it
            self.models[metadata.name].append(metadata)
            metadata.is_active = True
            
            self.save_registry()
            logger.info(f"Registered model {metadata.name} version {metadata.version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            return False
    
    def get_active_model(self, name: str) -> Optional[ModelMetadata]:
        """Get active model version"""
        if name in self.models:
            for model in self.models[name]:
                if model.is_active:
                    return model
        return None
    
    def get_model_versions(self, name: str) -> List[ModelMetadata]:
        """Get all versions of a model"""
        return self.models.get(name, [])
    
    def list_models(self) -> Dict[str, ModelMetadata]:
        """List all active models"""
        active_models = {}
        for name, versions in self.models.items():
            active = self.get_active_model(name)
            if active:
                active_models[name] = active
        return active_models

class ModelCache:
    """In-memory model caching with LRU eviction"""
    
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.access_times: Dict[str, datetime] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get model from cache"""
        if key in self.cache:
            self.access_times[key] = datetime.utcnow()
            return self.cache[key]
        return None
    
    def put(self, key: str, model: Any):
        """Put model in cache"""
        # Remove oldest if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        
        self.cache[key] = model
        self.access_times[key] = datetime.utcnow()
    
    def remove(self, key: str):
        """Remove model from cache"""
        if key in self.cache:
            del self.cache[key]
            del self.access_times[key]
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()
        self.access_times.clear()

class ProductionModelServer:
    """Production model server with deployment, versioning, and serving"""
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.loaders = {
            'sklearn': SklearnModelLoader(),
            'pytorch': PyTorchModelLoader(),
        }
        
        self.registry = ModelRegistry()
        self.cache = ModelCache(max_size=10)
        self.loaded_models: Dict[str, Any] = {}
        
        self.metrics = {
            'predictions': 0,
            'model_loads': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0
        }
    
    def _get_loader(self, model_type: str) -> ModelLoader:
        """Get appropriate model loader"""
        if model_type not in self.loaders:
            raise ValueError(f"Unsupported model type: {model_type}")
        return self.loaders[model_type]
    
    async def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of model file"""
        loop = asyncio.get_event_loop()
        def _calc_checksum():
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        
        return await loop.run_in_executor(None, _calc_checksum)
    
    async def deploy_model(
        self,
        name: str,
        version: str,
        model_file_path: str,
        model_type: str,
        description: str = "",
        performance_metrics: Dict[str, float] = None,
        input_schema: Dict[str, Any] = None,
        output_schema: Dict[str, Any] = None,
        tags: List[str] = None
    ) -> bool:
        """Deploy a new model version"""
        try:
            # Validate model file exists
            model_path = Path(model_file_path)
            if not model_path.exists():
                raise FileNotFoundError(f"Model file not found: {model_file_path}")
            
            # Calculate checksum
            checksum = await self._calculate_checksum(model_file_path)
            
            # Copy model to models directory
            target_path = self.models_dir / name / f"{version}.pkl"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            loop = asyncio.get_event_loop()
            async with aiofiles.open(model_file_path, 'rb') as src:
                content = await src.read()
            async with aiofiles.open(target_path, 'wb') as dst:
                await dst.write(content)
            
            # Create metadata
            metadata = ModelMetadata(
                name=name,
                version=version,
                model_type=model_type,
                created_at=datetime.utcnow(),
                file_path=str(target_path),
                file_size=model_path.stat().st_size,
                checksum=checksum,
                description=description,
                performance_metrics=performance_metrics or {},
                input_schema=input_schema or {},
                output_schema=output_schema or {},
                tags=tags or []
            )
            
            # Test loading the model
            loader = self._get_loader(model_type)
            test_model = await loader.load(str(target_path))
            
            # Register model
            success = self.registry.register_model(metadata)
            if success:
                # Cache the loaded model
                cache_key = f"{name}:{version}"
                self.cache.put(cache_key, test_model)
                self.metrics['model_loads'] += 1
                logger.info(f"Successfully deployed model {name} version {version}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to deploy model {name} version {version}: {e}")
            self.metrics['errors'] += 1
            return False
    
    async def load_model(self, name: str, version: Optional[str] = None) -> Any:
        """Load model into memory"""
        try:
            # Get model metadata
            if version:
                # Get specific version
                versions = self.registry.get_model_versions(name)
                metadata = next((v for v in versions if v.version == version), None)
            else:
                # Get active version
                metadata = self.registry.get_active_model(name)
            
            if not metadata:
                raise ValueError(f"Model {name} version {version or 'active'} not found")
            
            # Check cache first
            cache_key = f"{name}:{metadata.version}"
            model = self.cache.get(cache_key)
            if model:
                self.metrics['cache_hits'] += 1
                return model
            
            # Load from disk
            loader = self._get_loader(metadata.model_type)
            model = await loader.load(metadata.file_path)
            
            # Cache the model
            self.cache.put(cache_key, model)
            self.metrics['cache_misses'] += 1
            self.metrics['model_loads'] += 1
            
            logger.info(f"Loaded model {name} version {metadata.version}")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model {name}: {e}")
            self.metrics['errors'] += 1
            raise
    
    async def predict(
        self,
        model_name: str,
        data: Any,
        version: Optional[str] = None
    ) -> Any:
        """Make prediction with model"""
        try:
            # Load model
            model = await self.load_model(model_name, version)
            
            # Get model metadata
            if version:
                versions = self.registry.get_model_versions(model_name)
                metadata = next((v for v in versions if v.version == version), None)
            else:
                metadata = self.registry.get_active_model(model_name)
            
            # Make prediction
            loader = self._get_loader(metadata.model_type)
            prediction = await loader.predict(model, data)
            
            self.metrics['predictions'] += 1
            return prediction
            
        except Exception as e:
            logger.error(f"Prediction failed for model {model_name}: {e}")
            self.metrics['errors'] += 1
            raise
    
    async def get_model_info(self, name: str, version: Optional[str] = None) -> Optional[Dict]:
        """Get model information"""
        try:
            if version:
                versions = self.registry.get_model_versions(name)
                metadata = next((v for v in versions if v.version == version), None)
            else:
                metadata = self.registry.get_active_model(name)
            
            if not metadata:
                return None
            
            return asdict(metadata)
            
        except Exception as e:
            logger.error(f"Failed to get model info for {name}: {e}")
            return None
    
    def list_models(self) -> Dict[str, Any]:
        """List all deployed models"""
        return {
            name: asdict(metadata)
            for name, metadata in self.registry.list_models().items()
        }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get server metrics"""
        return {
            **self.metrics,
            'cache_size': len(self.cache.cache),
            'registered_models': len(self.registry.models),
            'total_model_versions': sum(len(versions) for versions in self.registry.models.values())
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        health_status = {
            'status': 'healthy',
            'checks': {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            # Check if we can load the registry
            active_models = self.registry.list_models()
            health_status['checks']['model_count'] = len(active_models)
            
            # Test loading a model if available
            if active_models:
                test_model_name = list(active_models.keys())[0]
                try:
                    await self.load_model(test_model_name)
                    health_status['checks']['model_loading'] = 'pass'
                except Exception as e:
                    health_status['checks']['model_loading'] = f'fail: {str(e)}'
                    health_status['status'] = 'degraded'
            else:
                health_status['checks']['model_loading'] = 'skip: no models'
            
            # Check cache
            health_status['checks']['cache_size'] = len(self.cache.cache)
            
            # Get metrics
            health_status['checks']['metrics'] = await self.get_metrics()
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['checks']['error'] = str(e)
            logger.error(f"Model server health check failed: {e}")
        
        return health_status

# Predefined model schemas for common use cases
CONVERSION_PREDICTION_SCHEMA = {
    'input_schema': {
        'type': 'object',
        'properties': {
            'code_snippet': {'type': 'string'},
            'conversion_type': {'type': 'string'},
            'minecraft_version': {'type': 'string'}
        },
        'required': ['code_snippet', 'conversion_type']
    },
    'output_schema': {
        'type': 'object',
        'properties': {
            'success_probability': {'type': 'number'},
            'confidence_score': {'type': 'number'},
            'estimated_time': {'type': 'number'}
        }
    }
}

QUALITY_ASSESSMENT_SCHEMA = {
    'input_schema': {
        'type': 'object',
        'properties': {
            'converted_code': {'type': 'string'},
            'original_code': {'type': 'string'},
            'test_results': {'type': 'object'}
        }
    },
    'output_schema': {
        'type': 'object',
        'properties': {
            'quality_score': {'type': 'number'},
            'issues_found': {'type': 'array'},
            'recommendations': {'type': 'array'}
        }
    }
}
