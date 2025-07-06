#!/usr/bin/env python3
from ai_engine.src.models.smart_assumptions import SmartAssumptionEngine

engine = SmartAssumptionEngine()

feature_type = 'simple_custom_dimension'
feature_lower = feature_type.lower()
feature_keywords = feature_lower.replace('_', ' ').split()
print(f'Feature keywords: {feature_keywords}')

for assumption in engine.assumption_table:
    assumption_keywords = [word.lower() for word in assumption.java_feature.lower().split()]
    print(f'\nChecking {assumption.java_feature}:')
    print(f'  Assumption keywords: {assumption_keywords}')
    
    match_score = 0
    specific_matches = 0
    
    for feature_word in feature_keywords:
        for assumption_word in assumption_keywords:
            if feature_word == 'custom' and assumption_word == 'custom':
                match_score += 1
                print(f'    Generic custom match: {feature_word} -> {assumption_word} (+1)')
            elif len(feature_word) > 3 and (feature_word in assumption_word or assumption_word in feature_word):
                match_score += 5
                specific_matches += 1
                print(f'    Substring match: {feature_word} -> {assumption_word} (+5)')
            elif feature_word == assumption_word and feature_word != 'custom':
                match_score += 8
                specific_matches += 1
                print(f'    Exact match: {feature_word} -> {assumption_word} (+8)')
    
    print(f'  Total score: {match_score}, specific matches: {specific_matches}')
    print(f'  Include: {specific_matches > 0 or match_score >= 8}')